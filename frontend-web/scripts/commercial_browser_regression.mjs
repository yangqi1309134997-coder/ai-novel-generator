import fs from 'node:fs'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'
import { chromium } from 'playwright-core'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const DEFAULT_REPORT_PATH = path.join(ROOT, 'logs', 'commercial_browser_regression_latest.json')
const FRONTEND_HOST = process.env.COMMERCIAL_FRONTEND_HOST || '127.0.0.1'
const STATE_FILE_CANDIDATES = [
  path.join(ROOT, 'logs', 'admin_ui_state.json'),
  path.join(ROOT, 'logs', 'commercial_regression_state.json')
]
const FRONTEND_PORT_CANDIDATES = (process.env.COMMERCIAL_FRONTEND_PORT_CANDIDATES || '')
  .split(',')
  .map(item => Number(item.trim()))
  .filter(Number.isInteger)

if (!FRONTEND_PORT_CANDIDATES.length) {
  FRONTEND_PORT_CANDIDATES.push(
    ...Array.from({ length: 18 }, (_, index) => 4173 + index),
    ...Array.from({ length: 13 }, (_, index) => 5173 + index)
  )
}

function parseArgs(argv) {
  const args = {
    frontendUrl: '',
    reportPath: DEFAULT_REPORT_PATH
  }

  for (let index = 0; index < argv.length; index += 1) {
    const current = argv[index]
    if (current === '--frontend-url') {
      args.frontendUrl = argv[index + 1] || ''
      index += 1
      continue
    }

    if (current === '--report-path') {
      args.reportPath = argv[index + 1] || DEFAULT_REPORT_PATH
      index += 1
      continue
    }

    if (current.startsWith('http://') || current.startsWith('https://')) {
      args.frontendUrl = current
    }
  }

  return args
}

function loadCredentialState() {
  for (const candidate of STATE_FILE_CANDIDATES) {
    if (!fs.existsSync(candidate)) continue
    const data = JSON.parse(fs.readFileSync(candidate, 'utf-8'))
    if (data.admin_email && data.customer_email && data.password) {
      return {
        adminEmail: data.admin_email,
        customerEmail: data.customer_email,
        password: data.password
      }
    }
  }

  throw new Error('No saved browser regression credentials found in logs/admin_ui_state.json or logs/commercial_regression_state.json.')
}

async function resolveFrontendUrl(preferredUrl = '') {
  const candidates = preferredUrl
    ? [preferredUrl]
    : FRONTEND_PORT_CANDIDATES.map(port => `http://${FRONTEND_HOST}:${port}`)

  for (const candidate of candidates) {
    try {
      const response = await fetch(candidate, { redirect: 'follow' })
      if (!response.ok) continue
      const html = await response.text()
      if (html.includes('AI小说生成器 5.0')) {
        return candidate
      }
    } catch {
      // Continue probing.
    }
  }

  throw new Error('Unable to find a running commercial frontend. Start frontend-web before running browser regression.')
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true })
}

function writeReport(reportPath, report) {
  ensureDir(reportPath)
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf-8')
}

function findChromeExecutable() {
  const candidates = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  ]

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate
    }
  }

  return ''
}

