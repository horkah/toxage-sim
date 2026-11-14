// Tutorial and demo of the app, without a framework.
//
// Both walk through the steps of tour-steps.js. A step shows a hint next to
// the control it is about. In the tutorial the user does what the hint says,
// and the tour goes on when it sees the result. In the demo the tour reads
// the hint for the user, does the step itself and goes on after a pause.
// The demo runs in an endless loop until it is stopped; before every new
// round the state before the demo is brought back. The right arrow key or a
// swipe to the left goes to the next step at once. The controls of the demo
// (pause, stop, speed) show on the first step and when the hint is clicked
// or touched; while they are shown the demo waits five seconds longer.
//
// A tour spans many pages. Pages are mostly swapped in place (app.js); the
// hint stays and is placed again after each swap. Its state is kept in the
// session storage of the tab, the speed of the demo and the offer at start in the local storage.
// Before a demo the server keeps a snapshot of parameters and data sets and
// brings it back at the end, so that the demo leaves no trace.

import { STEPS } from "./tour-steps.js";

const KEY = "toxage-tour";
// Reading time in seconds per 20 words (6.7 is 3 words per second), and the
// pause after each step in seconds.
const SPEED = { read: { key: "toxage-tourread", min: 0, max: 30, step: 0.1, fallback: 6.7 },
                pause: { key: "toxage-tourpause", min: 0.5, max: 10, step: 0.5, fallback: 2 } };
const HOLD = 5000;         // the demo waits this much longer while its controls are shown
const SWIPE = 60;          // pixels a finger must move to the left for "next"
const POLL = 400;
const PATIENCE = 240000;   // the demo gives up waiting for a result after this time

// Pure helpers, exported for the tests ---------------------------------------

// Number of words of a text.
export function words(text) {
  return (text.match(/\S+/g) || []).length;
}

// Seconds to read a text, given the seconds for 20 words.
export function readSeconds(text, secondsPer20Words) {
  return (words(text) / 20) * Math.max(0, secondsPer20Words);
}

// True for a movement of a finger that is a swipe to the left: far enough,
// and more sideways than up or down.
export function swipedLeft(dx, dy, min = SWIPE) {
  return dx <= -min && Math.abs(dy) < Math.abs(dx) * 0.6;
}

// Replace {name} by values that the tour remembered, e.g. the id of a data set.
export function fill(text, mem) {
  return text.replace(/\{(\w+)\}/g, (_, name) => (name in mem ? mem[name] : `{${name}}`));
}

// True if the page at `current` is the page that `wanted` names: the same
// path, and every query parameter of `wanted` with the same value.
export function onPage(current, wanted) {
  const a = new URL(current, "http://x"), b = new URL(wanted, "http://x");
  if (a.pathname !== b.pathname) return false;
  for (const [key, value] of b.searchParams) if (!a.searchParams.getAll(key).includes(value)) return false;
  return true;
}

// Steps that apply: some change data and are left out in read-only mode,
// some belong to one mode only, some need something an earlier step made.
export function applies(step, mode, readOnly, mem) {
  if (step.only && step.only !== mode) return false;
  if (step.changes && readOnly) return false;
  if (step.needs && !(step.needs in mem)) return false;
  return true;
}

// The value limited to [low, high].
export function clamp(value, low, high) {
  return Math.min(high, Math.max(low, value));
}

// Where to put a box of size (w, h) next to a target rectangle in a window
// of size (W, H): below if there is room, else above, else at the bottom.
export function place(target, w, h, W, H, gap = 12) {
  if (!target) return { left: clamp(W - w - 16, 8, W), top: clamp(H - h - 16, 8, H), side: "none" };
  const left = clamp(target.left + target.width / 2 - w / 2, 8, Math.max(8, W - w - 8));
  if (target.bottom + gap + h <= H) return { left, top: target.bottom + gap, side: "below" };
  if (target.top - gap - h >= 0) return { left, top: target.top - gap - h, side: "above" };
  return { left: clamp(W - w - 16, 8, W), top: clamp(H - h - 16, 8, H), side: "none" };
}

// Browser part ------------------------------------------------------------------

const browser = typeof document !== "undefined" && typeof sessionStorage !== "undefined";
let state = null;       // { mode, i, acted, shownAt, doneAt, paused, mem }
let panel = null, ring = null, timer = null, run = 0;

