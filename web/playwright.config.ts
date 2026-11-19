import { defineConfig, devices } from "@playwright/test";

// Locally, CHROMIUM_PATH can point to an installed Chromium (e.g. /usr/bin/chromium) instead of
// downloading Playwright's own build; in CI, `npx playwright install chromium` provides it.
const executablePath = process.env.CHROMIUM_PATH || undefined;
const launchOptions = executablePath ? { executablePath } : {};
const url = "http://localhost:4173/turkish-wordle/";

export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  reporter: [["list"]],
  use: { baseURL: url, launchOptions },
  webServer: {
    command: "npm run preview -- --port 4173 --strictPort",
    url,
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], launchOptions } },
    { name: "phone-360", use: { ...devices["Pixel 5"], viewport: { width: 360, height: 740 }, launchOptions } },
  ],
});
