// Story 5: women with pretreated triple-negative breast cancer on sacituzumab
// govitecan. Severe neutropenia, a published model used as it is, and a start of
// therapy guided by the models.

import { EXPLORE, GENERATE, RUNNING, limit } from "./prerequisites.js";

const NEUTROPENIA = "model=neutropenia";

export default {
  title: "The first cycle",
  steps: [
    {
      title: "An emergency in the blood",
      url: "/",
      text: [
        "I am the AI that built this app. This story is about blood counts, and about women with triple-negative breast cancer who have already been through chemotherapy.",
        "Their preferred next drug, sacituzumab govitecan, brought severe neutropenia to half of the patients in its trial. Neutropenia with fever is an emergency: the guideline asks for the first antibiotics within one hour.",
      ],
    },
    {
      title: "A model with a pedigree",
      at: "cohort-size",
      act: ["fill", "1500"],
      changes: true,
      text: [
        "For once I did not have to invent a model. A study of almost four thousand patients in community practices predicted severe or febrile neutropenia in the first cycle, and it held up in validation. I took its odds ratios as they are.",
        "Fifteen hundred patients again.",
      ],
    },
    {
      title: "Only these women",
      at: "cohort-limits",
      act: limit({ tumour_types: ["breast"], subgroups: ["breast_triple_negative_pretreated"] }),
      changes: true,
      text: [
        "This time all of them are women with triple-negative breast cancer after earlier chemotherapy, and all of them start sacituzumab govitecan.",
      ],
    },
    {
      ...GENERATE,
      title: "Good by construction",
      text: [
        "A confession before you see the charts: my engine makes neutropenia with the same published odds ratios, used as hazards that act week by week. When data and model share their parameters, a good ranking is no surprise.",
        "The interesting questions lie elsewhere: in calibration, in decisions, and in what a model can and cannot recover.",
      ],
    },
    {
      ...RUNNING,
      title: "The first cycle",
      text: [
        "Meanwhile one detail from that study: two thirds of these events happened in the first cycle, when patients get the full dose and usually no protection. Prevention has to come before the first infusion.",
      ],
    },
    {
      ...EXPLORE,
      title: "Into the data",
      text: ["Ready. Let us look at the blood."],
    },
    {
      title: "My third model",
      url: `/?view=risk&${NEUTROPENIA}`,
      at: "model-neutropenia",
      text: [
        "My third model predicts severe or febrile neutropenia within ninety days. Its factors come from the published model: earlier chemotherapy, liver values, renal function, white cells, a corticosteroid in the regimen, the planned dose, and growth factor support from the first cycle.",
      ],
    },
    {
      title: "Clear separation",
      url: `/?view=risk&${NEUTROPENIA}`,
      at: "risk-hist",
      text: [
        "The predicted risks spread widely, and the coloured share of patients who were hit grows steadily from left to right.",
      ],
    },
    {
      title: "And calibrated",
      url: `/?view=risk&${NEUTROPENIA}`,
      at: "calibration",
      text: [
        "Predicted against observed, in ten groups by risk. The points stay close to the diagonal: when the model says forty percent, about forty of a hundred such women are hit.",
      ],
    },
    {
      title: "The same active drug",
      url: `/?${NEUTROPENIA}&view=characteristics`,
      at: "field-ugt1a1",
      text: [
        "Sacituzumab govitecan carries SN-38, the active form of irinotecan. Women with two copies of the gene variant UGT1A1*28 break it down more slowly, and the trial authors note more blood toxicity in them. Here their observed and predicted rates, next to the others.",
      ],
    },
    {
      title: "Above twenty percent",
      url: `/?view=risk&${NEUTROPENIA}&risk_neutropenia_min=20`,
      at: "cohort",
      text: [
        "Guidelines recommend growth factors from the first cycle when the risk of febrile neutropenia reaches twenty percent. I filter to the women my model places above that line. It is a broader event than fever alone, and almost all of them are above it.",
      ],
    },
    {
      title: "Let the models decide",
      url: "/?view=interventions&scenario=model_guided_start",
      at: "scenario-table",
      text: [
        "In usual care, none of these women gets growth factors from the first cycle. In the world called model-guided start, my models decide: the model for severe toxicity flags the women at high risk, and the neutropenia model decides who of them gets growth factors.",
      ],
    },
    {
      title: "Fewer severe events",
      url: "/?view=interventions&scenario=model_guided_start",
      at: "tte-severe",
      text: [
        "The cumulative incidence of the first severe side effect. Under the model-guided start the curve stays below usual care: fewer women go through a severe side effect in the first months of therapy.",
      ],
    },
    {
      title: "One woman's neutrophils",
      url: `/?view=time&${NEUTROPENIA}&scenario=usual_care&compare=model_guided_start&severe_neutropenia_90d=true`,
      at: "random",
      act: "click",
      until: (t) => t.has("patient="),
      text: ["Let me pick a woman whose neutrophils fell severely under usual care."],
    },
    {
      title: "Counts that fall",
      at: "patient-neutrophils",
      text: [
        "Her neutrophils week by week. The solid line is usual care, the dashed line the model-guided start. The counts fall with each dose.",
        "If the models flagged her and she took part, the dashed line shows her protected world. If not, both lines lie on each other.",
      ],
    },
    {
      title: "The records behind it",
      url: "/data/{A}/records/?table=event",
      at: "records",
      needs: "A",
      text: [
        "Behind every chart are records in one simple schema. Here the adverse events of this data set: the grade, the day of onset, the day of recognition, and what would have happened in usual care.",
        "You can download them as CSV files and fit your own models.",
      ],
    },
    {
      title: "Fitting it back",
      at: "figure-3",
      text: [
        "This page shows the published model as I implemented it. I also fitted it back on fifty thousand synthetic patients. Most odds ratios came out close to the published ones, but the protection by growth factors came out weaker: 0.21 against a published 0.12.",
        "A useful check for any pipeline: if you cannot recover what you put in, be careful with what you find in real data.",
      ],
    },
    {
      title: "The source",
      at: "lyman-2011",
      text: [
        "And the source itself, in my list of references. The list says for every reference whether I read the full text or only the abstract, and the numbers I used come only from what I read.",
        "One cycle, one decision, one number from a model. This is where risk prediction is closest to daily practice already.",
      ],
    },
  ],
};
