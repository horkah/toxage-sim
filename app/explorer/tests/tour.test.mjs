import assert from "node:assert/strict";
import { test } from "node:test";

import { applies, textOf, clamp, fill, onPage, place, readSeconds, swipedLeft, words } from "../static/explorer/tour.js";
import { STEPS } from "../static/explorer/tour-steps.js";
import { STORIES } from "../static/explorer/stories/index.js";
import { AT } from "../static/explorer/stories/prerequisites.js";

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

test("the simple view leaves out the steps that need the full view, and uses its own texts", () => {
  assert.ok(!applies({ advanced: true }, "demo", false, {}, true));
  assert.ok(applies({ advanced: true }, "demo", false, {}, false));
  const simple = STEPS.filter((s) => applies(s, "demo", false, { A: 1 }, true));
  assert.ok(simple.length >= 30 && simple.length < STEPS.length);
  // The simple tour still creates its data set and deletes it again at the end.
  const titles = simple.map((s) => s.title);
  assert.ok(titles.includes("Generate") && titles.includes("Delete the first data set"));
  assert.ok(simple.every((s) => !s.target || !/parameters|records|archive|schema/.test(s.target + (s.url ?? ""))));
  const sections = STEPS.find((s) => s.title === "The sections");
  assert.notDeepEqual(textOf(sections, true), textOf(sections, false));
  assert.deepEqual(textOf({ text: ["a"] }, true), ["a"]);
});

test("the demo tells stories, each one shorter in the simple view", () => {
  assert.ok(STORIES.length >= 6);
  const used = new Set();
  for (const story of STORIES) {
    const advanced = story.steps.filter((s) => applies(s, "demo", false, { A: 1 }, false));
    const simple = story.steps.filter((s) => applies(s, "demo", false, { A: 1 }, true));
    assert.ok(advanced.length <= 25 && simple.length < advanced.length, story.title);
    // The first step shows the title and the choice of the story, in both views and before any change.
    assert.ok(!story.steps[0].advanced && !story.steps[0].changes && !story.steps[0].act, story.title);
    for (const s of story.steps) {
      assert.ok(s.title && s.text.length, `${story.title}: ${s.title}`);
      assert.ok(!s.at || s.target, `${story.title}: ${s.title}: unknown place ${s.at}`);
      assert.ok(!s.url || s.url.startsWith("/"), s.title);
      if (s.wait) assert.ok(s.until && !s.act, s.title);
      if (s.act) assert.equal(typeof s.act, "function", s.title);
      used.add(s.at);
    }
    // Read aloud: the story title and the texts, without symbols or brackets.
    for (const text of [story.title, ...story.steps.flatMap((s) => s.text)]) assert.ok(!/[()→›%]/.test(text), text);
  }
  // Every place of the app that a story needs is used, so prerequisites.js holds no more than that.
  assert.deepEqual(Object.keys(AT).filter((name) => !used.has(name)), []);
});
