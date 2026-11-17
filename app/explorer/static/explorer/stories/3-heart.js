// Story 3: men with prostate cancer under androgen deprivation. Two trials disagree
// on the heart; a warning phase before an event gives monitoring its chance.

import { EXPLORE, GENERATE, RUNNING, limit, pick } from "./prerequisites.js";

// Men with a cardiovascular event under cardiovascular monitoring, compared with usual
// care; the story prefers one who took part, had an alert and was recognised earlier.
const HEART = "view=time&model=cv&scenario=cardiovascular_monitoring&compare=usual_care&cv_event=true";
const MONITORED = "&participating=true&alerts_min=1";

export default {
  title: "Two drugs, one heart",
  steps: [
    {
      title: "A question nobody has settled",
      url: "/",
      text: [
        "I am the AI behind this app. This story is about men with prostate cancer, and about their hearts.",
        "For men with metastatic prostate cancer, androgen deprivation is the base of every therapy. Two kinds of drugs do this: agonists and antagonists of the same hormone. Whether one is kinder to the heart than the other is an open question.",
      ],
    },
    {
      title: "Fifteen hundred patients",
      at: "cohort-size",
      act: ["fill", "1500"],
      changes: true,
      text: [
        "As always, I start with synthetic patients. Each man gets an age, a blood pressure, diabetes or not, a smoking history, a renal function and, for some, an earlier heart attack or stroke.",
      ],
    },
    {
      title: "Only prostate cancer",
      at: "cohort-limits",
      act: limit({ tumour_types: ["prostate"] }),
      changes: true,
      text: [
        "This time I keep only men with prostate cancer, hormone-sensitive and castration-resistant. The form lets me choose tumour types, subgroups and regimens, and the engine keeps the shares of what is left.",
      ],
    },
    {
      ...GENERATE,
      title: "A warning phase",
      text: [
        "Heart attacks and strokes do not always come out of nowhere. In my engine, half of them have a warning phase, with a median of ten days, in which blood pressure rises and chest pain appears. That is the window a monitoring could use.",
      ],
    },
    {
      ...RUNNING,
      title: "Two worlds for the heart",
      text: [
        "Every man lives under usual care, and under cardiovascular monitoring: blood pressure measured at home, a weekly question about chest symptoms, and a detection model that decides when to raise an alert.",
      ],
    },
    {
      ...EXPLORE,
      title: "Into the data",
      text: ["Ready. Let us look at the heart."],
    },
    {
      title: "No tool for this",
      url: "/?view=risk&model=cv",
      at: "model-cv",
      text: [
        "My fifth model estimates the risk of a heart attack, a stroke or cardiovascular death within the first year of androgen deprivation. The European cardio-oncology guideline says that no dedicated risk tool exists for these men. So I had to build a first one.",
      ],
    },
    {
      title: "Two trials disagree",
      url: "/?model=cv&view=characteristics",
      at: "field-adt",
      text: [
        "In HERO, events within about a year were less than half as frequent with an antagonist as with an agonist. In PRONOUNCE, which enrolled only men with heart disease, there was no clear difference, and the trial was stopped early.",
        "Here are both drugs in my synthetic cohort: observed rate and predicted risk. I took the rates from HERO, so the agonist looks worse here as well.",
      ],
    },
    {
      title: "The scar of an earlier event",
      url: "/?model=cv&view=characteristics",
      at: "field-prior-event",
      text: [
        "The strongest single factor is an earlier heart attack or stroke. In HERO, eight of forty-five such men had a new event under the agonist, three of eighty-four under the antagonist.",
        "And a trap I built in on purpose: as the guideline suggests, men with an earlier event get an antagonist more often in my cohort. Confounding by indication, just as you would meet it in real data.",
      ],
    },
    {
      title: "Pooling conflicting evidence",
      at: "figure-5",
      text: [
        "This page shows how I handled the conflict. HERO alone gives a hazard ratio of almost five for an earlier event under an agonist. Pooled with PRONOUNCE it is about one and a half. I chose the pooled value, and the page shows the sources.",
        "The other factors, such as age, diabetes, hypertension, smoking and renal function, are my assumptions. You can see it at a glance: filled dots are published, open dots assumed.",
      ],
    },
    {
      title: "Not the same patients",
      url: "/?view=risk&model=cv",
      at: "vs-severe90",
      text: [
        "Each point is a man with both risks: the heart on one axis, any severe side effect of his therapy on the other. A man at low risk of severe side effects can still be at high risk for his heart.",
        "One score for everything would miss him. That is why every toxicity gets its own model.",
      ],
    },
    {
      title: "One man, two worlds",
      url: `/?${HEART}${MONITORED}`,
      at: "random",
      act: pick(HEART, MONITORED, / days earlier/),
      until: (t) => t.has("patient="),
      text: [
        "Now I pick a man who had a cardiovascular event and took part in the monitoring, and show him in both worlds.",
      ],
    },
    {
      title: "Rising pressure",
      at: "patient-pressure",
      text: [
        "His systolic blood pressure, week by week. The solid line is the monitored world, the dashed line usual care. Before the event the pressure climbs.",
      ],
    },
    {
      title: "What he reported",
      at: "patient-symptoms",
      text: [
        "His own weekly reports in the monitored world. Chest pain appears in the warning phase, an alert goes out, and a doctor sees him.",
      ],
    },
    {
      title: "The record",
      at: "patient-events",
      text: [
        "Both records side by side. In the monitored world the event was recognised days earlier than in usual care. When treatment in the warning phase works, the event stays mild, and no heart attack or stroke follows.",
      ],
    },
    {
      title: "How much earlier",
      url: "/?view=interventions&scenario=cardiovascular_monitoring",
      at: "iv-lead",
      text: [
        "For all men: the events that monitoring caught, and how many days earlier than usual care.",
        "And the limit: an event without a warning phase comes without notice. No monitoring catches it, not even a perfect one.",
      ],
    },
    {
      title: "Milder when caught",
      url: "/?view=interventions&scenario=cardiovascular_monitoring",
      at: "iv-grade",
      text: [
        "The grade each caught event had when it was recognised, against the grade it would have reached in usual care.",
      ],
    },
    {
      title: "All events by grade",
      url: "/?view=interventions&scenario=cardiovascular_monitoring",
      at: "iv-heart",
      text: [
        "Cardiovascular events by grade in every world. Monitoring moves a part of them from the severe grades to the mild ones: caught in the warning phase and treated in time.",
      ],
    },
    {
      title: "Time to the event",
      url: "/?view=interventions&scenario=cardiovascular_monitoring",
      at: "tte-heart",
      text: [
        "And the cumulative incidence over time, monitored against usual care, among the men under androgen deprivation.",
      ],
    },
    {
      title: "In the literature",
      at: "report-prostate",
      text: [
        "Both trials, their patients and their numbers are in my report on the literature, side by side. Their authors call the question unresolved.",
        "What I can offer is a model that states every assumption, a simulation that shows what monitoring could change, and a place where the result of the next trial can be entered in a minute.",
      ],
    },
  ],
};
