const fs = require('node:fs')
const path = require('node:path')
const { chromium } = require('playwright')
const AxeBuilder = require('@axe-core/playwright').default

const baseUrl = process.env.NG_DS_BASE_URL || 'http://127.0.0.1:4174'
const widths = [390, 430, 768, 1024, 1440, 1920]
const screenshotWidths = new Set([390, 768, 1440, 1920])
const output = path.resolve(__dirname, '..', '..', 'artifacts', 'design-system-v2', 'screenshots')

async function prepare(page) {
  await page.route('**/auth/me', (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ username: 'design-system-reviewer', role: 'validation' }),
  }))
}

async function viewport(browser, width) {
  const context = await browser.newContext({ viewport: { width, height: 1000 }, locale: 'fa-IR' })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await prepare(page)
  const response = await page.goto(`${baseUrl}/design-system`, { waitUntil: 'networkidle' })
  await page.locator('[data-trace-id="NG-DS-V2-LAB"]').waitFor()
  const layout = await page.evaluate(() => ({
    direction: getComputedStyle(document.documentElement).direction,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    sections: document.querySelectorAll('.ng-lab-section').length,
    productName: document.body.innerText.includes('Negin AI'),
  }))
  const axe = await new AxeBuilder({ page }).include('[data-trace-id="NG-DS-V2-LAB"]').withTags(['wcag2a','wcag2aa','wcag21aa']).analyze()
  const serious = axe.violations.filter((item) => ['serious','critical'].includes(item.impact))
  if (screenshotWidths.has(width)) {
    fs.mkdirSync(output, { recursive: true })
    await page.screenshot({ path: path.join(output, `neginai-design-system-v2-${width}.png`), fullPage: true })
  }
  const result = { width, status: response && response.status(), ...layout, pageErrors: errors, seriousAxe: serious.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => ({ target: n.target, summary: n.failureSummary })) })) }
  await context.close()
  if (result.status !== 200 || result.direction !== 'rtl' || result.overflow > 1 || result.sections !== 18 || !result.productName || errors.length || serious.length) throw new Error(JSON.stringify(result))
  return result
}

async function interactions(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'fa-IR', reducedMotion: 'reduce' })
  const page = await context.newPage()
  await prepare(page)
  await page.goto(`${baseUrl}/design-system`, { waitUntil: 'networkidle' })
  await page.locator('#lab-11').scrollIntoViewIfNeeded()
  const tabs = page.locator('#lab-11 [role="tab"]')
  await tabs.first().focus()
  await page.keyboard.press('ArrowLeft')
  const keyboardTab = await tabs.nth(1).getAttribute('aria-selected')
  await page.locator('#lab-06 button', { hasText: 'نمایش Modal' }).click()
  const modalVisible = await page.locator('.ng-modal').isVisible()
  await page.keyboard.press('Escape')
  const modalClosed = !(await page.locator('.ng-modal').isVisible())
  const targets = await page.locator('button:not(:disabled),input:not([type="checkbox"]):not([type="radio"]):not(:disabled),select:not(:disabled),textarea:not(:disabled)').evaluateAll((nodes) => nodes.filter((node) => {
    const r = node.getBoundingClientRect()
    return r.width > 0 && r.height > 0 && (r.width < 43.5 || r.height < 43.5)
  }).map((node) => ({ tag: node.tagName, label: node.getAttribute('aria-label') || node.textContent.trim().slice(0,30), width: node.getBoundingClientRect().width, height: node.getBoundingClientRect().height })))
  const motion = await page.locator('.ng-motion-sample').evaluate((el) => getComputedStyle(el).animationDuration)
  await context.close()
  const result = { keyboardTab, modalVisible, modalClosed, undersizedTargets: targets, reducedMotionDuration: motion }
  if (keyboardTab !== 'true' || !modalVisible || !modalClosed || targets.length || motion !== '0s') throw new Error(JSON.stringify(result))
  return result
}

async function main() {
  const browser = await chromium.launch({ channel: 'chrome', headless: true })
  try {
    const responsive = []
    for (const width of widths) responsive.push(await viewport(browser, width))
    console.log(JSON.stringify({ responsive, interactions: await interactions(browser), screenshots: output }, null, 2))
  } finally { await browser.close() }
}
main().catch((error) => { console.error(error); process.exitCode = 1 })
