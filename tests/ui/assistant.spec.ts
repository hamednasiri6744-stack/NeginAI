import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

async function openAssistant(page: import('@playwright/test').Page) {
  const response = await page.goto('/assistant', { waitUntil: 'domcontentloaded' });
  expect(response, 'assistant response').not.toBeNull();
  expect(response?.ok(), `assistant returned ${response?.status()}`).toBeTruthy();
  await expect(page.locator('#app')).toBeVisible();
}

test.describe('NeginAI assistant shell', () => {
  test('loads the existing RTL product shell without changing visual identity', async ({ page }) => {
    await openAssistant(page);

    await expect(page.locator('html')).toHaveAttribute('lang', 'fa');
    await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
    await expect(page.locator('meta[name="viewport"]')).toHaveAttribute('content', /viewport-fit=cover/);
    await expect(page.locator('meta[name="theme-color"]')).toHaveAttribute('content', '#0d0e0c');

    await expect(page.locator('#sidebar')).toBeAttached();
    await expect(page.locator('.main-panel')).toBeVisible();
    await expect(page.locator('#messages')).toBeVisible();
    await expect(page.locator('.composer-area')).toBeVisible();
    await expect(page.locator('#openSidebarBtn')).toBeAttached();
  });

  test('keeps the top-level shell inside the viewport on desktop and mobile profiles', async ({ page }) => {
    await openAssistant(page);

    const dimensions = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      innerWidth: window.innerWidth,
    }));

    expect(dimensions.clientWidth).toBeGreaterThan(0);
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 2);
    expect(dimensions.bodyScrollWidth).toBeLessThanOrEqual(dimensions.innerWidth + 2);
  });

  test('has no critical automated WCAG violations in the assistant shell', async ({ page }) => {
    await openAssistant(page);

    const scan = await new AxeBuilder({ page })
      .include('#app')
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    const critical = scan.violations.filter((violation) => violation.impact === 'critical');
    expect(
      critical,
      critical.map((item) => `${item.id}: ${item.help}`).join('\n'),
     ).toHaveLength(0);
  });
});
