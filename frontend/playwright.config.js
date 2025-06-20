// @ts-check
/** @type {import('@playwright/test').PlaywrightTestConfig} */
const config = {
  webServer: {
    command: 'npm start',
    port: 3000,
    timeout: 120 * 1000,
    reuseExistingServer: !process.env.CI,
    cwd: './frontend'
  },
  testDir: './e2e',
  use: {
    baseURL: 'http://localhost:3000',
    headless: true
  }
};
module.exports = config;
