import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

async function openAnonymousLogin(page: Page) {
  await page.route('**/auth/me', (route) => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'unauthorized' }),
  }))
  await page.goto('/')
  await expect(page.locator('#keyDialog')).toBeVisible()
}

test('NUI-001 preserves login controls, states, accessibility, and auth transition', async ({ page }) => {
  await page.route('**/auth/login', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 180))
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ username: 'operator', role: 'seller' }),
    })
  })
  await openAnonymousLogin(page)

  await expect(page.locator('nav')).toHaveCount(0)
  await expect(page.locator('.ng-login-brand .ng-brand-name')).toHaveText('Negin AI')
  await expect(page.locator('#username')).toHaveAttribute('autocomplete', 'username')
  await expect(page.locator('#password')).toHaveAttribute('autocomplete', 'current-password')
  await expect(page.locator('#keyDialog')).toHaveAttribute('data-auth-state', 'default')

  await page.locator('#username').focus()
  const focusRing = await page.locator('#username').locator('..').evaluate((element) => getComputedStyle(element).boxShadow)
  expect(focusRing).not.toBe('none')

  await page.locator('#password').fill('secret')
  await page.locator('#togglePasswordVisibility').click()
  await expect(page.locator('#password')).toHaveAttribute('type', 'text')
  await expect(page.locator('#togglePasswordVisibility')).toHaveAttribute('aria-pressed', 'true')

  await page.locator('#username').fill('operator')
  await page.getByRole('button', { name: 'ورود به Negin AI' }).click()
  await expect(page.locator('#keyDialog')).toHaveAttribute('data-auth-state', 'loading')
  await expect(page.getByRole('status')).toContainText('ورود موفق بود')
  await expect(page.locator('nav')).toBeVisible()
})

test('NUI-001 reports validation errors and has no serious axe violations', async ({ page }) => {
  await openAnonymousLogin(page)
  await page.getByRole('button', { name: 'ورود به Negin AI' }).click()
  await expect(page.locator('#loginError')).toBeVisible()
  await expect(page.locator('#username')).toHaveAttribute('aria-describedby', 'loginError')
  await expect(page.locator('#password')).toHaveAttribute('aria-invalid', 'true')

  const results = await new AxeBuilder({ page }).include('#keyDialog').analyze()
  const material = results.violations.filter((violation) => ['serious', 'critical'].includes(violation.impact ?? ''))
  expect(material).toEqual([])
})

test('NUI-001 exposes offline feedback and disabled submit semantics', async ({ page, context }) => {
  await openAnonymousLogin(page)
  await context.setOffline(true)
  await expect(page.locator('#keyDialog')).toHaveAttribute('data-auth-state', 'offline')
  await expect(page.getByText('آفلاین هستید؛ برای ورود به اینترنت متصل شوید.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'ورود به Negin AI' })).toBeDisabled()
  await context.setOffline(false)
})

test('NUI-001 is overflow-free at required responsive widths', async ({ page }, testInfo) => {
  await openAnonymousLogin(page)
  for (const width of [390, 430, 768, 1024, 1440, 1920]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(0)
    if (width === 390 || width === 1440) {
      await page.screenshot({ path: testInfo.outputPath(`nui-001-${width}.png`), fullPage: true })
    }
  }
})

test.describe('Android browser', () => {
  test.use({ userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/123 Mobile Safari/537.36' })

  test('preserves the Android download action', async ({ page }) => {
    await openAnonymousLogin(page)
    await expect(page.locator('#androidDownloadLogin')).toHaveAttribute('href', '/download/android')
  })
})
