// Page behaviour without a framework.
//
// Navigation in place: links and forms of the app load the next page with
// fetch and swap the changed parts, so the page does not reload. Focus,
// scroll positions and opened groups are kept. Without JavaScript every link
// and form still works as a normal page load.
//
// Also here: settings, the warning before deleting, short messages
// (toasts), forms that apply on change, and the search in the parameters.
// Pure helpers are exported for the tests in explorer/tests/app.test.mjs.

const STORE = "toxage-";
const HEADER = "X-Toxage-Fetch";
const POLL = 2000;

// Pure helpers ---------------------------------------------------------------------

// Address of a GET form: the action with the non-empty values of the form.
export function formUrl(action, entries) {
  const url = new URL(action);
  url.search = "";
  for (const [key, value] of entries) {
    if (typeof value === "string" && value !== "") url.searchParams.append(key, value);
  }
  return url.href;
}

// Whether a URL is a page of the app that can be loaded in place.
export function swappable(url, origin) {
  if (url.origin !== origin) return false;
  const path = url.pathname;
  if (path.startsWith("/static/") || path.startsWith("/disclaimer")) return false;
  if (/\/(export|archive)\//.test(path) || path.endsWith(".csv")) return false;
  return true;
}

// What to do when a request of the page script fails without an answer:
// "ignore" when the page is being left (browsers such as Firefox cancel the
// running requests then and report it as an error) or for the update of a
// part of the page, which the next update repeats; "message" for a form that
// was sent, which must not be repeated as a page load (a GET of a POST
// address such as /data/delete/ is refused with 405); "load" to load a page
// address normally.
export function afterFailure(method, partial, leaving) {
  if (leaving || partial) return "ignore";
  return method === "GET" ? "load" : "message";
}

// True if a text matches every word of a search, ignoring case.
export function matches(text, query) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const hay = text.toLowerCase();
  return words.every((w) => hay.includes(w));
}

// Browser part ------------------------------------------------------------------------

const browser = typeof document !== "undefined" && typeof window !== "undefined";

function load(key) {
  try { return localStorage.getItem(STORE + key) || ""; } catch { return ""; }
}

function save(key, value) {
  try {
    if (value) localStorage.setItem(STORE + key, value);
    else localStorage.removeItem(STORE + key);
  } catch { /* storage blocked: the setting lasts for this page only */ }
}

function apply(key, value) {
  if (value) document.documentElement.dataset[key] = value;
  else delete document.documentElement.dataset[key];
}

function csrf() {
  return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
}

export function toast(text) {
  const box = document.querySelector(".toasts");
  if (!box || !text) return;
  const item = document.createElement("div");
  item.className = "toast";
  item.setAttribute("role", "status");
  item.textContent = text;
  box.append(item);
  setTimeout(() => { item.classList.add("out"); setTimeout(() => item.remove(), 350); }, 2800);
}

// Warning before deleting ---------------------------------------------------------------

// Ask with the red warning dialog. Resolves to true if the user confirms.
export function confirmDialog({ title, text, action }) {
  const dialog = document.getElementById("confirm");
  // The demo answers for the user.
  if (document.documentElement.dataset.tourAuto === "1") return Promise.resolve(true);
  if (!dialog?.showModal) return Promise.resolve(window.confirm(text));
  dialog.querySelector("h2").textContent = title || "Delete?";
  dialog.querySelector(".confirm-text").textContent = text || "";
  dialog.querySelector("button.danger").textContent = action || "Delete";
  return new Promise((resolve) => {
    dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), { once: true });
    dialog.returnValue = "";
    dialog.showModal();
  });
}

// Attributes of forms are read with getAttribute: a field named e.g. "dataset",
// "action" or "method" hides the property of the same name of its form.
const attr = (el, name) => el?.getAttribute(`data-${name}`) ?? null;

function question(form, submitter) {
  // The question of a button or a form; data-confirm-if names a radio value that needs it.
  const source = attr(submitter, "confirm") ? submitter : form;
  if (!attr(source, "confirm")) return null;
  const condition = attr(form, "confirm-if");
  if (source === form && condition && !form.querySelector(`input[value="${CSS.escape(condition)}"]:checked`)) return null;
  return { title: attr(source, "confirm-title"), text: attr(source, "confirm"), action: attr(source, "confirm-action") };
}

// Swapping pages in place --------------------------------------------------------------

let controller = null;
let pollTimer = null;
let shown = null;       // path and query of the page on screen
let leaving = false;    // the browser is leaving the page

const here = () => location.pathname + location.search;

function remember(root) {
  // What the swap should keep: open groups, scroll positions, focus.
  const open = {};
  for (const d of root.querySelectorAll("details[id]")) open[d.id] = d.open;
  const scroll = {};
  for (const el of root.querySelectorAll("[data-keep-scroll][id]")) scroll[el.id] = el.scrollTop;
  const el = document.activeElement;
  let focus = null;
  if (el && el !== document.body && root.contains(el)) {
    focus = {
      id: el.id, name: el.name, value: el.type === "checkbox" || el.type === "radio" ? el.value : null,
      typed: el.matches?.("input[type=text], input[type=search], input[type=number]") ? el.value : null,
      start: el.selectionStart ?? null,
    };
  }
  return { open, scroll, focus };
}

