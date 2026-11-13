// The steps of the tutorial and the demo.
//
// A step has a title and a text (list of paragraphs) and may have:
//   url      page on which the step is shown; the tour goes there first
//   target   CSS selector of the control that the hint points to
//   do       what is done in this step, as an instruction
//   act      function that does it (the demo calls it, the tutorial offers it)
//   until    function that says whether the result is there
//   wait     true: the step waits for `until` without anything being done
//   free     true: in the tutorial the step may be passed without doing it
//   changes  true: the step changes data or parameters (left out in read-only mode)
//   needs    name of a remembered value without which the step is left out
//   only     "tutorial" or "demo"
// {A} and {B} in selectors and addresses stand for the ids of the data sets
// that the tour created. Functions get the helper object of tour.js.

const card = (name) => `article.dataset[data-id="{${name}}"]`;
const param = (path) => `input[name="p:${path}"]`;
const ECOG = "severe_toxicity_90d/odds_ratios/ecog_2_or_higher/value";
const FLAGGED = "risk_adapted_start/share_flagged";

// A data set that was not there when the tour began or when the step before made one.
const created = (name) => async (t) => {
  const state = await t.state();
  const found = state.datasets.find((d) => !t.mem.known.includes(d.id));
  if (!found) return false;
  t.mem[name] = found.id;
  t.mem.known.push(found.id);
  return true;
};
const ready = (name) => (t) => t.q(`${card(name)}[data-status="ready"]`) !== null;
const gone = (name) => async (t) => !(await t.state()).datasets.some((d) => d.id === t.mem[name]);
// The table row of one parameter, and the same row while its value differs from the default.
const row = (path) => `tr:has(${param(path)})`;
const changedRow = (path) => `tr.changed:has(${param(path)})`;
const isChanged = (path) => (t) => t.q(changedRow(path)) !== null;
const isDefault = (path) => (t) => t.q(row(path)) !== null && t.q(changedRow(path)) === null;

