// Render the figures of this folder to PNG: every HTML file with an element
// #figure is shot at 1.5x its size (1280 x 720 -> 1920 x 1080).
// Usage: node background/figures/render.mjs [name ...]
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const here = dirname(fileURLToPath(import.meta.url));
const wanted = process.argv.slice(2);
const files = readdirSync(here).filter((f) => f.endsWith(".html"))
  .filter((f) => !wanted.length || wanted.includes(f.replace(/\.html$/, "")));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
for (const file of files) {
  await page.goto(pathToFileURL(join(here, file)).href);
  await page.evaluate(() => document.fonts.ready);
  const figure = await page.$("#figure");
  if (!figure) continue;
  const out = join(here, file.replace(/\.html$/, ".png"));
  await figure.screenshot({ path: out });
  console.log(`rendered ${out}`);
}
await browser.close();
