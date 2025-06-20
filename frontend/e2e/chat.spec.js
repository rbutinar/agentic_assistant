const { test, expect } = require('@playwright/test');

test('user can start session and chat', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('text=Agentic Assistant')).toBeVisible();

  // Wait for input to be enabled
  await expect(page.locator('input[placeholder="Type your message..."]')).toBeEnabled();

  // Send a message
  await page.fill('input[placeholder="Type your message..."]', 'Hello agent!');
  await page.click('button:has-text("Send")');

  // Wait for assistant reply
  await expect(page.locator('.chat-message.assistant .content')).toContainText(/.+/);
});
