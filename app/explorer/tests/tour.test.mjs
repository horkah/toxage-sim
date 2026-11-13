import assert from "node:assert/strict";
import { test } from "node:test";

import { applies, clamp, fill, onPage, place, readSeconds, swipedLeft, words } from "../static/explorer/tour.js";
import { STEPS } from "../static/explorer/tour-steps.js";

test("words and reading time", () => {
  assert.equal(words("one two  three\nfour"), 4);
  assert.equal(words(""), 0);
  assert.equal(readSeconds("a ".repeat(20), 6.7), 6.7);     // seconds per 20 words
  assert.equal(readSeconds("a ".repeat(100), 2), 10);
  assert.equal(readSeconds("a ".repeat(100), 0), 0);       // 0: no time to read
  assert.equal(readSeconds("a b", -3), 0);
});

test("a swipe to the left is far enough and mostly sideways", () => {
  assert.ok(swipedLeft(-80, 10));
  assert.ok(!swipedLeft(-40, 0));           // too short
  assert.ok(!swipedLeft(80, 0));            // to the right
  assert.ok(!swipedLeft(-80, 70));          // rather downwards
});

test("fill replaces remembered values", () => {
  assert.equal(fill('article[data-id="{A}"]', { A: 7 }), 'article[data-id="7"]');
  assert.equal(fill("/data/{B}/records/", {}), "/data/{B}/records/");
});

test("onPage compares path and the wanted parameters", () => {
  assert.ok(onPage("http://h/?view=time&scenario=combined&patient=P1", "/?view=time&scenario=combined"));
  assert.ok(onPage("http://h/data/", "/data/"));
  assert.ok(!onPage("http://h/?view=risk", "/?view=time"));
  assert.ok(!onPage("http://h/data/", "/"));
  assert.ok(onPage("http://h/?tumour_type=breast&tumour_type=prostate", "/?tumour_type=breast"));
});

test("applies leaves steps out by mode, read-only state and memory", () => {
  assert.ok(applies({}, "demo", true, {}));
  assert.ok(!applies({ changes: true }, "demo", true, {}));
  assert.ok(applies({ changes: true }, "demo", false, {}));
  assert.ok(!applies({ only: "tutorial" }, "demo", false, {}));
  assert.ok(!applies({ needs: "A" }, "tutorial", false, {}));
  assert.ok(applies({ needs: "A" }, "tutorial", false, { A: 3 }));
});

test("place puts the hint below, above or in the corner", () => {
  const target = { left: 100, top: 100, bottom: 130, width: 80, height: 30 };
  assert.deepEqual(place(target, 200, 100, 1000, 800), { left: 40, top: 142, side: "below" });
  assert.equal(place({ ...target, top: 700, bottom: 730 }, 200, 100, 1000, 800).side, "above");
  assert.equal(place({ ...target, top: 50, bottom: 780 }, 200, 100, 1000, 800).side, "none");
  assert.equal(place(null, 200, 100, 1000, 800).side, "none");
  assert.equal(place({ ...target, left: 950 }, 200, 100, 1000, 800).left, 792);
  assert.equal(clamp(5, 1, 3), 3);
});

test("steps are well formed", () => {
  assert.ok(STEPS.length > 50);
  for (const step of STEPS) {
    assert.ok(step.title && step.text.length, step.title);
    assert.ok(!step.url || step.url.startsWith("/"), step.title);
    if (step.act) assert.ok(step.do && step.until, `${step.title}: a step that acts says what it does and when it is done`);
    if (step.wait) assert.ok(step.until && !step.act, step.title);
    if (step.do) assert.ok(step.act, step.title);
  }
});

test("every step that deletes or resets is marked as changing and can be passed in the tutorial", () => {
  for (const step of STEPS.filter((s) => /delete|reset/i.test(s.do || "") && !/filter/i.test(s.title))) {
    assert.ok(step.changes && step.free, step.title);
  }
});

test("the tour works without what it changes", () => {
  const readOnly = STEPS.filter((s) => applies(s, "demo", true, {}));
  assert.ok(readOnly.length > 35);
  assert.ok(readOnly.every((s) => !s.needs));
});
