// Tests of the chart helpers. Run with: node --test app/explorer/tests/
import { test } from "node:test";
import assert from "node:assert/strict";
import { esc, fmt, linePath, niceStep, niceTicks, scale, withParams } from "../static/explorer/charts.js";

test("esc escapes markup", () => {
  assert.equal(esc(`<a href="x">&'`), "&#60;a href=&#34;x&#34;&#62;&#38;&#39;");
});

test("niceStep picks round steps", () => {
  assert.equal(niceStep(0.23), 0.25);
  assert.equal(niceStep(7), 10);
  assert.equal(niceStep(3), 5);
  assert.equal(niceStep(0), 1);
});

test("niceTicks covers the range", () => {
  assert.deepEqual(niceTicks(0, 1), [0, 0.2, 0.4, 0.6, 0.8, 1]);
  assert.deepEqual(niceTicks(32, 88), [20, 40, 60, 80, 100]);
  assert.deepEqual(niceTicks(32, 88, 10), [30, 40, 50, 60, 70, 80, 90]);
  const ticks = niceTicks(0, 0);
  assert.ok(ticks.length >= 2);
});

test("scale maps linearly and survives a zero domain", () => {
  const s = scale(0, 10, 100, 200);
  assert.equal(s(5), 150);
  assert.equal(scale(3, 3, 0, 10)(3), 5);
});

test("fmt formats percent, integers and numbers", () => {
  assert.equal(fmt(0.1234, "pct"), "12.3%");
  assert.equal(fmt(0.5, "pct"), "50%");
  assert.equal(fmt(64.6, "int"), "65");
  assert.equal(fmt(1.2345), "1.23");
  assert.equal(fmt(null, "pct"), "–");
});

test("linePath draws lines and steps", () => {
  const id = (v) => v;
  assert.equal(linePath([[0, 0], [10, 5]], id, id), "M0.0,0.0L10.0,5.0");
  assert.equal(linePath([[0, 0], [10, 5]], id, id, true), "M0.0,0.0H10.0V5.0");
});

test("withParams replaces parameters and keeps the rest", () => {
  const href = "http://host/?sex=male&regimen=a&patient=P1";
  assert.equal(withParams(href, { patient: "P2" }), "/?sex=male&regimen=a&patient=P2");
  assert.equal(withParams(href, { regimen: ["b", "c"] }), "/?sex=male&patient=P1&regimen=b&regimen=c");
  assert.equal(withParams("http://host/", { risk_min: 10, risk_max: 20 }), "/?risk_min=10&risk_max=20");
});
