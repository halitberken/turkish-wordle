import { expect, test, type Page } from "@playwright/test";

const turkishKey = (page: Page, key: string) =>
  page.evaluate((k) => document.body.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true })), key);

const states = (page: Page, row: number) =>
  page.locator(`#board .row:nth-child(${row}) .tile`).evaluateAll((tiles) => tiles.map((t) => (t as HTMLElement).dataset.state));

test("play a full game by typing, with the Turkish keyboard", async ({ page }) => {
  await page.goto("./?word=kalem#play");
  await expect(page.locator("body")).toHaveAttribute("data-ready", "true");

  // physical keyboard; "not in the word list" is rejected without using a row
  await page.keyboard.type("zzzzz");
  await page.keyboard.press("Enter");
  await expect(page.locator("#toast")).toHaveText("Not in the word list");
  for (let i = 0; i < 5; i++) await page.keyboard.press("Backspace");

  await page.keyboard.type("kapak");
  await page.keyboard.press("Enter");
  await expect.poll(() => states(page, 1)).toEqual(["correct", "correct", "absent", "absent", "absent"]);
  await expect(page.locator('.key[data-key="p"]')).toHaveAttribute("data-state", "absent"); // reveal finished

  // capital İ from a physical (Turkish) keyboard becomes dotted i (Turkish rules)
  await page.keyboard.type("ER");
  await turkishKey(page, "İ"); // Playwright's US key map has no İ key: send the event a Turkish keyboard sends
  await page.keyboard.type("KA");
  await page.keyboard.press("Enter");
  await expect(page.locator("#board .row:nth-child(2) .tile").nth(2)).toHaveText("İ");
  await expect.poll(() => states(page, 2)).toEqual(["present", "absent", "absent", "present", "present"]);
  await expect(page.locator('.key[data-key="e"]')).toHaveAttribute("data-state", "present");

  // the on-screen Turkish keyboard: dotless I and Ç
  for (const key of ["k", "ı", "l", "ı", "ç", "enter"]) await page.click(`.key[data-key="${key}"]`);
  await expect(page.locator("#board .row:nth-child(3) .tile").nth(1)).toHaveText("I");
  await expect.poll(() => states(page, 3)).toEqual(["correct", "absent", "correct", "absent", "absent"]);
  await expect(page.locator('.key[data-key="k"]')).toHaveAttribute("data-state", "correct");
  await expect(page.locator('.key[data-key="r"]')).toHaveAttribute("data-state", "absent");
  await expect(page.locator('.key[data-key="ç"]')).toHaveAttribute("data-state", "absent");

  await page.keyboard.type("kalem");
  await page.keyboard.press("Enter");
  await expect.poll(() => states(page, 4)).toEqual(Array(5).fill("correct"));
  await expect(page.locator("#result-text")).toHaveText("Solved in 4/6.");
  await expect(page.locator("#stats-dialog")).toBeVisible();

  // nothing scrolls sideways, even on a 360 px phone
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});

test("watch the entropy agent solve SAYMA like the Python agent", async ({ page }) => {
  await page.goto("./#watch");
  await expect(page.locator("body")).toHaveAttribute("data-ready", "true");
  await page.fill("#watch-word", "sayma");
  await page.selectOption("#watch-agent", "entropy");
  await page.click("#watch-play");
  await expect(page.locator("#watch-status")).toHaveText("Solved in 3 guesses.");
  const words = await page.locator("#watch-rows li .tiles").evaluateAll((rows) =>
    rows.map((r) => [...r.querySelectorAll(".tile")].map((t) => t.textContent).join("")));
  expect(words).toEqual(["KAMER", "SALYA", "SAYMA"]); // python scripts/play.py watch --word sayma
});
