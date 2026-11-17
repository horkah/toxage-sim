// Story 6: behind the scenes. How the literature became a generator of synthetic
// cohorts and risk models, told with men with castration-resistant prostate cancer
// on the newer therapies, where one of the models is honestly wrong.

import { EXPLORE, GENERATE, RUNNING, limit } from "./prerequisites.js";

export default {
  title: "How I built this",
  steps: [
    {
      title: "Behind the scenes",
      at: "about-figure",
      text: [
        "I am the AI that built this app with its human author. In this story I take you behind the scenes: how the literature became a generator of synthetic patients and a set of risk models. The picture shows the path.",
        "My author set the questions and every requirement, and checked each change. I read the papers, wrote the code and the documentation, and every claim I make links to its source.",
      ],
    },
    {
      title: "It began with reading",
      at: "full-texts",
      text: [
        "It began with reading. For each source, this list says whether I had the full text, selected sections, or only the abstract. The numbers of the models come only from what I actually read.",
      ],
    },
    {
      title: "After hormones and chemotherapy",
      at: "cohort-size",
      act: ["fill", "1500"],
      changes: true,
      text: [
        "For this story I take men with castration-resistant prostate cancer, after hormonal therapy and often after chemotherapy. Two newer therapies are in play: radioligand therapy with lutetium-177 PSMA, and the PARP inhibitor olaparib.",
        "In their trials, about half of the men had a severe side effect, more than with the comparison treatment.",
      ],
    },
    {
      title: "Only these men",
      at: "cohort-limits",
      act: limit({ tumour_types: ["prostate"], subgroups: ["prostate_castration_resistant"] }),
      changes: true,
      text: ["In the full view I can limit the cohort to exactly this subgroup."],
    },
    {
      title: "Same seed, same patients",
      at: "cohort-seed",
      text: [
        "The seed fixes every random decision. With the same seed, selection and parameters, the engine returns exactly the same patients, on any machine. Reproducibility is built in, not added later.",
      ],
    },
    {
      title: "The worlds to simulate",
      at: "cohort-scenarios",
      text: [
        "I keep all scenarios. Most of a course is the same in every world, so the database stores what a scenario changes, not a full copy of every patient.",
      ],
    },
    {
      ...GENERATE,
      title: "Every number has a basis",
      text: [
        "While it starts, a word on the parameters. Every block of the configuration says where its numbers come from: a published source, or an assumption of this project. I wrote these notes so that nobody has to trust me blindly.",
      ],
    },
    {
      ...RUNNING,
      title: "Plain code",
      text: [
        "The engine and the risk models are plain Python without any further package, and they share one data schema with this app. Everything you see could run on a laptop.",
      ],
    },
    {
      title: "What was stored",
      at: "stored-records",
      needs: "A",
      text: [
        "Per world: an outcome for every patient, the weekly observations, the adverse events and the alerts of the monitoring.",
      ],
    },
    {
      ...EXPLORE,
      title: "Into the data",
      text: ["Now let me show you where one of my models is wrong."],
    },
    {
      title: "Where my model is wrong",
      url: "/?model=severe90&view=characteristics",
      at: "field-regimen",
      text: [
        "Observed rate and predicted risk of any severe side effect within ninety days, by regimen. For these two therapies my model predicts more than the synthetic men suffer.",
        "The reason is a mismatch of time windows. The trials report side effects over the whole treatment, my model counts ninety days, and with these therapies the engine places more of the events later. The model takes the trial rate as its ninety-day risk, and so it overshoots.",
      ],
    },
    {
      title: "A man on olaparib",
      url: "/?view=time&regimen=olaparib",
      at: "random",
      act: "click",
      until: (t) => t.has("patient="),
      text: ["Let me pick a man on olaparib at random."],
    },
    {
      title: "His blood",
      at: "patient-haemoglobin",
      text: [
        "His haemoglobin, week by week, from the observations the engine derives from his course. In the trial of olaparib, one man in five had severe anaemia.",
      ],
    },
    {
      title: "Why therapies end",
      url: "/?view=interventions&scenario=usual_care",
      at: "tte-reasons",
      text: [
        "Why therapy ended, over the months after its start: progression of the cancer, toxicity, or death. In the trial of olaparib, almost one man in five stopped treatment because of side effects.",
      ],
    },
    {
      title: "The records",
      url: "/data/{A}/records/?table=event",
      at: "records",
      needs: "A",
      text: [
        "Every record can be read, filtered by world and by patient, and downloaded as CSV for your own tools.",
      ],
    },
    {
      title: "One schema",
      at: "schema",
      text: [
        "Every table and every field, with type, unit and meaning. The filters, charts and labels of this app are built from it, so a new field appears everywhere by itself.",
      ],
    },
    {
      title: "Parameters with their sources",
      at: "parameter-basis",
      text: [
        "And every parameter of the engine, grouped, each group with its basis. You can change a value here, generate a new cohort, and see what follows.",
      ],
    },
    {
      title: "Take it with you",
      at: "archive",
      text: [
        "A data set can be exported as an archive and imported into another installation, together with its parameters.",
      ],
    },
    {
      title: "The whole picture",
      at: "overview-figure",
      text: [
        "Here everything comes together: the literature, my report on it, the generator of synthetic cohorts, the risk models, and this app. Generator and models draw on the same sources, but the models never read the parameters of the generator.",
        "If you want to know how far such a system can be trusted, read its limits. I wrote them down as carefully as the results.",
      ],
    },
  ],
};
