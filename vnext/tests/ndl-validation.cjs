const { chromium } = require('playwright')
const AxeBuilder = require('@axe-core/playwright').default

const baseUrl = process.env.NDL_BASE_URL || 'http://127.0.0.1:4174'
const viewports = [390, 430, 768, 1024, 1440, 1920]

async function authorizeValidationRoute(page) {
  await page.route('**/auth/me', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ username: 'validation-user', role: 'validation' }),
  }))
}

async function validateViewport(browser, width) {
  const context = await browser.newContext({ viewport: { width, height: 900 }, locale: 'fa-IR' })
  const page = await context.newPage()
  const pageErrors = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  await authorizeValidationRoute(page)
  const response = await page.goto(`${baseUrl}/design-system`, { waitUntil: 'networkidle' })
  await page.locator('[data-trace-id="NDL-VALIDATION-001"]').waitFor()
  const layout = await page.evaluate(() => ({
    direction: document.documentElement.dir,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    componentCount: document.querySelectorAll('[class*="ndl-"]').length,
  }))
  const axe = await new AxeBuilder({ page })
    .include('[data-trace-id="NDL-VALIDATION-001"]')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze()
  const materialViolations = axe.violations.filter(({ impact }) => impact === 'critical' || impact === 'serious')
  const result = {
    width,
    status: response?.status(),
    overflow: layout.scrollWidth - layout.clientWidth,
    direction: layout.direction,
    componentCount: layout.componentCount,
    pageErrors,
    materialAxeViolations: materialViolations.map(({ id }) => id),
  }
  await context.close()
  if (!response?.ok() || layout.direction !== 'rtl' || result.overflow > 1 || pageErrors.length || materialViolations.length) {
    throw new Error(`Viewport validation failed: ${JSON.stringify(result)}`)
  }
  return result
}

async function validateInteraction(browser) {
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    locale: 'fa-IR',
    reducedMotion: 'reduce',
  })
  const page = await context.newPage()
  await authorizeValidationRoute(page)
  await page.goto(`${baseUrl}/design-system`, { waitUntil: 'networkidle' })

  const tabs = page.getByRole('tab')
  await tabs.first().focus()
  await page.keyboard.press('ArrowLeft')
  const selectedTabIndex = await tabs.evaluateAll((nodes) =>
    nodes.findIndex((node) => node.getAttribute('aria-selected') === 'true'),
  )

  const overlayActions = page.locator('.ndl-validation__section').nth(5).locator('.ndl-button')
  await overlayActions.nth(0).click()
  const dialogVisible = await page.locator('.ndl-dialog').isVisible()
  await page.keyboard.press('Escape')
  const dialogClosedWithEscape = !(await page.locator('.ndl-dialog').isVisible())
  const reducedMotionDuration = await page.locator('.ndl-skeleton span').first()
    .evaluate((element) => getComputedStyle(element).animationDuration)
  const undersizedTouchTargets = await page.locator('button:not(:disabled), input:not(:disabled)').evaluateAll((nodes) =>
    nodes.filter((node) => {
      const rect = node.getBoundingClientRect()
      const visible = rect.width > 0 && rect.height > 0
      return visible && (rect.width < 43.5 || rect.height < 43.5)
    }).map((node) => ({
      tag: node.tagName,
      label: node.getAttribute('aria-label') || node.textContent?.trim().slice(0, 40),
      width: node.getBoundingClientRect().width,
      height: node.getBoundingClientRect().height,
    })),
  )

  await context.close()
  const result = { selectedTabIndex, dialogVisible, dialogClosedWithEscape, reducedMotionDuration, undersizedTouchTargets }
  if (selectedTabIndex !== 1 || !dialogVisible || !dialogClosedWithEscape || reducedMotionDuration !== '0s' || undersizedTouchTargets.length) {
    throw new Error(`Interaction validation failed: ${JSON.stringify(result)}`)
  }
  return result
}

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  try {
    const responsive = []
    for (const width of viewports) responsive.push(await validateViewport(browser, width))
    const interaction = await validateInteraction(browser)
    console.log(JSON.stringify({ responsive, interaction }, null, 2))
  } finally {
    await browser.close()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