function restore(root, kept) {
  for (const [id, open] of Object.entries(kept.open)) {
    const d = root.querySelector(`details[id="${CSS.escape(id)}"]`);
    if (d) d.open = open;
  }
  for (const [id, top] of Object.entries(kept.scroll)) {
    const el = document.getElementById(id);
    if (el) el.scrollTop = top;
  }
  const f = kept.focus;
  if (!f) return;
  let el = f.id ? document.getElementById(f.id) : null;
  if (!el && f.name) {
    const all = [...root.querySelectorAll(`[name="${CSS.escape(f.name)}"]`)];
    el = all.find((x) => f.value === null || x.value === f.value) || all[0];
  }
  if (!el) return;
  // Keep what the user is typing while the page was loading.
  if (f.typed !== null && el.value !== f.typed) el.value = f.typed;
  el.focus({ preventScroll: true });
  if (f.start !== null && el.setSelectionRange) {
    try { el.setSelectionRange(f.start, f.start); } catch { /* not a text field */ }
  }
}

function swap(doc, only) {
  const main = document.getElementById("main");
  const next = doc.getElementById("main");
  if (only) {
    const target = document.querySelector(only), source = doc.querySelector(only);
    if (target && source) target.replaceWith(document.adoptNode(source));
  } else {
    const kept = remember(main);
    document.title = doc.title;
    for (const key of ["readOnly", "tourSnapshot", "section"]) {
      if (doc.body.dataset[key] !== undefined) document.body.dataset[key] = doc.body.dataset[key];
    }
    const nav = document.getElementById("nav"), newNav = doc.getElementById("nav");
    if (nav && newNav) nav.replaceWith(document.adoptNode(newNav));
    main.dataset.page = next.dataset.page;
    main.replaceChildren(...[...next.childNodes].map((n) => document.adoptNode(n)));
    restore(main, kept);
  }
  settle(document);
  document.dispatchEvent(new CustomEvent("toxage:swap", { detail: { only } }));
}

// Load a page in place. options: method, body, push (default true), only (a
// selector: swap just this part), keepScroll.
export async function visit(href, options = {}) {
  const url = new URL(href, location.href);
  const method = options.method || "GET";
  if (!swappable(url, location.origin)) { location.href = url.href; return; }
  if (!options.only) controller?.abort();
  const mine = options.only ? new AbortController() : (controller = new AbortController());
  document.documentElement.classList.add("loading");
  let response;
  try {
    response = await fetch(url.href, {
      method, body: options.body, signal: mine.signal, credentials: "same-origin",
      headers: { [HEADER]: "1", ...(method === "POST" ? { "X-CSRFToken": csrf() } : {}) },
    });
  } catch (error) {
    if (error.name === "AbortError") return;
    const next = afterFailure(method, Boolean(options.only), leaving);
    if (next === "load") location.href = url.href;
    else if (next === "message") toast("The server could not be reached. Please try again.");
    return;
  } finally {
    if (mine === controller || options.only) document.documentElement.classList.remove("loading");
  }
  // A page that answers a form in place says under which address it can be loaded again.
  const final = new URL(response.headers.get("X-Toxage-Location") || response.url, location.href);
  const html = (response.headers.get("content-type") || "").includes("text/html") ? await response.text() : null;
  if (mine.signal.aborted) return;
  const doc = html && new DOMParser().parseFromString(html, "text/html");
  // Leave the in-place mode for pages outside the app's frame, e.g. the disclaimer.
  if (!doc || !doc.getElementById("main") || !doc.getElementById("nav") || !swappable(final, location.origin)) {
    location.href = final.href;
    return;
  }
  const samePage = final.pathname === location.pathname;
  if (options.only) { swap(doc, options.only); return; }
  if (options.push !== false && final.href !== location.href) history.pushState({}, "", final.href);
  else if (final.href !== location.href) history.replaceState({}, "", final.href);
  swap(doc);
  shown = here();
  if (final.hash) revealHash();
  else if (!(options.keepScroll ?? samePage)) window.scrollTo(0, 0);
}

function onClick(event) {
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const link = event.target.closest("a[href]");
  if (!link || link.target || link.hasAttribute("download") || link.dataset.native !== undefined) return;
  const url = new URL(link.href, location.href);
  if (!swappable(url, location.origin)) return;
  // Anchors on the same page scroll as usual.
  if (url.pathname === location.pathname && url.search === location.search && url.hash) return;
  event.preventDefault();
  visit(url.href);
}

