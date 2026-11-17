// What the stories of the demo need from the app: named places with their page
// and CSS selector. A step of a story names one of them in `at`; its hint points
// there, and a step that acts (click, fill) acts there. A place marked `full`
// exists only in the full view, so its steps are left out in the simple view:
// this makes the short version of every story.
//
// When the app changes, this file is the one to update. `just check-stories`
// plays every story in both views and lists the places it did not find, with
// the steps that use them. Places that no story uses fail a test.

import { ECOG, card, created, param, ready } from "../tour-steps.js";

const page = (path, sel, full = false) => ({ page: path, sel, full });
const data = (sel, full) => page("/data/", sel, full);
const chart = (id, full) => page("/", `tox-chart[chart="${id}"]`, full);
const model = (id) => page("/", `nav[aria-label="Risk model"] a[data-model="${id}"]`);
const figure = (n, name) => page("/documents/risk-model/", `img[src$="/risk-model-${n}-${name}.png"]`);
const heading = (doc, id) => page(`/documents/${doc}/`, `#${id}`);

export const AT = {
  // Data: generate a data set and look at it
  "cohort-size": data('#generate input[name="n"]'),
  "cohort-limits": data("#generate details.limit", true),
  "cohort-seed": data('#generate input[name="seed"]', true),
  "cohort-scenarios": data("#generate fieldset", true),
  "calibrate-again": data('#generate input[name="recalibrate"]', true),
  generate: data('#generate button[type="submit"]'),
  "new-data-set": data(card("A")),
  "stored-records": data(`${card("A")} table`, true),
  "explore-data-set": data(`${card("A")} form[action="/data/use/"] button`),
  archive: data("#archive", true),
  records: page("/data/{A}/records/", "table.records", true),

  // Explorer: selection, models, patient
  filters: page("/", "#filters"),
  cohort: page("/", "#cohort"),
  random: page("/", "#random"),
  models: page("/", 'nav[aria-label="Risk model"]'),
  "model-severe90": model("severe90"),
  "model-ild": model("ild"),
  "model-neutropenia": model("neutropenia"),
  "model-diarrhoea": model("diarrhoea"),
  "model-cv": model("cv"),
  "patient-risk": page("/", ".panel.patient .riskcard"),
  "patient-events": page("/", ".charts .columns"),
  "scenario-table": page("/", ".charts table.numbers"),

  // Explorer: charts
  "risk-hist": chart("risk-hist"),
  calibration: chart("calibration"),
  incidence: chart("incidence"),
  "risk-age": chart("risk-age", true),
  "vs-severe90": chart("vs-severe90", true),
  "field-regimen": chart("field-regimen", true),
  "field-ga": chart("field-ga_impaired_domains", true),
  "field-adt": chart("field-adt_type", true),
  "field-prior-event": chart("field-prior_cardiovascular_event", true),
  "field-ugt1a1": chart("field-ugt1a1_28_homozygous", true),
  "patient-dose": chart("patient-dose"),
  "patient-neutrophils": chart("patient-neutrophils"),
  "patient-haemoglobin": chart("patient-haemoglobin", true),
  "patient-spo2": chart("patient-spo2"),
  "patient-pressure": chart("patient-pressure", true),
  "patient-symptoms": chart("patient-symptoms"),
  "iv-severe": chart("iv-severe"),
  "iv-hospital": chart("iv-hospital"),
  "iv-qaly": chart("iv-qaly", true),
  "iv-cost": chart("iv-cost"),
  "iv-lung": chart("iv-lung", true),
  "iv-heart": chart("iv-heart", true),
  "iv-lead": chart("iv-lead"),
  "iv-grade": chart("iv-grade"),
  "tte-os": chart("tte-os"),
  "tte-sfs": chart("tte-sfs"),
  "tte-severe": chart("tte-severe"),
  "tte-toxstop": chart("tte-toxstop"),
  "tte-reasons": chart("tte-reasons", true),
  "tte-heart": chart("tte-heart", true),

  // Parameters
  "ecog-odds-ratio": page("/parameters/risk/", param(ECOG), true),
  "parameter-basis": page("/parameters/parameters/", "form.params details", true),

  // Reference and About
  schema: page("/schema/", 'nav[aria-label="Tables"]'),
  "figure-1": figure(1, "severe-toxicity"),
  "figure-2": figure(2, "lung-toxicity"),
  "figure-3": figure(3, "neutropenia"),
  "figure-5": figure(5, "cardiovascular"),
  "report-older": heading("report", "older-patients"),
  "report-pancreas": heading("report", "toxicity-of-first-line-regimens"),
  "report-prostate": heading("report", "androgen-deprivation"),
  "full-texts": heading("references", "full-texts"),
  "lyman-2011": heading("references", "lyman-2011"),
  "overview-figure": page("/documents/", ".overview-figure img"),
  "about-figure": page("/about/", ".overview-figure img"),
};

// Parts of the steps that generate a data set and open it in the explorer.
export const GENERATE = { at: "generate", act: "click", until: created("A"), changes: true };
export const RUNNING = { at: "new-data-set", wait: true, until: ready("A"), changes: true, needs: "A" };
export const EXPLORE = { at: "explore-data-set", act: "click", until: () => location.pathname === "/", needs: "A" };

// Tick the boxes of the form "Generate" so that only the chosen tumour types,
// subgroups or regimens are left, e.g. { tumour_types: ["prostate"] }.
export const limit = (chosen) => () => {
  for (const box of document.querySelectorAll("#generate details.limit input[type=checkbox]")) {
    box.closest("details").open = true;
    const wanted = !chosen[box.name] || chosen[box.name].includes(box.value);
    if (box.checked !== wanted) box.click();
  }
};

// Select a random patient of the explorer state `query`. With `preferred`, it
// first looks at up to twelve random patients with these filters added, until
// the page of one matches `sign` (e.g. / days earlier/ in the table of events).
export const pick = (query, preferred = "", sign = null) => async (t) => {
  for (let i = 0; preferred && i < 12; i++) {
    try {
      const answer = await fetch(`/random/?${query}${preferred}`, { headers: { "X-Toxage-Fetch": "1" } });
      if (answer.url.includes("patient=") && (!sign || sign.test(await answer.text()))) return t.go(answer.url);
    } catch { /* try the next one */ }
  }
  return t.go(`/random/?${query}`);
};