export const STEPS = [
  // --- Start ------------------------------------------------------------------
  {
    title: "What this app is",
    text: [
      "The explorer shows synthetic patients with advanced pancreatic, prostate or breast cancer who start a systemic therapy. No real patient is in the data.",
      "Three parts work together. A data engine simulates each patient week by week. Risk models estimate the risk of severe side effects at therapy start. The app shows both, for a cohort and for one patient in relation to it.",
      "The tour goes through every part: creating data, reading the risk charts, following a patient over time, comparing interventions, changing model parameters, and removing everything again.",
    ],
  },
  {
    title: "The sections",
    target: ".mainnav",
    text: [
      "Five sections. “Explore” holds the charts. “Data” creates, inspects, exports and imports data sets. “Parameters” holds every number of the models. “Reference” has the data schema and the scientific background. “About” has the version and the authors.",
      "Pages change in place, without reloading. Objects are linked: a patient ID leads to the patient, a scenario to its charts, a field to its description in the schema.",
    ],
  },
  {
    title: "Help and settings",
    target: "#help summary",
    text: [
      "“Help” starts the tutorial or the demo at any time. “Settings” holds the bright or dark theme, the text size, and whether the tours are offered at start.",
    ],
    do: "Open the settings.",
    act: (t) => { const m = t.q("#settings"); if (m) m.open = true; },
    until: (t) => t.q("#settings[open]") !== null,
  },
  {
    title: "Settings",
    target: '#settings fieldset[data-setting="theme"]',
    text: [
      "Settings are kept in this browser. They do not change data or models.",
    ],
    do: "Close the settings again.",
    act: (t) => { const m = t.q("#settings"); if (m) m.open = false; },
    until: (t) => t.q("#settings[open]") === null,
  },

  // --- Data: create -------------------------------------------------------------
  {
    title: "Data sets",
    url: "/data/",
    target: ".page-head h1",
    text: [
      "A data set is one cohort of synthetic patients. Several can be stored side by side. The explorer shows one of them.",
      "The tour now creates a small data set of its own.",
    ],
  },
  {
    title: "Name",
    url: "/data/",
    target: '#generate input[name="name"]',
    changes: true,
    text: ["A name helps to tell data sets apart. Without one, the app uses the size and the seed."],
    do: "Enter a name, for example “Tour cohort”.",
    act: (t) => t.fill('#generate input[name="name"]', "Tour cohort"),
    until: (t) => (t.q('#generate input[name="name"]')?.value || "") !== "",
  },
  {
    title: "Number of patients",
    url: "/data/",
    target: '#generate input[name="n"]',
    changes: true,
    text: [
      "The patients are split equally over the three tumour types. Inside each type the engine forms subgroups: for example hormone-sensitive and castration-resistant prostate cancer, each with its own regimens, age and course.",
      "Small cohorts are quick but noisy. 300 patients are enough for the tour.",
    ],
    do: "Set the number of patients to 300.",
    act: (t) => t.fill('#generate input[name="n"]', "300"),
    until: (t) => t.q('#generate input[name="n"]')?.value === "300",
  },
  {
    title: "Seed",
    url: "/data/",
    target: '#generate input[name="seed"]',
    changes: true,
    text: [
      "The seed fixes all random decisions. The same seed with the same parameters gives exactly the same patients, so a result can be reproduced.",
    ],
  },
  {
    title: "Scenarios",
    url: "/data/",
    target: "#generate fieldset",
    changes: true,
    text: [
      "The engine simulates the same patients under several scenarios: usual care, a risk-adapted start of therapy, weekly symptom monitoring, home monitoring for lung toxicity, home monitoring for cardiovascular events, all of them combined, and perfect detection as an upper limit.",
      "Every patient has fixed random numbers. A patient therefore differs between two scenarios only from the point where an intervention acts. This makes the scenarios comparable patient by patient.",
    ],
  },
  {
    title: "Calibration",
    url: "/data/",
    target: '#generate input[name="recalibrate"]',
    changes: true,
    text: [
      "The engine is calibrated so that usual care reproduces the rates of severe side effects from the published trials. After a change of regimens or simulation parameters this has to be done again, which takes about a minute. With default parameters it is not needed.",
    ],
  },
  {
    title: "Generate",
    url: "/data/",
    target: '#generate button[type="submit"]',
    changes: true,
    text: ["Generating runs in the background on the server."],
    do: "Click “Generate”.",
    act: (t) => t.click('#generate button[type="submit"]'),
    until: created("A"),
  },
  {
    title: "Progress",
    url: "/data/",
    target: card("A"),
    changes: true,
    needs: "A",
    wait: true,
    text: [
      "The engine now simulates each patient under each scenario: every week adverse events can start, the dose can change, therapy can end, the patient can die. Follow-up runs until death or for ten years.",
      "The card updates itself until the data set is ready.",
    ],
    until: ready("A"),
  },
  {
    title: "What was stored",
    url: "/data/",
    target: `${card("A")} table`,
    needs: "A",
    text: [
      "Per scenario the data set holds one outcome per patient, the weekly observations while on therapy, the adverse events, and the alerts of the monitoring. Usual care has no alerts.",
    ],
  },
  {
    title: "Archive",
    url: "/data/",
    target: "#archive",
    text: [
      "“Export” on a data set, or “Export everything”, saves a file that can be imported later, also into another installation of the app. An import adds the data sets of the file, or replaces all data sets and parameter changes.",
    ],
  },
  {
    title: "Choose the data set",
    url: "/data/",
    target: `${card("A")} form[action="/data/use/"] button`,
    needs: "A",
    text: ["“Explore” makes this the data set of the explorer."],
    do: "Click “Explore”.",
    act: (t) => t.click(`${card("A")} form[action="/data/use/"] button`),
    until: (t) => location.pathname === "/",
  },

  // --- Explore: risk --------------------------------------------------------------
  {
    title: "The context",
    url: "/",
    target: "#context",
    text: [
      "The bar on top says what is shown: the data set, the scenario and the patient. Everything below follows it.",
    ],
  },
  {
    title: "Scenario",
    url: "/",
    target: "#scenario",
    text: [
      "All charts refer to one scenario and can be compared with a second one. The default is usual care, which is what the risk models describe: the risk at therapy start without an intervention.",
    ],
  },
  {
    title: "The cohort",
    url: "/",
    target: "#cohort",
    text: [
      "The panel on the left counts the selected patients. Each active filter shows here as a chip; a click on a chip removes it.",
    ],
  },
  {
    title: "Views",
    url: "/",
    target: 'nav[aria-label="View"]',
    text: [
      "Four views share the scenario, the filters and the selected patient: risk, patient characteristics, course over time, and interventions.",
    ],
  },
  {
    title: "Risk models",
    url: "/",
    target: 'nav[aria-label="Risk model"]',
    text: [
      "Each card is a risk model with the observed rate of its event, the mean predicted risk, and two measures of quality: the AUC says how well the model ranks patients (0.5 is chance, 1 is perfect), the Brier score how far the risks are from what happened (lower is better).",
      "Three risk models exist. The first estimates the risk of any severe side effect (grade 3 to 5) within 90 days. It starts from the published rate of the regimen and shifts it by age, performance status and impaired geriatric domains.",
      "The second estimates the risk of lung toxicity under trastuzumab deruxtecan, with six published risk factors such as low oxygen saturation and reduced renal function.",
      "The third estimates the risk of a heart attack, a stroke or cardiovascular death in the first year for men with prostate cancer under androgen deprivation.",
    ],
  },
  {
    title: "Distribution of predicted risk",
    url: "/",
    target: 'tox-chart[chart="risk-hist"]',
    text: [
      "Each bar is a band of predicted risk. The coloured part are the patients who had the event. If the model is good, the coloured share grows from left to right.",
      "A click on a bar filters the cohort to that risk band.",
    ],
  },
  {
    title: "Calibration",
    url: "/",
    target: 'tox-chart[chart="calibration"]',
    text: [
      "The patients are sorted by risk and split into ten groups. For each group the chart compares the mean predicted risk with the observed rate. On the dashed line prediction and observation agree.",
    ],
  },
  {
    title: "Cumulative incidence by risk group",
    url: "/",
    target: 'tox-chart[chart="incidence"]',
    text: [
      "The cohort is split into thirds by predicted risk. The curves show how the share of patients with the event grows over the days after therapy start. The further apart the curves, the better the model separates.",
    ],
  },
  {
    title: "Risk by age",
    url: "/",
    target: 'tox-chart[chart="risk-age"]',
    text: [
      "Each point is a patient. The bands are the regimens with their different base rates. A click on a point selects that patient.",
    ],
  },
  {
    title: "The second risk model",
    url: "/",
    target: 'nav[aria-label="Risk model"] a[href*="model=ild"]',
    text: ["All charts follow the chosen risk model."],
    do: "Click “Lung toxicity”.",
    act: (t) => t.click('nav[aria-label="Risk model"] a[href*="model=ild"]'),
    until: (t) => t.has("model=ild"),
  },
  {
    title: "Lung toxicity",
    url: "/?model=ild",
    target: 'nav[aria-label="Risk model"] a[data-model="ild"]',
    text: [
      "The model applies only to the regimens for which a rate is published, so it covers fewer patients. The engine uses the same published risk factors to generate lung toxicity, so this model ranks patients well by construction.",
      "For severe side effects the engine works differently from the model: a hidden frailty drives the events. That model therefore gains little over the plain rate of the regimen. This is a result, not an error.",
    ],
  },
  {
    title: "Risk across models",
    url: "/?model=ild",
    target: 'tox-chart[chart^="vs-"]',
    text: ["Each point is a patient for whom both models give a risk: is a patient at high risk for one outcome also at high risk for the other?"],
    do: "Click “Cardiovascular events”.",
    act: (t) => t.click('nav[aria-label="Risk model"] a[href*="model=cv"]'),
    until: (t) => t.has("model=cv"),
  },
  {
    title: "Cardiovascular events",
    url: "/?model=cv",
    target: 'nav[aria-label="Risk model"] a[data-model="cv"]',
    text: [
      "The third model covers the men with prostate cancer, who all get androgen deprivation. Its outcome is a heart attack, a stroke or cardiovascular death within the first year.",
      "The rates and the effect of an earlier event come from the HERO trial: under a GnRH agonist an earlier event raises the risk more than fourfold, under an antagonist hardly at all. The effects of age, diabetes, hypertension, smoking and renal function are assumptions.",
      "The engine adds factors the model does not know, such as frailty. The model therefore ranks patients well but predicts somewhat too few events.",
    ],
    do: "Go back to the first risk model.",
    act: (t) => t.click('nav[aria-label="Risk model"] a[href*="model=severe90"]'),
    until: (t) => t.has("model=severe90"),
  },

  // --- Explore: filters ------------------------------------------------------------
  {
    title: "Filters",
    url: "/",
    target: "#filters",
    text: [
      "Every field of the patient record and of the outcome has a filter, and every risk model a filter for its risk. They are built from the data schema, so a new field gets its filter by itself.",
    ],
    do: "Tick “breast” under “Tumour type”.",
    act: (t) => t.check('#filters input[name="tumour_type"][value="breast"]'),
    until: (t) => t.has("tumour_type=breast"),
  },
  {
    title: "A filtered cohort",
    url: "/?tumour_type=breast",
    target: "#cohort",
    text: [
      "All numbers and charts now refer to the patients with breast cancer; the chip shows the filter. The page changed in place, and its address holds the whole state: filters, scenario, view and patient. A view can be bookmarked or passed on.",
    ],
  },
  {
    title: "Reset the filters",
    url: "/?tumour_type=breast",
    target: "#filters-reset",
    text: ["“Reset all filters” removes all filters and keeps scenario, view and patient."],
    do: "Click “Reset all filters”.",
    act: (t) => t.click("#filters-reset"),
    until: (t) => !t.has("tumour_type="),
  },

  // --- Explore: one patient ----------------------------------------------------------
  {
    title: "Find a patient",
    url: "/",
    target: ".search",
    text: [
      "A patient is selected by ID, at random, or by a click on a point in a scatter plot. The number is enough: 42 stands for P000042.",
    ],
    do: "Enter 42 and click “Show”.",
    act: (t) => { t.fill('.search input[name="patient"]', "42"); t.click(".search button"); },
    until: (t) => t.has("patient="),
  },
  {
    title: "The patient",
    url: "/",
    target: ".panel.patient .facts",
    text: [
      "On top the key facts. Below: everything known at therapy start, such as tumour, regimen, age, performance status, blood values and comorbidity, and what happened to this patient in the selected scenario.",
      "Each name leads to its description in the data schema. “Records” shows the patient's rows in the data tables.",
    ],
  },
  {
    title: "The patient's risk",
    url: "/",
    target: ".panel.patient .riskcard",
    text: [
      "The cards of the risk models above now also show this patient's risk under each model. Below, the chosen model in detail: the patient's risk, the risk of a reference patient on the same regimen, the position among the selected patients, and what was observed.",
      "The bars show which factors raise or lower the risk and by how much. Together with the reference risk they give the patient's risk exactly.",
    ],
  },
  {
    title: "The patient in the cohort",
    url: "/",
    target: 'tox-chart[chart="risk-hist"]',
    text: [
      "The selected patient is marked in every chart: the risk band, a line at the patient's risk, a ring around the patient's point.",
    ],
  },
  {
    title: "A random patient",
    url: "/",
    target: "#random",
    text: ["“Random” picks a patient from the current selection."],
    do: "Click “Random”.",
    act: (t) => { t.mem.before = new URLSearchParams(location.search).get("patient"); t.click("#random"); },
    until: (t) => {
      const now = new URLSearchParams(location.search).get("patient");
      return now !== null && now !== (t.mem.before ?? "42") && now !== "P000042";
    },
  },

  // --- Explore: characteristics --------------------------------------------------------
  {
    title: "Patient characteristics",
    url: "/",
    target: 'nav[aria-label="View"] a[href*="view=characteristics"]',
    text: ["The second view looks at the cohort by each characteristic of the patients."],
    do: "Click “Patient characteristics”.",
    act: (t) => t.click('nav[aria-label="View"] a[href*="view=characteristics"]'),
    until: (t) => t.has("view=characteristics"),
  },
  {
    title: "Observed and predicted by group",
    url: "/?view=characteristics",
    target: 'tox-chart[chart="field-regimen"]',
    text: [
      "One chart per field. For each group it shows the observed rate, the mean predicted risk and the number of patients. Where the two bars differ, the model is off for this group.",
      "The group of the selected patient is marked. A click on a group filters by it.",
    ],
  },

  // --- Explore: time ----------------------------------------------------------------------
  {
    title: "Course over time",
    url: "/?view=characteristics",
    target: 'nav[aria-label="View"] a[href*="view=time"]',
    text: ["The engine follows every patient week by week. The third view shows this."],
    do: "Click “Course over time”.",
    act: (t) => t.click('nav[aria-label="View"] a[href*="view=time"]'),
    until: (t) => t.has("view=time"),
  },
  {
    title: "One patient, week by week",
    url: "/?view=time",
    target: 'tox-chart[chart="patient-dose"]',
    text: [
      "For the selected patient: the dose level, neutrophils, haemoglobin, platelets, oxygen saturation and four reported symptoms, for each week on therapy and shortly after.",
      "Vertical lines mark adverse events, alerts and the end of therapy. The values carry signals: blood counts fall with the dose, oxygen saturation falls from the true start of a lung toxicity, before it is recognised, and blood pressure and chest pain rise in the warning phase of a cardiovascular event.",
    ],
  },
  {
    title: "The patient's adverse events",
    url: "/?view=time",
    target: ".charts .columns",
    text: [
      "Each adverse event with the day it started, the day it was recognised, its grade, and what was done: pause, dose reduction or end of therapy. An event starts mild and worsens until it is recognised.",
    ],
  },
  {
    title: "The cohort over time",
    url: "/?view=time",
    target: 'tox-chart[chart="time-severe"]',
    text: [
      "For the selected patients: the share with a first severe adverse event, the share still on therapy, and survival over ten years. Most severe events come in the first weeks.",
    ],
  },

  // --- Explore: interventions ----------------------------------------------------------------
  {
    title: "Another scenario",
    url: "/?view=time",
    target: "#scenario-select",
    text: [
      "The same patients were simulated with interventions. “Combined” has a risk-adapted start of therapy for patients flagged as high risk, weekly symptom reports with alerts, and home monitoring for lung toxicity and for cardiovascular events.",
    ],
    do: "Choose the scenario “Combined”.",
    act: (t) => t.fill("#scenario-select", "combined"),
    until: (t) => t.has("scenario=combined"),
  },
  {
    title: "Two scenarios side by side",
    url: "/?view=time&scenario=combined",
    target: 'tox-chart[chart="patient-dose"]',
    text: [
      "The solid line is the selected scenario, the dashed line usual care. Where the lines lie on each other, the intervention did not reach this patient or changed nothing. Where they part, something was recognised earlier or the start of therapy was adapted.",
      "The two tables of adverse events show it in detail: the same event, recognised on an earlier day and at a lower grade.",
    ],
  },
  {
    title: "Interventions",
    url: "/?view=time&scenario=combined",
    target: 'nav[aria-label="View"] a[href*="view=interventions"]',
    text: ["The fourth view compares all scenarios."],
    do: "Click “Interventions”.",
    act: (t) => t.click('nav[aria-label="View"] a[href*="view=interventions"]'),
    until: (t) => t.has("view=interventions"),
  },
  {
    title: "Scenarios side by side",
    url: "/?view=interventions&scenario=combined",
    target: ".charts table.numbers",
    text: [
      "One row per scenario, for the same patients. An intervention works only as far as it reaches people: “Taking part” is lower in older and frailer patients, reports are missing in some weeks, patients drop out, and not every alert is acted on.",
      "Monitoring also costs: most alerts are false. The last columns give quality-adjusted life years and costs against usual care. The costs are placeholders, so these columns show how the model works, not a result.",
      "A click on the name of a scenario selects it.",
    ],
  },
  {
    title: "Charts of the scenarios",
    url: "/?view=interventions&scenario=combined",
    target: 'tox-chart[chart="iv-severe"]',
    text: [
      "The same numbers as bars. “Perfect detection” is the upper limit: everyone takes part and every event is caught at its first stage. The distance between a scenario and this limit is what participation, sensitivity and timing cost.",
      "A click on a bar selects that scenario.",
    ],
  },
  {
    title: "Early recognition",
    url: "/?view=interventions&scenario=combined",
    target: 'tox-chart[chart="iv-lead"]',
    text: [
      "For the events that monitoring recognised: how many days earlier than usual care, and at which grade instead of the grade they would have reached. Most events worsen within days, so a weekly report often comes too late. Lung toxicity develops over weeks, so monitoring gains more there. Of the cardiovascular events only those with a warning phase can be caught; the others come without notice, also with perfect detection.",
    ],
  },
  {
    title: "Back to usual care",
    url: "/?view=interventions&scenario=combined",
    target: "#scenario-select",
    text: ["The effects of the scenarios follow from assumed parameters. The next part shows where these parameters are."],
    do: "Choose the scenario “Usual care” again.",
    act: (t) => t.fill("#scenario-select", "usual_care"),
    until: (t) => t.has("scenario=usual_care"),
  },

  // --- Parameters --------------------------------------------------------------------------------
  {
    title: "Model parameters",
    url: "/parameters/parameters/",
    target: ".page-head h1",
    text: [
      "Every number of the models is here. The defaults are files of the repository. A changed value is stored in the database of the app and stays until it is reset.",
    ],
  },
  {
    title: "Four parameter files",
    url: "/parameters/parameters/",
    target: 'nav[aria-label="Parameter file"]',
    text: [
      "“Regimens” has the published rates of each therapy. “Simulation” has the population, the hazards of adverse events, survival and the measurements. “Interventions” has participation, detection, early treatment, costs and the scenarios. “Risk models” has the coefficients of the three risk models.",
      "Below the files, the groups of the open file lead straight to their place. The field “Find a parameter” narrows the list as you type.",
    ],
  },
  {
    title: "Values, defaults and their basis",
    url: "/parameters/parameters/",
    target: "form.params details",
    text: [
      "Each group states where its values come from: a published source or an assumption of this project. Each row shows the current value and the default.",
    ],
  },
  {
    title: "Parameters of the risk models",
    url: "/parameters/parameters/",
    target: 'nav[aria-label="Parameter file"] a[href="/parameters/risk/"]',
    text: ["Risk model parameters act on the explorer at once, because the risks are computed when a page is shown."],
    do: "Click “Risk models”.",
    act: (t) => t.click('nav[aria-label="Parameter file"] a[href="/parameters/risk/"]'),
    until: (t) => location.pathname === "/parameters/risk/",
  },
  {
    title: "Change a value",
    url: "/parameters/risk/",
    target: param(ECOG),
    changes: true,
    text: [
      "This is the odds ratio for a performance status of ECOG 2 or higher in the model for severe side effects. The default of 2 is an assumption.",
    ],
    do: "Set the value to 4 and leave the field, with Tab or Enter.",
    act: (t) => t.fill(param(ECOG), "4"),
    until: isChanged(ECOG),
  },
  {
    title: "A changed value",
    url: "/parameters/risk/",
    target: changedRow(ECOG),
    changes: true,
    text: [
      "A value is saved as soon as its field is left; a short message confirms it. The changed row is marked, the default stays visible, and the files and groups on the left count the changes. A value that does not fit, such as text for a number, is refused with a note.",
    ],
  },
  {
    title: "The effect in the explorer",
    url: "/?model=severe90&ecog_min=2",
    target: 'nav[aria-label="Risk model"] a[data-model="severe90"]',
    changes: true,
    text: [
      "The explorer, filtered to patients with ECOG 2 or higher. With the doubled odds ratio the model now predicts a much higher risk than is observed: on the card of the model, the mean predicted risk lies well above the observed rate.",
    ],
  },
  {
    title: "Reset one value",
    url: "/parameters/risk/",
    target: `button[value="reset:${ECOG}"]`,
    changes: true,
    free: true,
    text: ["The arrow ↺ next to a changed value brings its default back."],
    do: "Click ↺ in the marked row.",
    act: (t) => t.click(`button[value="reset:${ECOG}"]`),
    until: isDefault(ECOG),
  },
  {
    title: "Parameters of the engine",
    url: "/parameters/interventions/",
    target: param(FLAGGED),
    changes: true,
    text: [
      "Engine parameters act on data sets generated from then on. This one is the share of patients that the risk prediction at therapy start flags as high risk. The default is 0.3.",
    ],
    do: "Set the value to 0.5 and leave the field.",
    act: (t) => t.fill(param(FLAGGED), "0.5"),
    until: isChanged(FLAGGED),
  },

  // --- Data: a second data set, inspect, delete -------------------------------------------------------
  {
    title: "A data set with changed parameters",
    url: "/data/",
    target: "#generate",
    changes: true,
    text: [
      "The form now says that a parameter differs from the defaults. A new data set will use it. Calibrating again is not needed here, because this parameter does not touch usual care.",
    ],
    do: "Enter the name “Tour cohort B”, set 150 patients, and click “Generate”.",
    act: (t) => {
      t.fill('#generate input[name="name"]', "Tour cohort B");
      t.fill('#generate input[name="n"]', "150");
      t.check('#generate input[name="recalibrate"]', false);
      t.click('#generate button[type="submit"]');
    },
    until: created("B"),
  },
  {
    title: "Generating",
    url: "/data/",
    target: card("B"),
    changes: true,
    needs: "B",
    wait: true,
    text: ["The same patients as in the first data set would come out with the same seed and size; only the flagged share differs."],
    until: ready("B"),
  },
  {
    title: "Data sets remember their parameters",
    url: "/data/",
    target: `${card("B")} header`,
    needs: "B",
    text: [
      "The new data set shows that one parameter was changed when it was made. Stored data sets keep the values they were made with, whatever is changed later.",
    ],
  },
  {
    title: "Inspect the records",
    url: "/data/",
    target: `${card("B")} a[href$="/records/"]`,
    needs: "B",
    text: ["Every record of a data set can be read."],
    do: "Click “Inspect records”.",
    act: (t) => t.click(`${card("B")} a[href$="/records/"]`),
    until: (t) => location.pathname.endsWith("/records/"),
  },
  {
    title: "Tables",
    url: "/data/{B}/records/",
    target: 'nav[aria-label="Table"]',
    needs: "B",
    text: [
      "Six tables in the layout of the data schema: scenarios, baseline, outcome, adverse events, alerts and weekly observations.",
    ],
    do: "Click “event”.",
    act: (t) => t.click('nav[aria-label="Table"] a[href*="table=event"]'),
    until: (t) => t.has("table=event"),
  },
  {
    title: "Records",
    url: "/data/{B}/records/?table=event",
    target: "table.records",
    needs: "B",
    text: [
      "Each adverse event with its grade, the day it started and the day it was recognised. Two columns say what would have happened in usual care; for an event found through monitoring the difference is the gain.",
      "The records can be limited to a scenario and to one patient, and downloaded as CSV files for other tools.",
    ],
  },
  {
    title: "Delete a scenario",
    url: "/data/",
    target: `${card("B")} form:has(input[name="scenario"][value="perfect_detection"]) button`,
    changes: true,
    needs: "B",
    free: true,
    text: [
      "Data can be removed in parts. Deleting a scenario removes the courses of all patients in it. The space on disk is given back at once.",
    ],
    do: "Click “delete scenario” in the row “Perfect detection” and confirm the warning.",
    act: (t) => t.click(`${card("B")} form:has(input[name="scenario"][value="perfect_detection"]) button`),
    until: async (t) => {
      const d = (await t.state()).datasets.find((x) => x.id === t.mem.B);
      return !d || !d.scenarios.includes("perfect_detection");
    },
  },
  {
    title: "Delete a data set",
    url: "/data/",
    target: `${card("B")} .actions form[action="/data/delete/"] button`,
    changes: true,
    needs: "B",
    free: true,
    text: ["“Delete data set” removes it with all its scenarios."],
    do: "Click “Delete data set” of “Tour cohort B” and confirm the warning.",
    act: (t) => t.click(`${card("B")} .actions form[action="/data/delete/"] button`),
    until: gone("B"),
  },
  {
    title: "Reset a group of parameters",
    url: "/parameters/interventions/",
    target: 'form.params button[value="reset_source"]',
    changes: true,
    free: true,
    text: [
      "“Reset this file” brings all values of this file back to the defaults, “Reset everything” those of all four files.",
    ],
    do: "Click “Reset this file” and confirm.",
    act: (t) => t.click('form.params button[value="reset_source"]'),
    until: isDefault(FLAGGED),
  },
  {
    title: "Delete the first data set",
    url: "/data/",
    target: `${card("A")} .actions form[action="/data/delete/"] button`,
    changes: true,
    needs: "A",
    free: true,
    text: [
      "With the last data set of the tour gone and the parameters reset, the app is as it was before.",
    ],
    do: "Click “Delete data set” of the first data set of the tour and confirm the warning.",
    act: (t) => t.click(`${card("A")} .actions form[action="/data/delete/"] button`),
    until: gone("A"),
  },

  // --- Reference --------------------------------------------------------------------------------------
  {
    title: "The data schema",
    url: "/schema/",
    target: 'nav[aria-label="Tables"]',
    text: [
      "The engine, the risk models and the app share one description of the data: seven tables, each field with title, type, allowed values, unit and meaning. Filters, charts and labels of the app are built from it.",
      "Field names in the patient card and in the records lead here.",
    ],
  },
  {
    title: "Reference",
    url: "/documents/",
    target: ".cards",
    text: [
      "The reference holds the data schema and the documents behind the models: the report on therapy toxicity with its 28 references, the intervention model, and the descriptions of the data engine and the risk models.",
    ],
    do: "Open the “Toxicity report”.",
    act: (t) => t.click('a[href="/documents/report/"]'),
    until: (t) => location.pathname === "/documents/report/",
  },
  {
    title: "The scientific background",
    url: "/documents/report/",
    target: "#reference-nav",
    text: [
      "The report collects what trials and guidelines say about side effects of therapy in the three tumour types, and derives ten candidates for risk models. The app implements the first two.",
      "The rates of the regimens in the engine, the risk factors of lung toxicity and the rates of cardiovascular events come from these sources. Effect sizes of the interventions, costs and quality-of-life weights are assumptions.",
    ],
  },
  {
    title: "About",
    url: "/about/",
    target: "#authors",
    text: [
      "Who made the app and how, and which version runs here. The version and the build also stand in the footer of every page, next to the link to the disclaimer.",
    ],
  },
  {
    title: "The end",
    url: "/",
    target: "#help summary",
    text: [
      "That was every part of the app. Tutorial and demo can be started again under “Help”, and the offer at start can be switched off and on under “Settings”.",
    ],
  },
];
