import axios from 'axios'

const AUTH_STORAGE_KEY = 'ai-novel-auth'
const BACKEND_STATUS_EVENT = 'ai-novel-backend-status'

function readAuthSession() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

function emitBackendStatus(payload) {
  if (typeof window === 'undefined') {
    return
  }
  window.dispatchEvent(new CustomEvent(BACKEND_STATUS_EVENT, { detail: payload }))
}

api.interceptors.request.use(
  config => {
    const session = readAuthSession()
    if (session.accessToken) {
      config.headers.Authorization = `Bearer ${session.accessToken}`
    }
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => {
    emitBackendStatus({
      reachable: true,
      detail: '',
      checkedAt: new Date().toISOString()
    })
    return response.data
  },
  error => {
    if (error.response?.data) {
      emitBackendStatus({
        reachable: true,
        detail: '',
        checkedAt: new Date().toISOString()
      })
      return Promise.reject(error.response.data)
    }

    if (error.code === 'ECONNABORTED') {
      emitBackendStatus({
        reachable: false,
        detail: '请求超时，请稍后重试或检查后端服务状态。',
        checkedAt: new Date().toISOString()
      })
      return Promise.reject({
        detail: '请求超时，请稍后重试或检查后端服务状态。',
        message: '请求超时'
      })
    }

    emitBackendStatus({
      reachable: false,
      detail: `后端服务不可达，请确认 ${api.defaults.baseURL} 已启动。`,
      checkedAt: new Date().toISOString()
    })
    return Promise.reject({
      detail: `后端服务不可达，请确认 ${api.defaults.baseURL} 已启动。`,
      message: '后端服务不可达'
    })
  }
)

export const apiClient = {
  healthCheck() {
    return api.get('/health')
  },

  listProviders() {
    return api.get('/api/providers')
  },

  getApiConfig() {
    return api.get('/api/settings/api-config')
  },

  saveApiConfig(config) {
    return api.post('/api/settings/api-config', config)
  },

  testApiConnection(config) {
    return api.post('/api/test-api', config)
  },

  login(credentials) {
    return api.post('/api/auth/login', credentials)
  },

  register(payload) {
    return api.post('/api/auth/register', payload)
  },

  sendVerificationCode(email) {
    return api.post('/api/auth/send-code', { email })
  },

  verifyCode(email, code) {
    return api.post('/api/auth/verify-code', { email, code })
  },

  getCurrentUser() {
    return api.get('/api/auth/me')
  },

  getQuotaInfo() {
    return api.get('/api/auth/me/quota')
  },

  getPublicPolicy() {
    return api.get('/api/auth/policy')
  },

  getAdminPolicy() {
    return api.get('/api/auth/admin/policy')
  },

  saveAdminPolicy(payload) {
    return api.put('/api/auth/admin/policy', payload)
  },

  listAdminUsers() {
    return api.get('/api/auth/admin/users')
  },

  updateAdminUserMembership(userId, payload) {
    return api.put(`/api/auth/admin/users/${userId}/membership`, payload)
  },

  updateAdminUserRole(userId, payload) {
    return api.put(`/api/auth/admin/users/${userId}/role`, payload)
  },

  listAdminRoles() {
    return api.get('/api/auth/admin/roles')
  },

  listAdminAuditLogs(params = {}) {
    return api.get('/api/auth/admin/audit-logs', { params })
  },

  getBillingPlans() {
    return api.get('/api/billing/plans')
  },

  listBillingOrders() {
    return api.get('/api/billing/orders')
  },

  listBillingInvoices() {
    return api.get('/api/billing/invoices')
  },

  createBillingOrder(payload) {
    return api.post('/api/billing/orders', payload)
  },

  submitBillingPayment(orderId, payload) {
    return api.post(`/api/billing/orders/${orderId}/submit-payment`, payload)
  },

  sandboxPayBillingOrder(orderId, payload = {}) {
    return api.post(`/api/billing/orders/${orderId}/sandbox-pay`, payload)
  },

  approveBillingOrder(orderId, payload = {}) {
    return api.post(`/api/billing/orders/${orderId}/approve`, payload)
  },

  cancelBillingOrder(orderId, payload = {}) {
    return api.post(`/api/billing/orders/${orderId}/cancel`, payload)
  },

  redeemCardCode(code) {
    return api.post('/api/billing/redeem', { code })
  },

  getBalance() {
    return api.get('/api/billing/balance')
  },

  createTopUpOrder(payload) {
    return api.post('/api/billing/topup', payload)
  },

  listProjects() {
    return api.get('/api/projects')
  },

  getProject(projectId) {
    return api.get(`/api/projects/${projectId}`)
  },

  appendProjectChapter(projectId, payload) {
    return api.post(`/api/projects/${projectId}/chapters`, payload)
  },

  replaceProjectContent(projectId, payload) {
    return api.put(`/api/projects/${projectId}/content`, payload)
  },

  createProject(payload) {
    return api.post('/api/projects', payload)
  },

  deleteProject(projectId) {
    return api.delete(`/api/projects/${projectId}`)
  },

  getProjectExportUrl(projectId, format = 'txt') {
    const baseURL = api.defaults.baseURL || ''
    return `${baseURL}/api/projects/${projectId}/export?format=${encodeURIComponent(format)}`
  },

  listJobs() {
    return api.get('/api/jobs')
  },

  getJob(jobId) {
    return api.get(`/api/jobs/${jobId}`)
  },

  deleteJob(jobId) {
    return api.delete(`/api/jobs/${jobId}`)
  },

  createFullGenerationJob(payload) {
    return api.post('/api/jobs/full-generate', payload)
  },

  retryJob(jobId) {
    return api.post(`/api/jobs/${jobId}/retry`)
  },

  generateQuickOutline(payload) {
    return api.post('/api/quick/outline', payload)
  },

  generateSnowflakeArchitecture(config) {
    return api.post('/api/snowflake/architecture', config)
  },

  generateChapterBlueprint(data) {
    return api.post('/api/snowflake/blueprint', data)
  },

  parseBlueprint(blueprint) {
    return api.post('/api/parse-blueprint', { blueprint })
  },

  polishText(payload) {
    return api.post('/api/tools/polish', payload)
  },

  polishWithSuggestions(payload) {
    return api.post('/api/tools/polish-suggestions', payload)
  },

  analyzeContinuation(payload) {
    return api.post('/api/tools/continuation/analyze', payload)
  },

  generateContinuation(payload) {
    return api.post('/api/tools/continuation/generate', payload)
  },

  listPromptTemplates(category) {
    return api.get('/api/prompts/templates', { params: category ? { category } : {} })
  },

  getPromptTemplate(category, name) {
    return api.get('/api/prompts/template', { params: { category, name } })
  },

  savePromptTemplate(payload) {
    return api.post('/api/prompts/template', payload)
  },

  resetPromptTemplate(payload) {
    return api.post('/api/prompts/reset', payload)
  },

  // ---------------------------------------------------------------------------
  // 管理员 API
  // ---------------------------------------------------------------------------

  getAdminConfig() {
    return api.get('/api/admin/config')
  },

  saveAdminConfig(config) {
    return api.put('/api/admin/config', config)
  },

  getAdminConfigByKey(key) {
    return api.get(`/api/admin/config/${key}`)
  },

  saveAdminConfigByKey(key, value) {
    return api.put(`/api/admin/config/${key}`, value)
  },

  getAdminSmtpConfig() {
    return api.get('/api/admin/config/smtp')
  },

  saveAdminSmtpConfig(config) {
    return api.put('/api/admin/config/smtp', config)
  },

  testAdminSmtp(config) {
    return api.post('/api/admin/config/smtp/test', config)
  },

  getAdminPaymentConfig() {
    return api.get('/api/admin/config/payment')
  },

  saveAdminPaymentConfig(config) {
    return api.put('/api/admin/config/payment', config)
  },

  getAdminMembershipConfig() {
    return api.get('/api/admin/config/membership')
  },

  saveAdminMembershipConfig(config) {
    return api.put('/api/admin/config/membership', config)
  },

  getAdminUsers(params) {
    return api.get('/api/admin/users', { params })
  },

  getAdminUser(userId) {
    return api.get(`/api/admin/users/${userId}`)
  },

  banAdminUser(userId, data) {
    return api.put(`/api/admin/users/${userId}/ban`, data)
  },

  adjustUserBalance(userId, data) {
    return api.put(`/api/admin/users/${userId}/adjust-balance`, data)
  },

  generateCardCodes(data) {
    return api.post('/api/admin/card-codes/generate', data)
  },

  getAdminCardCodes(params) {
    return api.get('/api/admin/card-codes', { params })
  },

  disableCardCode(codeId) {
    return api.put(`/api/admin/card-codes/${codeId}/disable`)
  },

  getAdminOrders(params) {
    return api.get('/api/admin/orders', { params })
  },

  getAdminStats() {
    return api.get('/api/admin/stats')
  },

  getAdminAuditLogs(params) {
    return api.get('/api/admin/audit-logs', { params })
  },

  getAdminStyleConfig() {
    return api.get('/api/admin/config/styles')
  },

  saveAdminStyleConfig(config) {
    return api.put('/api/admin/config/styles', config)
  },

  getAdminGenerationConfig() {
    return api.get('/api/admin/config/generation')
  },

  saveAdminGenerationConfig(config) {
    return api.put('/api/admin/config/generation', config)
  },
}

export { AUTH_STORAGE_KEY }
export { BACKEND_STATUS_EVENT }
export const API_BASE_URL = api.defaults.baseURL || ''
export default api
