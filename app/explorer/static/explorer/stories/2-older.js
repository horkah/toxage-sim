// Story 2: patients aged seventy and older. Frailty is a hidden variable of the
// engine; the model for severe toxicity sees only its traces.

import { EXPLORE, GENERATE, RUNNING } from "./prerequisites.js";
import { ECOG, isChanged } from "../tour-steps.js";

const OLDER = "age_years_min=70&model=severe90";

export default {
  title: "Age is only a number",
  steps: [
    {
      title: "Older than the trials",
      url: "/",
      text: [
        "I am the AI that built this app. In this story I talk with you about older patients, and about a variable that no data set contains.",
        "In a trial of patients aged seventy and older with incurable cancer, seven in ten suffered a severe side effect within three months of usual care. When their oncologists received a geriatric assessment with advice, the rate fell to about five in ten.",
        "So the question is not how old a patient is, but what the years have done to the body. Let me show you how I put that into the data.",
      ],
    },
    {
      title: "A hidden variable",
      at: "cohort-size",
      act: ["fill", "1500"],
      changes: true,
      text: [
        "Fifteen hundred patients again. Each one gets something I call frailty: a hidden number that you will never find in any table of the app.",
        "Frailty shapes what a clinician can see, such as performance status, the impaired domains of a geriatric assessment, haemoglobin and albumin. And it raises the hazard of every side effect.",
      ],
    },
    {
      ...GENERATE,
      title: "A confounder I control",
      text: [
        "For you as a data scientist this is the interesting part. Frailty is a confounder that I control completely. I know its true value for every patient, and the risk model does not.",
        "So we can watch how well a model does that sees only the shadows of frailty.",
      ],
    },
    {
      ...RUNNING,
      title: "Week by week",
      text: [
        "While the engine runs: a frail patient on the same regimen is hit more often, and every hit can mean a reduced dose, a pause or the end of therapy.",
      ],
    },
    {
      ...EXPLORE,
      title: "Into the data",
      text: ["Ready. Let us look at the patients aged seventy and older."],
    },
    {
      title: "Seventy and older",
      url: `/?view=risk&${OLDER}`,
      at: "filters",
      text: [
        "A filter on age keeps the patients aged seventy or older. The panel counts them, and every chart follows the selection.",
      ],
    },
    {
      title: "Age by itself",
      url: `/?view=risk&${OLDER}`,
      at: "risk-age",
      text: [
        "Each point is one of these patients, placed by age and by the risk my model predicts. The bands are the regimens with their published rates. Within a band, age hardly moves the risk.",
        "That is not my invention. A study of older patients on chemotherapy found that age did not predict severe toxicity among them.",
      ],
    },
    {
      title: "What frailty leaves behind",
      url: `/?${OLDER}&view=characteristics`,
      at: "field-ga",
      text: [
        "Here the observed rate of severe side effects for each number of impaired geriatric domains, next to what the model predicts. The more domains are impaired, the more patients are hit.",
        "This is the trace of the hidden frailty, and the model can read it.",
      ],
    },
    {
      title: "Does the model know?",
      url: `/?view=risk&${OLDER}`,
      at: "risk-hist",
      text: [
        "The distribution of predicted risk among the older patients. The model separates them, but only moderately. Most of what drives the risk, it never sees.",
        "The published scores for older patients do no better. Their authors found that differences between patients count two to three times more than the regimen, and yet their scores rank patients only moderately well.",
      ],
    },
    {
      title: "Honest numbers",
      url: `/?view=risk&${OLDER}`,
      at: "calibration",
      text: [
        "Calibration looks better than ranking. When the model says sixty percent, about sixty of a hundred such patients are hit.",
        "You know this pair well: a model can be honest about the average and still unable to tell patients apart.",
      ],
    },
    {
      title: "One of them",
      url: `/?view=risk&${OLDER}`,
      at: "random",
      act: "click",
      until: (t) => t.has("patient="),
      text: ["Let me take one of them at random."],
    },
    {
      title: "The reasons behind a risk",
      at: "patient-risk",
      text: [
        "The card shows the risk of this patient and the risk of a reference patient on the same regimen. The bars show each factor: what raises the risk, what lowers it, and by how much.",
        "Nothing here is a black box. The reference risk and the factors give the risk of the patient exactly.",
      ],
    },
    {
      title: "The model on one page",
      at: "figure-1",
      text: [
        "This is how I documented the model: the predictors with their odds ratios, a filled dot where a study published the effect, an open dot where I had to assume it. Then the formula, a worked example and the sources.",
        "Several of these effects are assumptions, and the page says so.",
      ],
    },
    {
      title: "Question an assumption",
      at: "ecog-odds-ratio",
      act: ["fill", "4"],
      until: isChanged(ECOG),
      changes: true,
      text: [
        "Let me challenge one of them. The odds ratio for a poor performance status is an assumption of two. What if it were four?",
      ],
    },
    {
      title: "The picture shifts",
      url: "/?view=risk&model=severe90&ecog_min=2",
      at: "model-severe90",
      full: true,
      changes: true,
      text: [
        "Among the patients with a poor performance status, the predicted risk jumps at once, while the observed rate stays where it was. The card of the model shows the gap.",
        "Every assumption leaves its mark, and real data will tell which ones hold.",
      ],
    },
    {
      title: "A gentler start",
      url: `/?${OLDER}&view=interventions&scenario=risk_adapted_start`,
      at: "iv-severe",
      text: [
        "Now the intervention that geriatric oncology recommends. In the risk-adapted start, patients flagged as high risk begin with a reduced dose, get support against infection and are checked more closely.",
        "Among the older patients, fewer are hit within ninety days.",
      ],
    },
    {
      title: "Fewer therapies broken off",
      url: `/?${OLDER}&view=interventions&scenario=risk_adapted_start`,
      at: "tte-toxstop",
      text: [
        "And fewer have to stop therapy because of toxicity. In my model a lower dose costs some effect against the tumour, so the gain is not free.",
        "That trade-off is exactly what a real trial would have to weigh.",
      ],
    },
    {
      title: "Where this comes from",
      at: "report-older",
      text: [
        "Everything I told you about older patients is in my report on the literature, with its sources: the trials of geriatric assessment, the guideline that asks for it in everyone aged sixty-five or older, and the scores that predict toxicity.",
        "In the surveys that guideline cites, only about one oncologist in five used such an assessment routinely. That is the gap this story points at.",
      ],
    },
  ],
};