async function login(page, frontendUrl, email, password) {
  await page.goto(`${frontendUrl}/login`, { waitUntil: 'networkidle' })
  await page.getByRole('textbox', { name: '邮箱' }).fill(email)
  await page.getByRole('textbox', { name: '密码' }).fill(password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL(url => url.pathname === '/workspace', { timeout: 20000 })
}

async function waitForAdminData(page) {
  await page.goto('/settings', { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: '商业版后台控制台' }).waitFor()
  await page.waitForFunction(
    () => {
      const text = document.body.innerText
      return (
        text.includes('客户数')
        && text.includes('策略影响概览')
        && text.includes('账号与权限管理')
        && !text.includes('客户策略同步中')
      )
    },
    { timeout: 20000 }
  )
}

async function waitForAccountData(page) {
  await page.goto('/account', { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: '客户账号中心' }).waitFor()
  await page.waitForFunction(
    () => {
      const text = document.body.innerText
      const loadingGone = !text.includes('正在同步账号资料、最近项目和任务结果')
      const contentReady = text.includes('升级会员')
        && text.includes('升级订单与账单')
        && text.includes('最近项目')
      return loadingGone && contentReady
    },
    { timeout: 20000 }
  )
}

async function createBillingOrderFromAccount(page) {
  const beforeText = await page.locator('body').innerText()
  const beforeOrders = new Set(beforeText.match(/ORD-[A-Z0-9]+/g) || [])

  await page.getByRole('button', { name: '创建升级订单' }).first().click()

  await page.waitForFunction(
    (existingOrders) => {
      const text = document.body.innerText
      const currentOrders = text.match(/ORD-[A-Z0-9]+/g) || []
      return currentOrders.some(orderNo => !existingOrders.includes(orderNo))
    },
    Array.from(beforeOrders),
    { timeout: 20000 }
  )

  const afterText = await page.locator('body').innerText()
  const afterOrders = afterText.match(/ORD-[A-Z0-9]+/g) || []
  const createdOrderNo = afterOrders.find(orderNo => !beforeOrders.has(orderNo)) || ''
  if (!createdOrderNo) {
    throw new Error('Unable to detect the newly created billing order number on the account page.')
  }

  await page.waitForFunction(
    (orderNo) => {
      const text = document.body.innerText
      return text.includes(orderNo) && text.includes('已支付')
    },
    createdOrderNo,
    { timeout: 20000 }
  )

  return createdOrderNo
}

async function waitForBillingOrderVisibleInAdmin(page, orderNo) {
  await page.goto('/settings', { waitUntil: 'domcontentloaded' })
  await page.getByRole('heading', { name: '商业版后台控制台' }).waitFor()
  await page.waitForFunction(
    (currentOrderNo) => {
      const text = document.body.innerText
      return text.includes('升级订单管理') && text.includes(currentOrderNo)
    },
    orderNo,
    { timeout: 20000 }
  )
}

async function run() {
  const args = parseArgs(process.argv.slice(2))
  const credentials = loadCredentialState()
  const frontendUrl = await resolveFrontendUrl(args.frontendUrl)
  const report = {
    frontend_url: frontendUrl,
    started_at: new Date().toISOString(),
    checks: {},
    evidence: {}
  }

  const executablePath = findChromeExecutable()
  if (!executablePath) {
    throw new Error('Chrome or Edge executable was not found. Install Chrome/Edge or update the executable path list.')
  }

  const browser = await chromium.launch({
    executablePath,
    headless: true
  })

  try {
    const context = await browser.newContext({
      baseURL: frontendUrl,
      viewport: { width: 1440, height: 1080 }
    })
    const page = await context.newPage()

    await login(page, frontendUrl, credentials.adminEmail, credentials.password)
    report.checks.admin_login = true

    await waitForAdminData(page)
    report.checks.admin_settings_loaded = true
    report.evidence.admin_url = page.url()

    await page.getByRole('button', { name: '退出' }).click()
    await page.waitForURL(url => url.pathname === '/', { timeout: 20000 })
    report.checks.admin_logout = true

    await login(page, frontendUrl, credentials.customerEmail, credentials.password)
    report.checks.customer_login = true

    await waitForAccountData(page)
    report.checks.customer_account_loaded = true
    report.evidence.customer_url = page.url()

    const createdOrderNo = await createBillingOrderFromAccount(page)
    report.checks.customer_billing_order_created = true
    report.evidence.created_order_no = createdOrderNo

    await page.goto('/', { waitUntil: 'networkidle' })
    const landingText = await page.locator('body').innerText()
    report.checks.home_logged_in_state = landingText.includes('当前账号：') || landingText.includes('customer_ui_')

    await page.getByRole('button', { name: '退出' }).click()
    await page.waitForURL(url => url.pathname === '/', { timeout: 20000 })
    const loggedOutText = await page.locator('body').innerText()
    report.checks.home_clears_after_logout = loggedOutText.includes('未登录') && loggedOutText.includes('当前项目数')

    await login(page, frontendUrl, credentials.adminEmail, credentials.password)
    report.checks.admin_relogin_for_billing = true

    await waitForBillingOrderVisibleInAdmin(page, createdOrderNo)
    report.checks.admin_billing_order_visible = true

    return report
  } finally {
    await browser.close()
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  try {
    const report = await run()
    report.finished_at = new Date().toISOString()
    report.success = Object.values(report.checks).every(Boolean)
    writeReport(args.reportPath, report)

    for (const [name, result] of Object.entries(report.checks)) {
      console.log(`[${result ? 'PASS' : 'FAIL'}] ${name}`)
    }
    console.log(`[INFO] report: ${args.reportPath}`)
    process.exit(report.success ? 0 : 1)
  } catch (error) {
    const report = {
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      success: false,
      error: error instanceof Error ? error.message : String(error)
    }
    writeReport(args.reportPath, report)
    console.error(`[ERROR] ${report.error}`)
    console.error(`[INFO] report: ${args.reportPath}`)
    process.exit(1)
  }
}

main()
