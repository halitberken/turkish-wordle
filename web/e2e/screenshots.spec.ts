// Screenshots for the documentation: SCREENSHOTS=1 npx playwright test screenshots
// (writes ../docs/demo/web-*.png; skipped in normal test runs).

import { expect, test, type Page } from "@playwright/test";

test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to update the screenshots in docs/demo/");

const OUT = process.env.SCREENSHOT_DIR ?? "../docs/demo";

async function ready(page: Page, url: string, theme: "light" | "dark") {
  await page.addInitScript((t) => localStorage.setItem("kelime-avi:settings", JSON.stringify({ theme: t, contrast: false })), theme);
  await page.goto(url);
  await expect(page.locator("body")).toHaveAttribute("data-ready", "true");
}

async function guess(page: Page, word: string, lastKey: string) {
  await page.keyboard.type(word);
  await page.keyboard.press("Enter");
  await expect(page.locator(`.key[data-key="${lastKey}"]`)).toHaveAttribute("data-state", /.+/);
}

// One curated shot per page: play in light (desktop) and dark (phone), watch, assist (phone), about.
const only = (project: string) => test.skip(test.info().project.name !== project, `only on ${project}`);

for (const [theme, project] of [["light", "desktop"], ["dark", "phone-360"]] as const) {
  test(`play (${theme})`, async ({ page }, info) => {
    only(project);
    await ready(page, "./?word=sayma#play", theme);
    await guess(page, "kamer", "r");
    await guess(page, "salya", "y");
    await page.screenshot({ path: `${OUT}/web-play-${theme}-${info.project.name}.png` });
  });
}

test("watch", async ({ page }, info) => {
  only("desktop");
  await ready(page, "./#watch", "light");
  await page.fill("#watch-word", "sayma");
  await page.selectOption("#watch-agent", "frequency");
  await page.click("#watch-play");
  await expect(page.locator("#watch-status")).toHaveText(/Solved/, { timeout: 20_000 });
  await page.screenshot({ path: `${OUT}/web-watch-${info.project.name}.png`, fullPage: true });
});

test("assist", async ({ page }, info) => {
  only("phone-360");
  await ready(page, "./#assist", "light");
  await expect(page.locator("#assist-suggestion")).toContainText("KAMER");
  await page.click("#assist-suggestion button");
  await page.locator("#assist-tiles .tile").nth(1).click();
  await page.locator("#assist-tiles .tile").nth(1).click();
  await page.click("#assist-add");
  await expect(page.locator("#assist-facts")).toContainText("candidates left");
  await page.screenshot({ path: `${OUT}/web-assist-${info.project.name}.png`, fullPage: true });
});

test("about", async ({ page }, info) => {
  only("desktop");
  await ready(page, "./#about", "dark");
  await page.screenshot({ path: `${OUT}/web-about-${info.project.name}.png`, fullPage: true });
});
