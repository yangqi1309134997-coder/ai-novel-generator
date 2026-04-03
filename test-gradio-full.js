const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  console.log('=== Starting Gradio E2E Testing ===\n');

  // Test results tracking
  const results = {
    total: 0,
    passed: 0,
    failed: 0,
    warnings: []
  };

  function test(name, fn) {
    results.total++;
    console.log(`\n[Test ${results.total}] ${name}`);
    return fn().catch(error => {
      results.failed++;
      console.error(`❌ FAILED: ${name}`);
      console.error(`   Error: ${error.message}`);
      if (error.stack) {
        console.error(`   Stack: ${error.stack.split('\n').slice(0, 3).join('\n')}`);
      }
      return { success: false, error: error.message };
    }).then(result => {
      if (result.success !== false) {
        results.passed++;
        console.log(`✓ PASSED: ${name}`);
      }
      return result;
    });
  }

  function screenshot(name) {
    return page.screenshot({ path: `test-results/${name}.png`, fullPage: true });
  }

  async function clickBySelector(selector) {
    try {
      await page.waitForSelector(selector, { state: 'visible', timeout: 5000 });
      await page.click(selector, { timeout: 5000 });
      return true;
    } catch (error) {
      return false;
    }
  }

  async function waitForText(text, options = {}) {
    await page.waitForSelector(`:text("${text}")`, options);
  }

  // Create test results directory
  const fs = require('fs');
  if (!fs.existsSync('test-results')) {
    fs.mkdirSync('test-results');
  }

  // Step 1: Open page and take initial screenshot
  console.log('\n=== Step 1: Opening Page ===');
  await page.goto('http://localhost:7860', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await screenshot('01-initial-page');
  console.log('✓ Page loaded successfully');

  // Step 2: Test main Tab navigation
  console.log('\n=== Step 2: Testing Main Tab Navigation ===');

  const mainTabs = [
    { text: '✍️ 创作工作台', selector: '.tab-nav button' },
    { text: '🛠️ 优化与分析', selector: '.tab-nav button' },
    { text: '📁 项目中心', selector: '.tab-nav button' },
    { text: '⚙️ 系统设置', selector: '.tab-nav button' }
  ];

  for (const tab of mainTabs) {
    console.log(`\n--- Testing Tab: ${tab.text} ---`);
    try {
      // Try different selectors
      const tabSelectors = [
        tab.selector,
        'button',
        '[role="tab"]',
        `[data-testid*="tab"]`
      ];

      let clicked = false;
      for (const selector of tabSelectors) {
        try {
          await page.waitForSelector(selector, { state: 'visible', timeout: 5000 });
          const button = await page.locator(selector).first();
          const buttonText = await button.textContent();
          console.log(`   Checking button: "${buttonText}"`);

          if (buttonText && buttonText.includes(tab.text.split(' ')[1])) {
            await button.click({ timeout: 5000 });
            clicked = true;
            console.log(`   ✓ Clicked button with selector: ${selector}`);
            break;
          }
        } catch (e) {
          // Continue to next selector
        }
      }

      if (!clicked) {
        throw new Error(`Could not find or click tab: ${tab.text}`);
      }

      await page.waitForTimeout(1500);
      await screenshot(`02-main-tab-${tab.text.split(' ')[1]}`);
      console.log(`   ✓ Tab switched to ${tab.text}`);
    } catch (error) {
      console.error(`   ✗ FAILED to switch to tab: ${tab.text}`);
      results.warnings.push(`Failed to switch to main tab: ${tab.text}`);
    }
  }

  // Step 3: Test 创作工作台 sub-tabs
  console.log('\n=== Step 3: Testing 创作工作台 Sub-Tabs ===');

  // Go to 创作工作台
  await page.goto('http://localhost:7860', { waitUntil: 'networkidle', timeout: 30000 });

  // Try to find and click 创作工作台 tab
  const creationTabs = [
    { text: '📝 单章续写', selector: '.tab-nav button' },
    { text: '📚 整本生成', selector: '.tab-nav button' }
  ];

  for (const tab of creationTabs) {
    console.log(`\n--- Testing Sub-Tab: ${tab.text} ---`);

    try {
      // Wait for tab buttons to appear
      await page.waitForTimeout(1500);

      // Find and click the sub-tab
      const subTabButtons = await page.locator('.tab-nav button').all();
      let clicked = false;

      for (const button of subTabButtons) {
        const buttonText = await button.textContent();
        if (buttonText && buttonText.includes(tab.text.split(' ')[0])) {
          await button.click({ timeout: 5000 });
          clicked = true;
          console.log(`   ✓ Clicked sub-tab: ${tab.text}`);
          break;
        }
      }

      if (!clicked) {
        throw new Error(`Could not find sub-tab: ${tab.text}`);
      }

      await page.waitForTimeout(1500);
      await screenshot(`03-subtab-${tab.text.split(' ')[0]}`);

      // Test all interactive elements in the sub-tab
      console.log(`\n   Testing interactive elements...`);

      // Check for common Gradio components
      const interactiveSelectors = [
        'input[type="text"]',
        'input[type="number"]',
        'textarea',
        'select',
        'button',
        'input[type="checkbox"]',
        'input[type="radio"]'
      ];

      for (const selector of interactiveSelectors) {
        try {
          const elements = await page.locator(selector).all();
          if (elements.length > 0) {
            console.log(`   Found ${elements.length} ${selector} elements`);
          }
        } catch (e) {
          // Ignore errors
        }
      }

    } catch (error) {
      console.error(`   ✗ FAILED sub-tab: ${tab.text}`);
      results.warnings.push(`Failed to test sub-tab: ${tab.text}`);
    }
  }

  // Step 4: Test 优化与分析 tabs
  console.log('\n=== Step 4: Testing 优化与分析 Tabs ===');

  const analysisTabs = [
    { text: '📝 小说重写', selector: '.tab-nav button' },
    { text: '✨ 小说润色', selector: '.tab-nav button' },
    { text: '🔍 连贯性分析', selector: '.tab-nav button' },
    { text: '🧩 提示词编辑器', selector: '.tab-nav button' }
  ];

  for (const tab of analysisTabs) {
    console.log(`\n--- Testing Tab: ${tab.text} ---`);

    try {
      await page.goto('http://localhost:7860', { waitUntil: 'domcontentloaded', timeout: 60000 });

      // Wait for page to fully load
      await page.waitForTimeout(2000);

      // Try to find and click the tab
      const tabButtons = await page.locator('.tab-nav button').all();
      let clicked = false;

      for (const button of tabButtons) {
        const buttonText = await button.textContent();
        if (buttonText && buttonText.includes(tab.text.split(' ')[0])) {
          await button.click({ timeout: 5000 });
          clicked = true;
          console.log(`   ✓ Clicked tab: ${tab.text}`);
          break;
        }
      }

      if (!clicked) {
        throw new Error(`Could not find or click tab: ${tab.text}`);
      }

      await page.waitForTimeout(1500);
      await screenshot(`04-analysis-tab-${tab.text.split(' ')[0]}`);
      console.log(`   ✓ Tab content loaded`);

    } catch (error) {
      console.error(`   ✗ FAILED tab: ${tab.text}`);
      results.warnings.push(`Failed to test analysis tab: ${tab.text}`);
    }
  }

  // Step 5: Test 项目中心
  console.log('\n=== Step 5: Testing 项目中心 ===');

  try {
    await page.goto('http://localhost:7860', { waitUntil: 'networkidle', timeout: 30000 });

    // Find and click 项目中心 tab
    const tabButtons = await page.locator('.tab-nav button').all();
    let clicked = false;

    for (const button of tabButtons) {
      const buttonText = await button.textContent();
      if (buttonText && buttonText.includes('📁 项目中心')) {
        await button.click({ timeout: 5000 });
        clicked = true;
        console.log(`   ✓ Clicked 项目中心 tab`);
        break;
      }
    }

    if (!clicked) {
      throw new Error('Could not find or click 项目中心 tab');
    }

    await page.waitForTimeout(2000);
    await screenshot('05-project-center');

    // Test project center interactive elements
    console.log(`\n   Testing project center buttons...`);

    const buttons = await page.locator('button').all();
    for (const button of buttons) {
      const buttonText = await button.textContent();
      if (buttonText && (buttonText.includes('刷新') || buttonText.includes('删除') || buttonText.includes('导出'))) {
        try {
          await button.click({ timeout: 3000 });
          console.log(`   ✓ Found interactive button: "${buttonText.trim()}"`);
        } catch (e) {
          console.log(`   ✗ Button "${buttonText.trim()}" not clickable: ${e.message}`);
        }
      }
    }

  } catch (error) {
    console.error(`   ✗ FAILED 项目中心: ${error.message}`);
    results.warnings.push('Failed to test project center');
  }

  // Step 6: Test 系统设置 tabs
  console.log('\n=== Step 6: Testing 系统设置 Tabs ===');

  const settingsTabs = [
    { text: '🌐 接口管理', selector: '.tab-nav button' },
    { text: '📝 生成参数', selector: '.tab-nav button' },
    { text: '💾 缓存管理', selector: '.tab-nav button' }
  ];

  for (const tab of settingsTabs) {
    console.log(`\n--- Testing Tab: ${tab.text} ---`);

    try {
      await page.goto('http://localhost:7860', { waitUntil: 'domcontentloaded', timeout: 60000 });

      // Find and click the tab
      const tabButtons = await page.locator('.tab-nav button').all();
      let clicked = false;

      for (const button of tabButtons) {
        const buttonText = await button.textContent();
        if (buttonText && buttonText.includes(tab.text.split(' ')[0])) {
          await button.click({ timeout: 5000 });
          clicked = true;
          console.log(`   ✓ Clicked tab: ${tab.text}`);
          break;
        }
      }

      if (!clicked) {
        throw new Error(`Could not find or click tab: ${tab.text}`);
      }

      await page.waitForTimeout(1500);
      await screenshot(`06-settings-tab-${tab.text.split(' ')[0]}`);

      // Test specific elements based on tab
      if (tab.text.includes('接口管理')) {
        console.log(`   Testing interface management elements...`);

        // Check for select dropdowns
        const selects = await page.locator('select').all();
        console.log(`   Found ${selects.length} select dropdowns`);

        // Check for inputs
        const inputs = await page.locator('input[type="text"], input[type="password"]').all();
        console.log(`   Found ${inputs.length} text/password inputs`);

        // Check for buttons
        const buttons = await page.locator('button').all();
        for (const button of buttons) {
          const buttonText = await button.textContent();
          if (buttonText && buttonText.includes('测试连接')) {
            try {
              await button.click({ timeout: 5000 });
              console.log(`   ✓ "测试连接" button is clickable`);
            } catch (e) {
              console.log(`   ✗ "测试连接" button not clickable: ${e.message}`);
            }
          }
        }
      }

    } catch (error) {
      console.error(`   ✗ FAILED tab: ${tab.text} - ${error.message}`);
      results.warnings.push(`Failed to test settings tab: ${tab.text}`);
    }
  }

  // Summary
  console.log('\n\n=== Test Summary ===');
  console.log(`Total Tests: ${results.total}`);
  console.log(`Passed: ${results.passed}`);
  console.log(`Failed: ${results.failed}`);
  console.log(`Warnings: ${results.warnings.length}`);

  if (results.warnings.length > 0) {
    console.log('\nWarnings:');
    results.warnings.forEach(warning => {
      console.log(`  - ${warning}`);
    });
  }

  // Take final screenshot
  await page.screenshot({ path: 'test-results/final-screenshot.png', fullPage: true });

  console.log('\n✓ Testing complete!');
  console.log('Screenshots saved to: test-results/');
  console.log('\nPlease review the screenshots to identify any issues with interactive elements.');

  await browser.close();
})();
