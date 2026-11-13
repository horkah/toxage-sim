import assert from "node:assert/strict";
import { test } from "node:test";

import { afterFailure, formUrl, matches, swappable } from "../static/explorer/app.js";

test("formUrl keeps the non-empty values of a form", () => {
  const url = formUrl("http://h/?old=1", [["tumour_type", "breast"], ["tumour_type", "prostate"], ["age_min", ""], ["view", "time"]]);
  assert.equal(url, "http://h/?tumour_type=breast&tumour_type=prostate&view=time");
});

test("swappable: pages of the app, not files, downloads or the disclaimer", () => {
  const origin = "http://h";
  const ok = (path) => swappable(new URL(path, origin), origin);
  assert.ok(ok("/"));
  assert.ok(ok("/data/3/records/?table=event"));
  assert.ok(ok("/parameters/risk/"));
  assert.ok(!ok("/static/explorer/style.css"));
  assert.ok(!ok("/data/3/export/outcome.csv"));
  assert.ok(!ok("/data/archive/"));
  assert.ok(!ok("/data/3/archive/"));
  assert.ok(!ok("/disclaimer/?next=/"));
  assert.ok(!swappable(new URL("https://example.org/"), origin));
});

test("matches finds every word in any order", () => {
  assert.ok(matches("Odds ratio ECOG 2 or higher", "ecog odds"));
  assert.ok(matches("anything", "  "));
  assert.ok(!matches("Odds ratio ECOG", "ecog age"));
});

test("afterFailure never repeats a sent form as a page load", () => {
  assert.equal(afterFailure("POST", false, false), "message");     // e.g. a deletion: no GET of /data/delete/
  assert.equal(afterFailure("POST", false, true), "ignore");       // the page is being left
  assert.equal(afterFailure("GET", false, false), "load");
  assert.equal(afterFailure("GET", false, true), "ignore");
  assert.equal(afterFailure("GET", true, false), "ignore");        // update of a part of the page
});
