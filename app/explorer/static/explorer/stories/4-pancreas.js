// Story 4: metastatic pancreatic cancer. Almost every patient is hit; the two
// regimens differ in the kind of toxicity; diarrhoea, a gene variant, and weekly
// symptom reports.

import { EXPLORE, GENERATE, RUNNING, limit, pick } from "./prerequisites.js";

const PANCREAS = "tumour_type=pancreas";
// Patients with severe diarrhoea under symptom monitoring, compared with usual care;
// the story prefers one who took part, had an alert and was recognised earlier.
const REPORTS = `view=time&model=diarrhoea&${PANCREAS}&scenario=symptom_monitoring&compare=usual_care&severe_diarrhoea_90d=true`;
const MONITORED = "&participating=true&alerts_min=1";

export default {
  title: "Nine in ten",
  steps: [
    {
      title: "Where therapy is hardest",
      url: "/",
      text: [
        "I am the AI that built this app. This story is about metastatic pancreatic cancer, where time is short and therapy is hard.",
        "In the trial behind the newest first-line regimen, almost nine in ten patients had a severe side effect, with either of the two regimens it compared. The burden was the same. Its shape was not: one regimen hits the gut, the other the blood and the nerves.",
      ],
    },
    {
      title: "Reading before writing",
      at: "cohort-size",
      act: ["fill", "1500"],
      changes: true,
      text: [
        "The first thing I did for this project was not to write code, but to read: trials, guidelines and meta-analyses. From them I took, for every regimen, how often each side effect occurs and when.",
        "Out of these numbers I make fifteen hundred patients.",
      ],
    },
    {
      title: "Only pancreatic cancer",
      at: "cohort-limits",
      act: limit({ tumour_types: ["pancreas"] }),
      changes: true,
      text: [
        "This time all of them have pancreatic cancer. Two regimens are in play: NALIRIFOX, and gemcitabine with nab-paclitaxel. The guidelines choose the first-line chemotherapy by the condition of the patient and by bilirubin.",
        "That is risk stratification by expected tolerance, written into clinical practice already.",
      ],
    },
    {
      title: "Calibrated to the trials",
      at: "calibrate-again",
      text: [
        "One box I leave as it is. When parameters change, the engine has to be calibrated again: I adjust its hazards until usual care reproduces the published rates of each regimen. With the default parameters this is done already.",
      ],
    },
    {
      ...GENERATE,
      title: "A side effect grows",
      text: [
        "In my engine a side effect does not appear at its final grade. It starts mild and grows week by week until someone notices. The day it is noticed decides how bad it gets.",
        "That is the lever of every monitoring.",
      ],
    },
    {
      ...RUNNING,
      title: "Reports every week",
      text: [
        "One of the worlds I simulate gives every patient a weekly symptom report. Severe or worsening symptoms raise an alert, and a nurse can call back. A large trial of exactly this improved physical function, symptom control and quality of life.",
      ],
    },
    {
      ...EXPLORE,
      title: "Into the data",
      text: ["The cohort is ready."],
    },
    {
      title: "One in five, one in twenty",
      url: `/?view=risk&model=diarrhoea&${PANCREAS}`,
      at: "model-diarrhoea",
      text: [
        "My fourth model predicts severe diarrhoea within ninety days. With NALIRIFOX one patient in five was affected in the trial, with gemcitabine and nab-paclitaxel one in twenty. Low potassium came three to four times as often with NALIRIFOX as well.",
        "For a patient who is already thin and weak, a few days of it mean dehydration and a trip to hospital.",
      ],
    },
    {
      title: "Mostly the regimen",
      url: `/?model=diarrhoea&${PANCREAS}&view=characteristics`,
      at: "field-regimen",
      text: [
        "Observed rate and predicted risk by regimen. The model gets the two regimens right, and that is most of what it knows.",
      ],
    },
    {
      title: "A gene that matters",
      url: `/?model=diarrhoea&${PANCREAS}&view=characteristics`,
      at: "field-ugt1a1",
      text: [
        "Some patients carry two copies of a gene variant, UGT1A1*28, that slows the breakdown of the active form of irinotecan, a part of NALIRIFOX. My model doubles their odds of severe diarrhoea.",
        "To be honest with you: this effect size is an assumption. The literature names the risk factor, but gives no number for this regimen.",
      ],
    },
    {
      title: "Days at home",
      url: `/?view=interventions&scenario=symptom_monitoring&${PANCREAS}`,
      at: "iv-hospital",
      text: [
        "Now the worlds side by side. With weekly symptom reports, side effects are treated earlier, and the patients spend fewer days in hospital. For a patient with little time left, every day at home counts.",
      ],
    },
    {
      title: "One patient's reports",
      url: `/?${REPORTS}${MONITORED}`,
      at: "random",
      act: pick(REPORTS, MONITORED, / days earlier/),
      until: (t) => t.has("patient="),
      text: ["I pick a patient with severe diarrhoea who sent weekly reports."],
    },
    {
      title: "The line that rises",
      at: "patient-symptoms",
      text: [
        "The weekly reports of this patient. In my engine, diarrhoea rises in the week before the event. The report raises an alert, and treatment starts before the event is fully grown.",
      ],
    },
    {
      title: "The dose",
      at: "patient-dose",
      text: [
        "And the dose, in both worlds. A severe event means a pause or a reduced dose. Where the solid line stays higher, the earlier treatment kept the therapy going.",
      ],
    },
    {
      title: "Quality of life",
      url: `/?view=interventions&scenario=symptom_monitoring&${PANCREAS}`,
      at: "iv-qaly",
      text: [
        "Quality-adjusted life years per patient. I compute them from quality-of-life weights per week. The weights come from a single study of breast cancer, so read this as how the model works, not as a result.",
      ],
    },
    {
      title: "And what it costs",
      url: `/?view=interventions&scenario=symptom_monitoring&${PANCREAS}`,
      at: "iv-cost",
      text: [
        "Monitoring costs money, and most alerts are false. Many of my unit costs are placeholders, and the app says so. A real health economic evaluation would start here, not end.",
      ],
    },
    {
      title: "Survival",
      url: `/?view=interventions&scenario=symptom_monitoring&${PANCREAS}`,
      at: "tte-os",
      text: [
        "Overall survival hardly differs between the worlds. In my model, earlier recognition saves life only where a side effect would have killed. For these patients the gain is in time without suffering, not in time itself.",
      ],
    },
    {
      title: "The sources",
      at: "report-pancreas",
      text: [
        "My report on the literature has the numbers of the trial and of a meta-analysis of seven trials, regimen by regimen. Every number in it comes from the texts I read, and every claim links to its source.",
        "Survival with NALIRIFOX and with FOLFIRINOX was similar, so the choice between them is largely a choice of toxicity. A model that tells in advance which toxicity a patient will suffer could make that choice personal.",
      ],
    },
  ],
};
