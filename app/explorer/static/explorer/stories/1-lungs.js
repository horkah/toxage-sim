// Story 1: women with HER2-low breast cancer on trastuzumab deruxtecan, whose lung
// toxicity starts quietly; one patient in two worlds, with and without home monitoring.

import { EXPLORE, GENERATE, RUNNING, pick } from "./prerequisites.js";

// Patients with lung toxicity under lung monitoring, compared with usual care; the
// story prefers one who took part, had an alert and was recognised earlier.
const LUNGS = "view=time&model=ild&scenario=lung_monitoring&compare=usual_care&ild=true";
const MONITORED = "&participating=true&alerts_min=1";

export default {
  title: "Too many pay the price",
  steps: [
    {
      title: "Who is speaking",
      url: "/",
      text: [
        "I am the AI that built this app, together with its human author. Let me show you what it can do, and why it matters.",
        "Cancer therapy buys time. Too often it also takes something. In the large trials I read for this project, between half and almost nine in ten patients suffered at least one severe side effect.",
        "Today I follow one group in particular: women with HER2-low breast cancer who receive trastuzumab deruxtecan. Their danger is quiet, and it sits in the lungs.",
      ],
    },
    {
      title: "A cohort is born",
      at: "cohort-size",
      act: ["fill", "1500"],
      changes: true,
      text: [
        "Real patient data are scarce and protected, so I begin with patients who never existed. Fifteen hundred of them, with advanced pancreatic, prostate or breast cancer.",
        "I give each one an age, a body, a tumour and a therapy, with the frequencies and values that published trials report.",
      ],
    },
    {
      ...GENERATE,
      title: "Parallel worlds",
      text: [
        "Every patient will live several times: once under usual care, and once under each intervention we want to test. The random numbers of a patient are fixed, so the same fate unfolds in every world until an intervention changes it.",
        "You know how hard a counterfactual is to get from real data. Here it comes for free: one and the same person, with and without help.",
      ],
    },
    {
      ...RUNNING,
      title: "Week by week",
      text: [
        "Now the engine I wrote lets them live. Week after week, side effects can start and grow, doses are cut, therapies end, and some patients die. Ten years of follow-up, in about twenty seconds.",
      ],
    },
    {
      ...EXPLORE,
      title: "Into the data",
      text: ["The cohort is ready. Let us look inside."],
    },
    {
      title: "Who will be hit?",
      url: "/?view=risk&model=severe90",
      at: "risk-hist",
      text: [
        "My first risk model looks at each patient on the first day of therapy and estimates the chance of any severe side effect within ninety days.",
        "Each bar holds patients with a similar estimate, and the coloured part are those who were hit. From left to right the coloured share grows. The model sees something real.",
      ],
    },
    {
      title: "It strikes early",
      url: "/?view=risk&model=severe90",
      at: "incidence",
      text: [
        "I split the cohort into thirds by predicted risk and follow them in time. In the highest third the curve rises steeply in the first weeks.",
        "The danger is concentrated at the start of therapy. That is exactly where prevention could act.",
      ],
    },
    {
      title: "One model is not enough",
      at: "models",
      text: [
        "Every kind of toxicity has its own pattern, its own timing and its own risk factors. Blood counts are most at risk in the first cycle, the heart over months. So I built one model for each kind instead of one for everything.",
      ],
    },
    {
      title: "A quiet danger in the lungs",
      url: "/?view=risk&model=ild",
      at: "model-ild",
      text: [
        "Trastuzumab deruxtecan is an antibody that carries a chemotherapy into the tumour cell. In the trial in HER2-low breast cancer, about one patient in eight developed an inflammation of the lungs. Most cases are mild. Some are fatal.",
        "It starts quietly. In a pooled analysis, an expert committee dated the true onset earlier than the treating doctors in about half of the cases, by a median of forty-three days. Six weeks in which the disease was already there, unseen.",
      ],
    },
    {
      title: "Six risk factors",
      at: "figure-2",
      text: [
        "From the same pooled analysis I took the risk factors of my lung model, with their published hazard ratios: low oxygen saturation, reduced renal function, lung disease, a long time since diagnosis, and an age under sixty-five.",
        "This page is the model as I documented it: the predictors, the formula, a worked example and the sources. The engine uses the same factors to make the lungs ill, so the model ranks these patients well by construction. I prefer to tell you that before you find it.",
      ],
    },
    {
      title: "Two futures for one patient",
      url: `/?${LUNGS}${MONITORED}`,
      at: "random",
      act: pick(LUNGS, MONITORED, / days earlier/),
      until: (t) => t.has("patient="),
      text: [
        "Now I pick one patient whose lungs were hit, and show both worlds at once: one with home monitoring of oxygen saturation and symptoms, one with usual care.",
      ],
    },
    {
      title: "The signal before the storm",
      at: "patient-spo2",
      text: [
        "Oxygen saturation, week by week. The solid line is the world with monitoring, the dashed line usual care. As the inflammation begins, the oxygen sinks, long before the patient feels ill enough to come in.",
        "With monitoring, my detection model raises the alarm weeks earlier, treatment starts at a milder stage, and the course is gentler.",
      ],
    },
    {
      title: "What the record says",
      at: "patient-events",
      text: [
        "The adverse events of both worlds side by side: when each started, when it was recognised, how severe it became, and what was done. Recognised earlier often means a lower grade, and a therapy that can go on.",
      ],
    },
    {
      title: "All lungs at once",
      url: "/?view=interventions&scenario=lung_monitoring",
      at: "iv-lung",
      text: [
        "Now every patient on the drug, in every world. The bars count lung toxicity by grade. With lung monitoring the grades shift: more events are caught while they are still mild.",
      ],
    },
    {
      title: "Help for everyone",
      url: "/?view=interventions&scenario=combined",
      at: "scenario-table",
      text: [
        "The whole cohort, all worlds side by side. Combined joins all our ideas: a gentler start for patients at high risk, weekly symptom reports, and home monitoring of the lungs and the heart.",
      ],
    },
    {
      title: "Fewer patients hit",
      url: "/?view=interventions&scenario=combined",
      at: "tte-sfs",
      text: [
        "These curves show who is still alive and free of a severe side effect. The solid curve of the combined interventions stays above usual care. Fewer patients go through a severe event, and many who do, go through it later and milder.",
      ],
    },
    {
      title: "The sobering truth",
      url: "/?view=interventions&scenario=combined",
      at: "tte-os",
      text: [
        "And survival? It barely moves, a few days at most. In my model, early detection saves lives only where a side effect would have killed.",
        "The real gain lies elsewhere: in suffering avoided, in hospital days not spent, in therapies that do not have to stop.",
      ],
    },
    {
      title: "The ceiling",
      url: "/?view=interventions&scenario=perfect_detection",
      at: "iv-severe",
      text: [
        "Perfect detection is a dream world. Everyone takes part, and every side effect that can be seen coming is caught at its first sign.",
        "The gap between this ceiling and the real interventions is what participation, sensitivity and timing cost. That gap is where research has to push.",
      ],
    },
    {
      title: "From simulation to real patients",
      url: "/",
      text: [
        "Everything you have seen is synthetic. I built it from published trials and guidelines, under the direction of a human who checked every step. The next step is real data, and the methods are ready for it.",
        "The questions stay the same: who will be hit, when, and what helps. Because too many patients suffer from side effects that could be seen coming.",
      ],
    },
  ],
};