// A JSON value from session storage, fallback if missing or blocked.
function read(key, fallback = null) {
  try { return JSON.parse(sessionStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
// Keep the tour state in session storage, so that it survives a full page load.
function save() {
  try {
    if (state) sessionStorage.setItem(KEY, JSON.stringify(state));
    else sessionStorage.removeItem(KEY);
  } catch { /* storage blocked: the tour ends with the page */ }
}
// A speed value from local storage, limited to its range, else its default.
function setting(name) {
  const s = SPEED[name];
  let value = NaN;
  try { value = parseFloat(localStorage.getItem(s.key)); } catch { /* blocked */ }
  return Number.isFinite(value) ? clamp(value, s.min, s.max) : s.fallback;
}
// Keep a speed value in local storage; an empty value removes it.
function store(key, value) {
  try { if (value === "") localStorage.removeItem(key); else localStorage.setItem(key, value); } catch { /* blocked */ }
}
// The CSRF token of the page for the POST requests of the tour.
function csrf() {
  return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
}
// POST to an endpoint of the tour and return its JSON, {} on an error.
async function post(url) {
  const response = await fetch(url, { method: "POST", headers: { "X-CSRFToken": csrf() } });
  return response.ok ? response.json() : {};
}
let resume = null;      // wakes the current sleep early, e.g. for "next"
const sleep = (ms) => new Promise((resolve) => {
  resume = () => { clearTimeout(timer); resume = null; resolve(); };
  timer = setTimeout(() => { resume = null; resolve(); }, ms);
});

// What a step can use.
const api = {
  get mode() { return state.mode; },
  get mem() { return state.mem; },
  get readOnly() { return document.body.dataset.readOnly === "1"; },
  // The element of a selector; {A} etc. stand for remembered values; null if none or invalid.
  q(selector) {
    try { return document.querySelector(fill(selector, state.mem)); } catch { return null; }
  },
  has(part) { return location.search.includes(part); },
  on(url) { return onPage(location.href, fill(url, state.mem)); },
  go(url) { location.href = fill(url, state.mem); },
  click(selector) { api.q(selector)?.click(); },
  // Set a field like a user does: value, then input and change events.
  fill(selector, value) {
    const el = api.q(selector);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  },
  // Tick or untick a box by a click, so that the page reacts as to a user.
  check(selector, checked = true) {
    const el = api.q(selector);
    if (el && el.checked !== checked) el.click();
  },
  // The state of the app on the server: data sets, changed parameters, snapshot.
  async state() {
    try { return await (await fetch("/tour/state/")).json(); } catch { return { datasets: [], changes: {} }; }
  },
};

// All steps; a function so that tests and future variants can choose them.
function steps() {
  return STEPS;
}

// Open the groups that hide an element and scroll it to the middle of the window.
function reveal(el) {
  // Open the groups that hide the target, e.g. a filter group or the menu.
  // The handle of a group is visible while the group is closed, so it opens nothing.
  const from = el.tagName === "SUMMARY" ? el.parentElement : el;
  for (let node = from.parentElement; node; node = node.parentElement) {
    if (node.tagName === "DETAILS" && !node.open) node.open = true;
  }
  el.scrollIntoView({ block: "center", behavior: "instant" });
}

// Place the hint next to its target and the ring around it, or in the corner without a target.
function position() {
  if (!panel) return;
  const step = steps()[state.i];
  const el = step && step.target ? api.q(step.target) : null;
  const visible = el && el.getClientRects().length;
  const rect = visible ? el.getBoundingClientRect() : null;
  const spot = place(rect, panel.offsetWidth, panel.offsetHeight, innerWidth, innerHeight);
  panel.style.left = `${spot.left}px`;
  panel.style.top = `${spot.top}px`;
  panel.dataset.side = spot.side;
  if (rect) {
    ring.hidden = false;
    Object.assign(ring.style, { left: `${rect.left - 4}px`, top: `${rect.top - 4}px`,
                                width: `${rect.width + 8}px`, height: `${rect.height + 8}px` });
    panel.style.setProperty("--arrow", `${clamp(rect.left + rect.width / 2 - spot.left, 16, panel.offsetWidth - 16)}px`);
  } else {
    ring.hidden = true;
  }
}

// A range slider of a speed setting with its current value.
function slider(name, label, unit) {
  const s = SPEED[name];
  return `<label><span>${label}: <output>${setting(name)}</output> ${unit}</span>
    <input type="range" data-speed="${name}" min="${s.min}" max="${s.max}" step="${s.step}" value="${setting(name)}"></label>`;
}

// Both speed sliders of the demo.
function speedControls() {
  return `<div class="tour-speed">${slider("read", "Reading time", "seconds per 20 words")}
    ${slider("pause", "Pause after each step", "seconds")}</div>`;
}

// Save a speed setting while its slider moves, and show the value.
function bindSpeed(root) {
  for (const input of root.querySelectorAll("[data-speed]")) {
    input.addEventListener("input", () => {
      store(SPEED[input.dataset.speed].key, input.value);
      input.parentElement.querySelector("output").textContent = input.value;
      // Changing the speed counts as using the controls: the demo waits a little longer.
      if (state?.controls) hold();
    });
  }
}

// The controls of the demo: shown on the first step and on request.
function hold() {
  state.holdUntil = Date.now() + HOLD;
  save();
}

// Show or hide the controls of the demo; showing them holds the demo five seconds longer.
function toggleControls() {
  state.controls = !state.controls;
  state.holdUntil = state.controls ? Date.now() + HOLD : 0;
  save();
  panel?.querySelector(".tour-controls")?.toggleAttribute("hidden", !state.controls);
  panel?.querySelector("[data-tour=controls]")?.setAttribute("aria-expanded", String(state.controls));
  position();
}

// Draw the hint of a step: header, text, task, note and the buttons of the mode.
function show(step, note = "", free = false) {
  if (!panel) {
    ring = document.createElement("div");
    ring.className = "tour-ring";
    panel = document.createElement("section");
    panel.className = "tour";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-live", "polite");
    document.body.append(ring, panel);
    addEventListener("scroll", position, { passive: true });
    addEventListener("resize", position);
    panel.addEventListener("click", onPanelClick);
  }
  const demo = state.mode === "demo";
  // Count the steps of this mode; those that depend on an earlier step count too.
  const shown = steps().filter((s) => applies({ ...s, needs: null }, state.mode, noChanges(), state.mem));
  const number = shown.indexOf(step) + 1;
  const task = step.do ? `<p class="tour-do"><b>${demo ? "The demo does this next:" : "Your turn:"}</b> ${step.do}</p>` : "";
  let buttons;
  if (demo) {
    // The first step shows the controls, later steps on request.
    if (number <= 1 && (state.round || 1) <= 1 && state.controls === undefined) state.controls = true;
    buttons = `<button type="button" data-tour="pause">${state.paused ? "Resume" : "Pause"}</button>
      <button type="button" data-tour="stop">Stop the demo</button>`;
  } else {
    const next = step.wait && !free
      ? ""
      : step.act && !step.free && !free
        ? `<button type="button" data-tour="auto">Do it for me</button>`
        : `<button type="button" class="primary" data-tour="next">${state.i === steps().length - 1 ? "Finish" : "Next"}</button>`;
    buttons = `<button type="button" data-tour="back"${number <= 1 ? " disabled" : ""}>Back</button>${next}
      <button type="button" data-tour="stop">End the tutorial</button>`;
  }
  const round = demo && (state.round || 1) > 1 ? ` · round ${state.round}` : "";
  const toggle = demo
    ? `<button type="button" class="tour-toggle" data-tour="controls" aria-expanded="${Boolean(state.controls)}"
         title="Controls: pause, stop, speed">⋯</button>`
    : "";
  const controls = `<div class="tour-buttons">${buttons}</div>${demo ? speedControls() : ""}
    ${demo ? `<p class="tour-keys">Next step: → key or swipe to the left. Click the text to hide these controls.</p>`
           : `<p class="tour-keys">The → key or a swipe to the left also goes on, where “Next” is offered.</p>`}`;
  panel.innerHTML = `<header><span>${demo ? "Demo" : "Tutorial"}${round} · step ${number} of ${shown.length}</span>${toggle}</header>
    <h2>${step.title}</h2>${step.text.map((p) => `<p>${p}</p>`).join("")}${task}
    ${note ? `<p class="tour-note">${note}</p>` : ""}
    <div class="tour-controls"${demo && !state.controls ? " hidden" : ""}>${controls}</div>`;
  bindSpeed(panel);
  // Bring the target into view when the hint appears, not when it is drawn
  // again while waiting: the step itself may just have closed what held it.
  const el = step.target ? api.q(step.target) : null;
  if (el && !note) reveal(el);
  position();
  requestAnimationFrame(position);
}

// Remove hint and ring from the page.
function hide() {
  clearTimeout(timer);
  panel?.remove();
  ring?.remove();
  panel = ring = null;
  delete document.documentElement.dataset.tourAuto;
}

// Wait until the page has the answer to its running request, at most 60
// seconds. A deletion is done on the server before its answer arrives (giving
// back disk space takes a while); moving on earlier would cancel the request.
async function settled() {
  const started = Date.now();
  while (Number(document.documentElement.dataset.requests || 0) > 0 && Date.now() - started < 60000) {
    await sleep(POLL / 4);
  }
}

// Wait until the result of a step is there; the demo gives up after PATIENCE, the tutorial waits.
async function until(step, patient) {
  // Wait for the result of a step. Returns false if the tour moved on meanwhile.
  const mine = run, started = Date.now();
  for (;;) {
    if (mine !== run) return false;
    if (!step.until || await step.until(api)) {
      await settled();
      return mine === run;
    }
    if (!patient && Date.now() - started > PATIENCE) return true;
    await sleep(POLL);
  }
}

// All text of a hint, for its reading time.
function hintText(step) {
  return [step.title, ...step.text, step.do || ""].join(" ");
}

// Wait while the user reads. The time already spent on the hint counts,
// because a page may load again while a hint is shown.
async function reading(step) {
  const mine = run;
  for (;;) {
    if (mine !== run) return false;
    if (state.skip) return true;
    if (state.holdUntil > Date.now()) {
      state.shownAt += POLL;
      await sleep(POLL);
    } else if (!state.paused) {
      const left = readSeconds(hintText(step), setting("read")) * 1000 - (Date.now() - state.shownAt);
      if (left <= 0) return true;
      await sleep(Math.min(left, POLL));
    } else {
      state.shownAt += POLL;
      await sleep(POLL);
    }
  }
}

// Wait the pause after a step of the demo, longer while paused or while the controls are shown.
async function pausing() {
  const mine = run;
  for (;;) {
    if (mine !== run) return false;
    if (state.skip) return true;
    if (state.holdUntil > Date.now()) {
      state.doneAt += POLL;
      await sleep(POLL);
    } else if (!state.paused) {
      const left = setting("pause") * 1000 - (Date.now() - state.doneAt);
      if (left <= 0) return true;
      await sleep(Math.min(left, POLL));
    } else {
      state.doneAt += POLL;
      await sleep(POLL);
    }
  }
}

// Go to the next (by 1) or previous (by -1) step that applies.
function move(by) {
  // Go to the next (or previous) step that applies.
  let i = state.i + by;
  while (steps()[i] && !applies(steps()[i], state.mode, noChanges(), state.mem)) i += by;
  state.i = Math.max(0, i);
  state.acted = false;
  state.shownAt = state.doneAt = null;
  // A new step starts with the controls of the demo hidden and no wait or skip pending.
  state.skip = false;
  state.holdUntil = 0;
  state.controls = false;
  save();
}

// The right arrow key or a swipe to the left. The demo goes on at once
// (a result it waits for, such as a data set, still has to come); the
// tutorial goes on where it offers "Next".
function next() {
  if (!state) return;
  if (state.mode === "demo") {
    state.skip = true;
    state.holdUntil = 0;
    save();
    clearTimeout(timer);
    // Wake the waiting loop now instead of after its sleep.
    if (resume) resume();
  } else {
    panel?.querySelector('[data-tour="next"]')?.click();
  }
}

// True if the user is typing in a field, where the arrow keys belong to the field.
function typing(target) {
  return target.closest?.("input, select, textarea, [contenteditable]") !== null;
}

// The right arrow key goes to the next step.
function onKey(event) {
  if (!state || event.key !== "ArrowRight" || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
  if (typing(event.target) || document.querySelector("dialog[open]")) return;
  event.preventDefault();
  next();
}

let touch = null;
// Note where a finger touched the screen.
function onTouchStart(event) {
  const t = event.touches[0];
  // Swipes inside wide tables and form fields scroll or change them.
  touch = event.touches.length === 1 && !event.target.closest(".scroll, input, select, textarea")
    ? { x: t.clientX, y: t.clientY } : null;
}
// A swipe to the left goes to the next step.
function onTouchEnd(event) {
  if (!touch || !state) return;
  const t = event.changedTouches[0];
  if (swipedLeft(t.clientX - touch.x, t.clientY - touch.y)) next();
  touch = null;
}

// Run the current step: go to its page, show the hint, act or wait, then go on.
async function play() {
  const mine = ++run;
  clearTimeout(timer);
  const step = steps()[state.i];
  if (!step) return finish();
  if (!applies(step, state.mode, noChanges(), state.mem)) { move(1); return play(); }
  const demo = state.mode === "demo";
  document.documentElement.dataset.tourAuto = demo ? "1" : "0";

  if (state.acted) {
    // The step was done before the page loaded again: wait for its result.
    show(step, "Waiting for the result …");
    if (!await until(step, !demo)) return;
  } else {
    // A step of the tutorial may already be done, e.g. after the user's click loaded a new page.
    const done = !demo && (step.act || step.wait) && step.until && state.shownAt && await step.until(api);
    if (mine !== run) return;
    if (!done) {
      if (step.url && !api.on(step.url)) { api.go(step.url); return; }
      state.shownAt ??= Date.now();
      save();
      if (demo) {
        show(step);
        if (!await reading(step)) return;
        if (step.act || step.wait) {
          state.acted = true;
          save();
          if (step.act) await step.act(api);
          show(step, "Waiting for the result …");
          if (!await until(step, false)) return;
        }
      } else {
        // What the step asks for may already be the case; then "Next" goes on.
        const already = Boolean(step.until && await step.until(api));
        if (mine !== run) return;
        show(step, already ? "This is already the case here." : step.wait ? "Waiting for the result …" : "", already);
        if (already || step.free || !(step.act || step.wait)) return;     // the button "Next" goes on
        if (!await until(step, true)) return;
      }
    }
  }
  if (mine !== run) return;
  if (demo) {
    state.doneAt ??= Date.now();
    save();
    position();
    if (!await pausing()) return;
  }
  move(1);
  play();
}

// End of the tour: the demo starts its next round, unless it was stopped; then the state before it comes back.
async function finish(stopped = false) {
  run++;
  const demo = state.mode === "demo";
  const needsRestore = demo && Boolean(state.mem.owner);
  if (demo && !stopped) {
    // The demo runs in a loop: bring the state before the demo back and start again.
    const round = (state.round || 1) + 1;
    hide();
    if (needsRestore) await post("/tour/restore/");
    await begin("demo", round);
    location.href = "/";
    return;
  }
  state = null;
  save();
  hide();
  if (needsRestore) await post("/tour/restore/");
  const text = demo
    ? (stopped ? "The demo was stopped." : "The demo is over.")
      + (needsRestore ? " Parameters and data sets are as they were before the demo." : "")
    : (stopped ? "The tutorial was ended." : "You have seen every part of the app.")
      + " What you created or changed stays. Data sets can be deleted on the page “Data”, changed parameters reset on the page “Parameters”.";
  message(demo ? "Demo" : "Tutorial", text, needsRestore ? "/" : null);
}

// A dialog with a message; closing it can load a page.
function message(title, text, reload) {
  const dialog = document.createElement("dialog");
  dialog.className = "tour-dialog";
  dialog.innerHTML = `<h2>${title}</h2><p>${text}</p><form method="dialog"><button class="primary">Close</button></form>`;
  document.body.append(dialog);
  dialog.addEventListener("close", () => { dialog.remove(); if (reload) location.href = reload; });
  dialog.showModal();
}

// Buttons of the hint, and a click on the text of a demo hint that shows or hides the controls.
async function onPanelClick(event) {
  const action = event.target.closest("[data-tour]")?.dataset.tour;
  if (!action) {
    // A click on the text of a demo hint shows or hides the controls.
    if (state?.mode === "demo" && !event.target.closest(".tour-controls, a, button, input, label")) toggleControls();
    return;
  }
  if (action === "controls") return toggleControls();
  if (action === "stop") return finish(true);
  if (action === "pause") {
    state.paused = !state.paused;
    if (!state.paused) state.holdUntil = 0;
    save();
    event.target.textContent = state.paused ? "Resume" : "Pause";
    return;
  }
  if (action === "back") { move(-1); return play(); }
  if (action === "next") { move(1); return play(); }
  if (action === "auto") {
    const step = steps()[state.i];
    run++;
    state.acted = true;
    save();
    await step.act(api);
    play();
  }
}

// Note the state before a tour and set the tour to its first step.
// The demo notes the state on the server and gets a token that lets it change
// things, also in read-only mode; the server restores an earlier snapshot of
// this browser or an abandoned one first. If another demo is running, this one
// leaves out the steps that change something (owner false).
async function begin(mode, round = 1) {
  let owner = false;
  if (mode === "demo") {
    owner = Boolean((await post("/tour/snapshot/")).taken);
    // The page was drawn before the permission: its controls follow with the next page.
    if (owner) document.body.dataset.readOnly = "0";
  }
  const before = await api.state();
  state = { mode, i: 0, acted: false, shownAt: null, doneAt: null, paused: false, round,
            controls: undefined, holdUntil: 0, skip: false,
            mem: { known: before.datasets.map((d) => d.id), owner, readOnly: before.read_only } };
  save();
}

// True if the tour must leave out the steps that change something: read-only
// mode without the demo's permission, or another demo is running.
function noChanges() {
  if (state?.mode === "demo") return !state.mem.owner;
  return api.readOnly;
}

// Start a tour from its first step.
export async function start(mode) {
  if (state) { run++; hide(); }
  await begin(mode);
  for (const pop of document.querySelectorAll("details.popover[open]")) pop.open = false;
  play();
}

// The offer of the tours after the disclaimer, once per browser session.
function welcome() {
  const dialog = document.createElement("dialog");
  dialog.className = "tour-dialog";
  dialog.innerHTML = `<h2>Welcome to the toxage-sim explorer</h2>
    <p>The app shows synthetic patients with advanced cancer, their risk of severe side effects of therapy,
      and what early detection could change. Two guided tours explain every part of it.</p>
    <div class="tour-choice">
      <button type="button" class="primary" data-choice="tutorial">Tutorial</button>
      <p>Step by step. A hint points to each feature, and you click and type yourself.
        What you create or change stays until you remove it.</p>
      <button type="button" class="primary" data-choice="demo">Demo</button>
      <p>The same tour, running by itself in a loop until you stop it. It creates data and
        changes parameters, and puts everything back after each round. The → key or a swipe to
        the left goes to the next step; a click on the hint shows pause, stop and speed.</p>
    </div>
    ${speedControls()}
    <label class="check"><input type="checkbox" data-off> Do not offer this at start again
      <small>The menu has both tours at any time, and a setting to bring this offer back.</small></label>
    <div class="tour-buttons"><button type="button" data-choice="">Not now</button></div>`;
  document.body.append(dialog);
  bindSpeed(dialog);
  dialog.addEventListener("click", (event) => {
    const choice = event.target.closest("[data-choice]")?.dataset.choice;
    if (choice === undefined) return;
    if (dialog.querySelector("[data-off]").checked) store("toxage-welcome", "off");
    dialog.close();
    dialog.remove();
    if (choice) start(choice);
  });
  dialog.showModal();
}

// A note on top of the page when a demo did not finish, with a button to bring the state back.
function unfinished() {
  // A demo that did not reach its end, e.g. because the tab was closed.
  const note = document.createElement("div");
  note.className = "tour-unfinished";
  note.innerHTML = `A demo did not finish. Its data sets and parameter changes are still there.
    <button type="button" class="primary">Bring back the state before the demo</button>`;
  note.querySelector("button").addEventListener("click", async () => {
    await post("/tour/restore/");
    location.reload();
  });
  document.body.prepend(note);
}

// Set up the tours on a page: buttons, keys, swipes, and a running tour or the offer.
function init() {
  if (!document.querySelector(".mainnav")) return;      // not on the disclaimer
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-tour-start]");
    if (button) start(button.dataset.tourStart);
  });
  document.addEventListener("keydown", onKey);
  document.addEventListener("touchstart", onTouchStart, { passive: true });
  document.addEventListener("touchend", onTouchEnd, { passive: true });
  // A page swapped in place moves the target of the hint.
  document.addEventListener("toxage:swap", () => { if (panel) requestAnimationFrame(position); });
  state = read(KEY);
  if (state) return play();
  if (document.body.dataset.tourSnapshot === "1") unfinished();
  let off = false, seen = false;
  try {
    off = localStorage.getItem("toxage-welcome") === "off";
    seen = sessionStorage.getItem("toxage-welcome-seen") === "1";
    sessionStorage.setItem("toxage-welcome-seen", "1");
  } catch { /* storage blocked: offer on every page would annoy, so do not */ seen = true; }
  if (!off && !seen) welcome();
}

if (browser) {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
}