async function onSubmit(event) {
  const form = event.target;
  if (event.defaultPrevented || form.hasAttribute("data-native") || form.getAttribute("method") === "dialog") return;
  const submitter = event.submitter;
  const asked = question(form, submitter);
  // Read the attributes: a field named "action" or "method" hides the properties of the form.
  const method = (submitter?.getAttribute("formmethod") || form.getAttribute("method") || "get").toLowerCase();
  const action = new URL(submitter?.getAttribute("formaction") || form.getAttribute("action") || location.href, location.href);
  if (!swappable(action, location.origin)) {
    if (asked) {
      event.preventDefault();
      if (await confirmDialog(asked)) HTMLFormElement.prototype.submit.call(form);
    }
    return;
  }
  event.preventDefault();
  if (asked && !await confirmDialog(asked)) return;
  if (method === "get") {
    visit(formUrl(action.href, new FormData(form, submitter)));
  } else {
    visit(action.href, { method: "POST", body: new FormData(form, submitter), keepScroll: true });
  }
}

// Forms with data-auto apply on every change. Text fields wait for a pause.
let typing = null;
function onChange(event) {
  const form = event.target.form;
  if (!form || !form.hasAttribute("data-auto") || event.target.matches("[data-find]")) return;
  if (event.target.type === "file") return;
  // A field that follows another one goes back to its default when that one changes,
  // e.g. the comparison when the scenario changes.
  for (const el of form.querySelectorAll(`[data-clear-when="${CSS.escape(event.target.name)}"]`)) el.selectedIndex = -1;
  clearTimeout(typing);
  event.target.closest("tr")?.classList.add("saving");
  form.requestSubmit();
}

function onInput(event) {
  const el = event.target;
  if (el.matches("[data-find]")) return find(el);
  // Patient search fields of GET forms apply after a pause in typing.
  if (el.form?.hasAttribute("data-auto") && el.type === "search" && el.form.getAttribute("method") === "get") {
    clearTimeout(typing);
    typing = setTimeout(() => el.form.requestSubmit(), 600);
  }
}

function find(input) {
  const query = input.value.trim();
  const rows = document.querySelectorAll(input.dataset.find);
  for (const row of rows) row.hidden = query !== "" && !matches(row.textContent, query);
  // Open the groups that have hits, so that they can be seen.
  for (const group of document.querySelectorAll("#params details")) {
    const hits = group.querySelectorAll("tbody tr:not([hidden])").length;
    group.hidden = query !== "" && hits === 0;
    if (query && hits) group.open = true;
  }
}

// After every load or swap ----------------------------------------------------------------

// Open the groups that hide the target of the address' anchor, and show it.
function revealHash() {
  if (!location.hash) return;
  let target = null;
  try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch { return; }
  if (!target) return;
  for (let node = target; node; node = node.parentElement) {
    if (node.tagName === "DETAILS") node.open = true;
  }
  target.scrollIntoView({ block: target.tagName === "TR" ? "center" : "start" });
}

function settle(root) {
  for (const note of root.querySelectorAll("[data-toast]")) {
    toast(note.textContent.trim());
    note.remove();
  }
  for (const set of root.querySelectorAll("[data-setting]")) {
    const current = load(set.dataset.setting);
    for (const input of set.querySelectorAll("input")) input.checked = input.value === current;
  }
  // Data sets that are being generated: update their part of the page until
  // they are done, then the whole page once (e.g. the button "Generate").
  clearTimeout(pollTimer);
  const busy = root.querySelector("[data-poll]");
  if (busy) {
    const page = location.href;
    pollTimer = setTimeout(async () => {
      if (location.href !== page || !document.querySelector("[data-poll]")) return;
      await visit(page, { only: busy.dataset.poll, push: false });
      if (location.href === page && !document.querySelector("[data-poll]")) visit(page, { push: false, keepScroll: true });
    }, POLL);
  }
  const search = root.querySelector("[data-find]");
  if (search?.value) find(search);
}

function init() {
  document.addEventListener("click", onClick);
  document.addEventListener("submit", onSubmit);
  document.addEventListener("change", onChange);
  document.addEventListener("input", onInput);
  document.addEventListener("toxage:navigate", (event) => visit(event.detail));
  document.documentElement.dataset.router = "1";
  addEventListener("beforeunload", () => { leaving = true; });
  addEventListener("pagehide", () => { leaving = true; });
  addEventListener("pageshow", () => { leaving = false; });
  addEventListener("popstate", () => {
    // A jump to an anchor on the same page needs no load.
    if (here() === shown) return revealHash();
    visit(location.href, { push: false, keepScroll: false });
  });
  addEventListener("hashchange", revealHash);

  // Settings are kept in this browser.
  document.addEventListener("change", (event) => {
    const set = event.target.closest("[data-setting]");
    if (!set) return;
    save(set.dataset.setting, event.target.value);
    apply(set.dataset.setting, event.target.value);
  });

  // Close an open popover on a click outside it, or with Escape.
  document.addEventListener("click", (event) => {
    // A click in the hint of a tour does not count; its button may be gone by now.
    if (event.target.closest(".tour") || !event.target.isConnected) return;
    for (const pop of document.querySelectorAll("details.popover[open]")) {
      if (!pop.contains(event.target) || event.target.closest(".menuitem")) pop.open = false;
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") for (const pop of document.querySelectorAll("details.popover[open]")) pop.open = false;
  });
  shown = here();
  settle(document);
  revealHash();
}

if (browser) {
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
}
