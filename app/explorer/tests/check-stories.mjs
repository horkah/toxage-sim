// Play every story of the demo in the full and in the simple view, at full speed,
// and list the steps whose place (stories/prerequisites.js) was not found, and the
// steps that waited long for their result. Needs the app running with
// TOXAGE_SIMPLE_UI=1, so that both views exist, and Playwright.
// Usage: node app/explorer/tests/check-stories.mjs [address of the app] [story numbers]
import { createRequire } from "node:module";

const { chromium } = createRequire(import.meta.url)("playwright");
const [base = "http://localhost:8000", ...wanted] = process.argv.slice(2);
const { STORIES } = await import("../static/explorer/stories/index.js");
const numbers = wanted.length ? wanted.map(Number) : STORIES.map((_, i) => i + 1);
const SLOW = 60000;             // a step that waits longer than this is listed
const STUCK = 300000;           // and the story is given up after this

const browser = await chromium.launch();
let problems = 0;
for (const view of ["full", "simple"]) {
  for (const n of numbers) {
    const context = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
    await context.addCookies([{ name: "toxage_disclaimer", value: "1", url: base },
      ...(view === "full" ? [{ name: "toxage_ui", value: "advanced", url: base }] : [])]);
    await context.addInitScript(() => {
      localStorage.setItem("toxage-tourread", "0");
      localStorage.setItem("toxage-tourpause", "0.5");
      localStorage.setItem("toxage-welcome", "off");
    });
    const page = await context.newPage();
    const found = [];
    page.on("console", (m) => { if (m.text().startsWith("demo:")) found.push(m.text().replace(/^demo: /, "")); });
    page.on("pageerror", (e) => found.push(`error: ${e.message}`));
    await page.goto(`${base}/`);
    await page.evaluate(() => document.querySelector('[data-tour-start="demo"]').click());
    await page.selectOption(".tour select[data-story]", String(n - 1));
    // Follow the story until the demo goes on with the next one.
    const read = () => page.evaluate(() => JSON.parse(sessionStorage.getItem("toxage-tour") || "null")).catch(() => undefined);
    let step = -1, since = Date.now(), state;
    for (;;) {
      await page.waitForTimeout(500);
      state = await read();
      if (state === undefined) continue;            // the page is loading
      if (!state || state.story !== n - 1) break;
      if (Date.now() - since > STUCK) {
        found.push(`stuck at step "${STORIES[n - 1].steps[state.i]?.title}"`);
        break;
      }
      if (state.i !== step) {
        if (Date.now() - since > SLOW) found.push(`step "${STORIES[n - 1].steps[step]?.title}" waited ${Math.round((Date.now() - since) / 1000)} s`);
        step = state.i;
        since = Date.now();
      }
    }
    // Stop the next story once its hint is shown: the server then brings the state before the demo back.
    if (state) {
      try {
        await page.locator('.tour [data-tour="stop"]').dispatchEvent("click", {}, { timeout: 120000 });
        await page.waitForSelector("dialog.tour-dialog", { timeout: 60000 });
      } catch {
        await page.evaluate(() => fetch("/tour/restore/", { method: "POST",
          headers: { "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")?.value || "" } }));
      }
    }
    await context.close();
    const lines = [...new Set(found)];
    problems += lines.length;
    console.log(`Story ${n} "${STORIES[n - 1].title}", ${view} view: ${lines.length ? "" : "all places found"}`);
    for (const line of lines) console.log(`  ${line}`);
  }
}
await browser.close();
process.exit(problems ? 1 : 0);
