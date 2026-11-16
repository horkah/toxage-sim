# engine

Generator for synthetic patient data. It is a microsimulation: every patient is simulated individually, week by week, from the start of a systemic therapy line until death or for ten years. The same patients are simulated under several intervention scenarios, so that the effect of an intervention can be read off patient by patient. The output follows the central [schema](../schema/).

The engine serves five risk model candidates of the [toxicity report](../background/toxicity-report.md) and the [intervention model](../background/intervention-model.md):

- Candidate 1: any adverse event of grade 3 to 5 within 90 days of therapy start.
- Candidate 2: interstitial lung disease or pneumonitis, including the delay until it is recognised.
- Candidate 3: neutropenia of grade 3 or higher or febrile neutropenia within 90 days.
- Candidate 4: diarrhoea of grade 3 or higher within 90 days.
- Candidate 5: major cardiovascular events under androgen deprivation for prostate cancer, including the warning phase before an event.
- Interventions: risk prediction at therapy start with an adapted start, and monitoring during therapy with early recognition and early treatment.

## Run

```bash
python3 engine/generate.py --n 3000 --seed 1 --out engine/output
```

This writes `scenario.csv`, `baseline.csv`, `observation.csv`, `event.csv`, `alert.csv`, `outcome.csv` and `metadata.json` to the output folder and prints key numbers per regimen and per scenario. `--scenarios` limits the run to some scenarios, for example `--scenarios usual_care`. `--tumours`, `--subgroups` and `--regimens` limit the cohort, for example `--tumours breast --regimens trastuzumab_deruxtecan`. The same seed gives the same data. The output folder is not under version control. 3000 patients under all eight scenarios take about 45 seconds.

```bash
python3 engine/calibrate.py
python3 -m unittest discover engine/tests
```

`calibrate.py` matches the event rates of usual care to the literature and writes `config/calibration.json`. It takes about two minutes and has to be run again after every change of the model or its parameters. The engine needs Python 3 and no further packages. It imports the risk models of this repository for the model-guided start and for lung monitoring.

## Files

| File | Content |
|---|---|
| `generate.py` | Command line entry: simulates all patients under all scenarios, checks the data against the schema, writes the files |
| `population.py` | Baseline characteristics and choice of therapy |
| `hazards.py` | Weekly hazards of adverse events |
| `draws.py` | Fixed random numbers per patient, purpose and week |
| `interventions.py` | What a scenario means for one patient: participation, adapted start by stand-in or risk models, detection |
| `course.py` | Course of one patient in weekly steps under one scenario, and the outcome summary |
| `measurements.py` | Weekly observations derived from the course; the home measurements that the detection model reads |
| `calibrate.py` | Calibration against the literature |
| `uncertainty.py` | Repeated simulation with parameters drawn from their published uncertainty |
| `config/regimens.json` | Regimens with reference values and sources |
| `config/parameters.json` | Parameters of population, hazards, actions, survival and measurements |
| `config/interventions.json` | Parameters of the intervention model and the list of scenarios |
| `config/calibration.json` | Calibration factors, written by `calibrate.py` |
| `config/uncertainty.json` | The parameters with a published interval or a known number of patients, for `uncertainty.py` |
| `tests/test_engine.py` | Tests |

Every block of the configuration files states whether its values come from the literature or are assumptions. `generate.default_config()` returns the whole configuration as one dictionary; a caller can change values in a copy and pass it to `generate.generate()`.

## Structure of the simulation

```
latent frailty ──► baseline characteristics ──► choice of regimen and starting dose
       │                    │                              │
       │                    │         scenario: adapted start for flagged patients
       └────────────────────┴───────────┬──────────────────┘
                                        ▼
        every week:   hazards of adverse events  ◄── dose level, time on therapy
                                        │
                      an event starts mild and worsens
                                        │
           recognised by usual care, or earlier by monitoring (scenario)
                                        │
        grade, change of therapy, hospital stay, death; costs and quality of life
                                        │
                                        ▼
        observations of the week: blood values, oxygen saturation, blood pressure, symptoms
```

A patient is followed until death or for 520 weeks. Observations are written while the patient is on therapy and for four weeks after. The cohort has 25% patients with pancreatic, 40% with prostate and 35% with breast cancer, in six subgroups with eleven regimens. A cohort can be limited to some tumour types, subgroups and regimens; the shares of what is left keep their proportions.

## Patient groups

| Tumour (share) | Subgroup | Share within tumour | Regimens |
|---|---|---|---|
| pancreas (25%) | `pancreas_metastatic` | 100% | `nalirifox`, `gemcitabine_nab_paclitaxel` |
| prostate (40%) | `prostate_hormone_sensitive` | 50% | `adt_docetaxel`, `adt_docetaxel_abiraterone`, `adt_docetaxel_darolutamide` |
| prostate | `prostate_castration_resistant` | 50% | `lu_psma_617`, `olaparib` |
| breast (35%) | `breast_her2_low` | 60% | `trastuzumab_deruxtecan`, `chemotherapy_single_agent` |
| breast | `breast_triple_negative` | 25% | `pembrolizumab_chemotherapy` |
| breast | `breast_triple_negative_pretreated` | 15% | `sacituzumab_govitecan` |

The subgroups differ in age, earlier therapy lines, time since diagnosis, blood values, toxicity profile, treatment duration and survival.

## Model variables

### Latent variable

| Variable | Meaning |
|---|---|
| Frailty | One number per patient, standard normal plus an age term and a shift for pancreatic cancer. It is not written to the data. |

### Baseline variables

| Variable | Depends on |
|---|---|
| Subgroup | Tumour type |
| Age | Subgroup |
| Sex | Tumour type |
| ECOG | Frailty |
| Impaired geriatric domains (from age 65) | Frailty |
| Albumin, body mass index | Frailty, pancreatic cancer |
| Diabetes | Age, pancreatic cancer |
| Cardiovascular disease | Age, sex |
| Earlier cardiovascular event (myocardial infarction or stroke) | Cardiovascular disease |
| Arterial hypertension | Age, diabetes, cardiovascular disease |
| Systolic blood pressure | Arterial hypertension, age |
| Smoking | Tumour type |
| Type of androgen deprivation (prostate cancer only) | Earlier cardiovascular event |
| Lung comorbidity | – |
| Renal function (eGFR and category) | Age, diabetes |
| Bilirubin | Pancreatic cancer (biliary obstruction in 20%) |
| AST, alkaline phosphatase | Biliary obstruction; alkaline phosphatase also castration-resistant prostate cancer |
| Oxygen saturation | Lung comorbidity, frailty |
| Earlier therapy lines, years since diagnosis | Subgroup |
| Neutrophils, haemoglobin, platelets | Earlier therapy lines, sex, frailty, renal function |
| White blood cells | Neutrophils |
| Regimen | Subgroup; in pancreatic cancer frailty, age and bilirubin; in HER2-low breast cancer lung problems |
| Starting dose level | Frailty, age |
| G-CSF prophylaxis | Regimen (docetaxel) |
| Khorana score | Tumour type, platelets, haemoglobin, white cells, body mass index |
| Thromboprophylaxis | Khorana score of 2 or more (10% of these patients) |
| Immunosuppressive medication | Regimen (always with abiraterone, which is given with prednisone) |
| UGT1A1*28 homozygous | – |

### Variables over time

| Variable | Changes through |
|---|---|
| Therapy status (on treatment, interrupted, stopped) | Adverse events, progression, planned end, death |
| Dose level (1.0, 0.8, 0.6) | Dose reductions after adverse events |
| Recent drug exposure | Dose and status of the last weeks |
| Adverse events with type, grade, onset day, recognition day and action | Weekly hazards |
| Neutrophils, haemoglobin, platelets | Exposure, patient sensitivity, events |
| Oxygen saturation, cough, shortness of breath | Lung toxicity from its true onset |
| Systolic blood pressure, chest pain | Warning phase of a cardiovascular event, hypertension events, regimens that raise blood pressure |
| Fatigue, diarrhoea | Exposure, frailty, events |
| Death | Tumour, frailty, ECOG, fatal adverse events |
| Alerts of the monitoring components | Developing events, participation, false alerts |
| Hospital days, unplanned visits, costs, quality-adjusted life years | Recognised events and their grade, alerts, participation |

### Event types

`neutropenia`, `febrile_neutropenia`, `anaemia`, `thrombocytopenia`, `diarrhoea`, `peripheral_neuropathy`, `hypertension`, `immune_related`, `interstitial_lung_disease`, `cardiovascular_event`, `venous_thromboembolism`, `major_bleeding`, `other`.

The engine generates events that reach grade 3 to 5 in usual care, and interstitial lung disease of any grade. With monitoring such an event can be recognised at grade 1 or 2.

A `cardiovascular_event` is a myocardial infarction, a stroke or cardiovascular death in a man under androgen deprivation. In usual care it has grade 3, 4 or 5. If monitoring catches its warning phase and treatment works, it is recorded at grade 1 or 2 and no major event follows.

## Covariate mechanisms

These mechanisms make the data behave like real data rather than like independent random columns.

1. **Latent frailty.** Frailty drives ECOG, geriatric impairments, albumin, body mass index, haemoglobin and oxygen saturation, and it raises the hazards of adverse events and death. The observed variables are therefore correlated with each other and predict toxicity, but none of them explains it fully.
2. **Age effects.** Age lowers renal function, raises the rates of diabetes and cardiovascular disease, and adds to frailty and to the toxicity hazards.
3. **Tumour-specific patterns.** Pancreatic cancer comes with more frailty, lower albumin and weight, more diabetes and, in some patients, raised bilirubin. Castration-resistant prostate cancer and HER2-low breast cancer come with earlier therapy lines and lower blood counts.
4. **Treatment by indication.** Fitter and younger pancreatic patients more often get NALIRIFOX. Patients with lung problems less often get trastuzumab deruxtecan. Men with an earlier cardiovascular event more often get a GnRH antagonist instead of an agonist. Frail and older patients more often start with a reduced dose. Regimen and dose are therefore not independent of the patient's risk.
5. **Type-specific risk factors.** Neutropenia and febrile neutropenia follow the published model of [Lyman et al. (2011)](../background/references.md#lyman-2011): earlier chemotherapy, an age of 65 or older, raised AST, alkaline phosphatase or bilirubin, lower renal function, fewer white cells and immunosuppressive medication raise the hazard, G-CSF lowers it. In patients with two copies of UGT1A1*28, sacituzumab govitecan and the irinotecan in NALIRIFOX cause more neutropenia and diarrhoea: both act through SN-38, which these patients break down slowly. Low haemoglobin and renal impairment raise the hazard of anaemia. Diabetes raises the hazard of neuropathy, cardiovascular disease that of hypertension. The six published risk factors raise the hazard of lung toxicity under trastuzumab deruxtecan. For cardiovascular events an earlier event raises the hazard under a GnRH agonist and under an antagonist, as HERO ([Shore et al., 2020](../background/references.md#shore-2020)) and PRONOUNCE ([Lopes et al., 2021](../background/references.md#lopes-2021)) show together; age, diabetes, hypertension, smoking, renal function, cardiovascular disease without an event and frailty add to it.
6. **Time patterns.** Neutropenia, diarrhoea and unspecified events occur mainly in the first weeks: older patients had their first severe toxicity after a median of 22 days ([Extermann et al., 2012](../background/references.md#extermann-2012)), and two thirds of first neutropenic events fall into the first cycle ([Lyman et al., 2011](../background/references.md#lyman-2011)). Anaemia, low platelets, hypertension and immune-related events peak around week 8. Neuropathy grows with time on therapy. Lung toxicity follows the published onset distribution. Cardiovascular events have a constant hazard while the patient is on therapy. Toxicity from docetaxel ends after 18 weeks.
   Venous thromboembolism occurs with the pancreatic regimens (10.2% within three months without prophylaxis) and with olaparib (4%). Thromboprophylaxis lowers its hazard to 0.41 and brings 1.7 percentage points of major bleeding within 26 weeks ([Key et al., 2020](../background/references.md#key-2020)). A major bleeding comes without notice.
7. **Feedback.** A severe event can lead to an interruption, a dose reduction or the end of therapy. A lower dose lowers the hazard of later events. A patient who stops therapy has no further therapy-related events.
8. **Competing events.** Progression, the planned end of therapy and death end the time at risk.
9. **Delayed recognition.** Lung toxicity has a true onset day and a recognition day. In 53% of cases recognition is delayed, with a median of 43 days. Therapy continues until recognition.
10. **Warning phase.** Half of the cardiovascular events are preceded by a warning phase with a median of 10 days, such as unstable angina, a transient ischaemic attack or rising blood pressure. The other half come without notice.
11. **Signals in the measurements.** Blood values fall with exposure, more so in patients with a high hazard, and show the event in the event week. Oxygen saturation falls and cough and shortness of breath rise from the true onset of lung toxicity, so they can show it before it is recognised. Blood pressure and chest pain rise during the warning phase of a cardiovascular event; blood pressure also rises with regimens that cause hypertension and peaks in the week of a hypertension event. Diarrhoea rises in the week before a diarrhoea event. Measurements have noise, and some weeks are missing.

## Hazard model

For each patient, week and event type:

```
hazard = target hazard of the regimen
         × time weight of the week
         × patient multiplier
         × dose level ^ 2
         × calibration factor
```

- **Target hazard.** From the share of trial patients with a severe event of that type, see `config/regimens.json`. The type `other` is set so that all types together give the overall rate of severe toxicity of the trial. For cardiovascular events the target comes from the leuprolide arm of HERO, 6.2% in 48 weeks, for all five prostate regimens. HERO counted death from any cause as an event. In PRONOUNCE 16 of 26 such events were cardiovascular death, myocardial infarction or stroke ([Lopes et al., 2021](../background/references.md#lopes-2021)); this share brings the target to 3.8%.
- **Patient multiplier.** The product of the general factors (frailty, age, bilirubin above 1.5 times the upper limit) and the type-specific factors. Neutropenia and febrile neutropenia take frailty from the general factors and everything else from the published model. For lung toxicity only the published hazard ratios apply, and only under trastuzumab deruxtecan. Cardiovascular events have risk factors of their own as well; the dose of the cancer therapy does not change their hazard.
- **Calibration factor.** Set by `calibrate.py` so that generated patients with ECOG 0 or 1, who resemble trial patients, reach the published rates within the 52 weeks. Cardiovascular events are matched in the men on a GnRH agonist.

Each event type has its own fixed random number per week. A lower hazard therefore removes events and adds none. No new event of a type starts while an earlier one of the same type is not yet recognised.

## Natural course of an event

An event starts at grade 1 and worsens until it is recognised.

- **Usual care** recognises an event at a fixed later day and at the grade it has reached by then. For lung toxicity this is the published recognition delay. For a cardiovascular event it is the end of the warning phase, or the day of onset if there is none. For the other types the event passes through the lower grades first; the days per grade are in `config/interventions.json`.
- **Monitoring** can recognise the event on a report day before that. The grade is then the stage the event has reached. With a given probability early treatment stops the worsening; otherwise the event still reaches its usual-care grade.
- Every event record holds both: the day and grade of recognition, and the day and grade it would have had in usual care.

In the scenario "usual care" this gives the same events and grades as the literature, which stay the calibration targets.

## Scenarios

| Scenario | Content |
|---|---|
| `usual_care` | No intervention |
| `risk_adapted_start` | A risk prediction at therapy start flags 30% of the patients as high risk. Flagged patients who take part get a reduced starting dose (probability 0.5), G-CSF with regimens that cause severe neutropenia in 20% or more (0.7), thromboprophylaxis with a Khorana score of 2 or more (0.7), supportive measures (all hazards except lung toxicity and cardiovascular events × 0.75) and weekly symptom reports. |
| `model_guided_start` | As the risk-adapted start, but the [risk models](../risk-model/) decide. The model for severe toxicity (candidate 1) gives the score; the 30% with the highest risk are flagged. A flagged patient gets G-CSF if the model for severe neutropenia (candidate 3) gives a risk of 20% or more without G-CSF. |
| `symptom_monitoring` | All patients are offered weekly symptom reports during therapy. An alert leads to contact and, if the patient attends and the team acts, to recognition on the next day. |
| `lung_monitoring` | Patients on trastuzumab deruxtecan are offered home monitoring of oxygen saturation and symptoms with a detection model for lung toxicity. |
| `cardiovascular_monitoring` | Men with prostate cancer under androgen deprivation are offered home monitoring of blood pressure and chest symptoms with a detection model. It can catch cardiovascular events that have a warning phase, and hypertension. |
| `combined` | Risk-adapted start, symptom monitoring, lung monitoring and cardiovascular monitoring |
| `perfect_detection` | As combined, with full participation, a predictor without noise, detection of every event at its first stage, early treatment that always works, and no false alerts. Cardiovascular events without a warning phase and major bleedings cannot be seen in advance and remain. Upper limit. |

The components of a scenario and all their parameters are in `config/interventions.json`. A new scenario is a new entry there.

**Fixed random numbers.** Every random decision of a patient is tied to a purpose and a week (`draws.py`). A scenario changes probabilities, not the random numbers. A patient whom an intervention does not reach has exactly the same course as in usual care, and a patient who is reached differs only from the point where the intervention acts. The tests check this.

**Detection during therapy.** Lung monitoring uses the detection model of the [risk models](../risk-model/): each week it reads the oxygen saturation, cough and breathlessness of the patient, the same values that the observation table holds, and alerts by a published rule. Its true and false alerts follow from the measurements. Symptom monitoring and cardiovascular monitoring use stand-ins: a sensitivity per stage of an event, times the share of events of a type that show in symptoms, plus a rate of false alerts.

**Prediction at therapy start.** The risk-adapted start uses a stand-in: the true patient-related risk plus noise; the noise sets its accuracy. The model-guided start uses the risk models with their literature configuration, as a clinic could. Comparing the two shows how far the models are from a predictor that knows part of the truth.

**Participation.** Whether a patient takes part depends on frailty and age. Reports are missing in some weeks, more often in frail patients. Each week a patient can drop out of the monitoring for good. After an alert the patient may not attend, and the team may not act. Every earlier false alert of a patient makes it a little less likely that the team acts on the next alert (alert fatigue). In all scenarios, including usual care, a patient on therapy can be lost to follow-up: therapy ends, and only events of grade 4 or 5 are still recognised.

**Consequences.** The grade at recognition decides the change of therapy, the probability and length of a hospital stay, intensive care, the duration of the event and the loss of quality of life.

**Quality of life.** The weights are the utilities of [Lloyd et al. (2006)](../background/references.md#lloyd-2006): 0.715 while the patient is on the therapy line, 0.272 less after its end, when the patient counts as progressive, and 0.150 less during febrile neutropenia, 0.103 during severe diarrhoea and 0.115 during other severe events. A therapy line that lasts longer because fewer patients stop for toxicity therefore gains quality-adjusted life years.

**Costs.** Costs are counted for unplanned visits, hospital days, diagnostics after alerts, risk assessment, set-up, monitoring weeks and the handling of alerts. The costs of the cancer drugs are not included.

## Reference values and how well they are met

Usual care, from a run with 9000 patients (seed 1), all ECOG levels included:

| Regimen | Trial: any severe toxicity | Generated: any severe toxicity | Generated: within 90 days | Generated: stopped for toxicity |
|---|---|---|---|---|
| `nalirifox` | 87% | 87% | 86% | 23% |
| `gemcitabine_nab_paclitaxel` | 86% | 87% | 86% | 22% |
| `adt_docetaxel` | 63.5% | 68% | 63% | 12% |
| `adt_docetaxel_abiraterone` | 63% | 70% | 60% | 11% |
| `adt_docetaxel_darolutamide` | 66.1% | 72% | 66% | 12% |
| `lu_psma_617` | 52.7% | 53% | 46% | 10% |
| `olaparib` | 51% | 57% | 48% | 12% |
| `trastuzumab_deruxtecan` | 52.6% | 55% | 51% | 15% |
| `chemotherapy_single_agent` | 67.4% | 71% | 70% | 8% |
| `pembrolizumab_chemotherapy` | 68.1% | 70% | 68% | 13% |
| `sacituzumab_govitecan` | 64% | 66% | 64% | 6% |

The calibration matches each event type to the literature within 0.3 percentage points in generated patients with ECOG 0 or 1 during the first 52 weeks. The table differs from the trial rates because it includes patients with ECOG 2 and events after week 52.

Further checks against the literature:

| Quantity | Literature | Generated |
|---|---|---|
| Severe toxicity within 90 days in patients aged 70 or older with at least one impaired geriatric domain, usual care | 71% ([Mohile et al., 2021](../background/references.md#mohile-2021), usual care) | about 68% |
| The same in flagged patients who take part in the risk-adapted start, against usual care | relative risk 0.74 ([Mohile et al., 2021](../background/references.md#mohile-2021)); 50.5% against 60.6% in GAIN ([Dale et al., 2023](../background/references.md#dale-2023)) | 51% against 70%, relative risk 0.73 |
| Day of the first severe toxicity, median and quartiles | 22, 9 to 51, in patients aged 70 or older on chemotherapy ([Extermann et al., 2012](../background/references.md#extermann-2012)) | 15, 11 to 24, in pancreatic cancer |
| Severe or febrile neutropenia with and without G-CSF | 6.4% and 22.8% in the first cycle ([Lyman et al., 2011](../background/references.md#lyman-2011)) | 20% and 54% within 90 days with docetaxel alone |
| Severe neutropenia with sacituzumab govitecan, with and without two copies of UGT1A1*28 | higher risk with two copies, no number ([Bardia et al., 2021](../background/references.md#bardia-2021)) | 66% and 52% within 90 days |
| AST above 35 U/l, alkaline phosphatase above 120 U/l, white cells below 5 | 13.5%, 19.5%, 12.8% ([Lyman et al., 2011](../background/references.md#lyman-2011)) | 15%, 20%, 18% |
| Venous thromboembolism in pancreatic cancer without and with thromboprophylaxis | 10.2% within three months without; hazard ratio 0.41 with ([Key et al., 2020](../background/references.md#key-2020)) | 11.9% and 4.8% over the whole follow-up |
| Khorana score of 3 or more among patients with pancreatic cancer | – | 20% |
| Dose reduction with NALIRIFOX | 60% ([Wainberg et al., 2023](../background/references.md#wainberg-2023)) | about 47% |
| Therapy stopped because of adverse events with NALIRIFOX | 32% ([Wainberg et al., 2023](../background/references.md#wainberg-2023)) | about 23% |
| Therapy stopped because of adverse events with sacituzumab govitecan | 5% ([Bardia et al., 2021](../background/references.md#bardia-2021)) | about 6% |
| Lung toxicity with trastuzumab deruxtecan within 52 weeks | 10.5% (12.1% overall, 87% of events within 12 months) | about 14% in this run; between 8% and 14% in runs with other seeds |
| Share of lung toxicity recognised late | 53% ([Powell et al., 2022](../background/references.md#powell-2022)) | about 51% |
| Median day of onset of lung toxicity | 129 ([Modi et al., 2022](../background/references.md#modi-2022)) | about 116 |
| Cardiovascular events within 48 weeks under a GnRH agonist | 3.8%: 6.2% ([Shore et al., 2020](../background/references.md#shore-2020)), of which 61.5% cardiovascular ([Lopes et al., 2021](../background/references.md#lopes-2021)) | 4.4% |
| Hazard with an earlier event against without, under a GnRH agonist | 1.46 (HERO and PRONOUNCE together) | 8.1% against 4.1%, a ratio of about 2 |
| Cardiovascular events within 48 weeks under a GnRH antagonist | 1.8%: 2.9% ([Shore et al., 2020](../background/references.md#shore-2020)), of which 61.5% cardiovascular | 3.0% |
| Share of men with an earlier cardiovascular event | 13.9% ([Shore et al., 2020](../background/references.md#shore-2020)) | 12.7% |

Scenarios, from the same run, per patient of the whole cohort:

| Scenario | Taking part | Severe toxicity, 90 days | Severe events | Cardiovascular events | Deaths from toxicity | Hospital days | Alerts | QALY | Cost of care (€) | Cost of intervention (€) |
|---|---|---|---|---|---|---|---|---|---|---|
| `usual_care` | 0% | 65.1% | 1.14 | 286 | 200 | 3.62 | 0 | 1.321 | 3682 | 0 |
| `risk_adapted_start` | 21.5% | 61.1% | 1.03 | 283 | 177 | 3.24 | 0.69 | 1.325 | 3290 | 424 |
| `model_guided_start` | 21.9% | 60.9% | 0.99 | 285 | 175 | 3.15 | 0.45 | 1.325 | 3193 | 300 |
| `symptom_monitoring` | 78.6% | 63.0% | 1.08 | 282 | 151 | 3.22 | 2.95 | 1.330 | 3261 | 1452 |
| `lung_monitoring` | 9.7% | 65.1% | 1.14 | 286 | 196 | 3.62 | 0.02 | 1.322 | 3684 | 60 |
| `cardiovascular_monitoring` | 30.3% | 64.8% | 1.13 | 272 | 197 | 3.60 | 0.73 | 1.322 | 3816 | 229 |
| `combined` | 78.6% | 59.1% | 0.98 | 274 | 141 | 2.96 | 3.72 | 1.334 | 3162 | 1793 |
| `perfect_detection` | 100% | 0.4% | 0.02 | 150 | 25 | 0.14 | 1.18 | 1.375 | 172 | 2606 |

Cardiovascular events and deaths from toxicity are counts among the 9000 patients, over the whole follow-up.

- **Stand-in against risk models.** The risk-adapted start and the model-guided start flag the same share of patients and reach about the same result, by different patients: 41% of the flags agree. The stand-in knows the frailty of a patient and flags in all three tumours. The model for severe toxicity ranks mostly by the regimen and flags mainly patients with pancreatic cancer (2217 of 2700 flags). Its flagged patients have a higher risk (85% severe toxicity within 90 days in usual care, 66% with the adapted start) than those of the stand-in (70% and 51%).
- **G-CSF by the model.** In the model-guided start the model for severe neutropenia decides on G-CSF. Together with the flags in pancreatic cancer this brings fewer severe events than the stand-in does, with fewer alerts.
- **Thromboprophylaxis.** Usual care has 288 venous thromboembolisms. The risk-adapted start lowers them to 255, the model-guided start to 197, because it flags more patients with pancreatic cancer, who all have a Khorana score of 2 or more. Major bleedings rise from 2 to 3 and 4; one of them is fatal in each of the two.
- **Lung monitoring** reaches only the patients on trastuzumab deruxtecan and reads their weekly measurements. Among them it recognised 28 of 153 lung toxicity events early, by a median of about four and a half weeks, and lowered the events of grade 3 or higher from 23 to 21. Of its 203 alerts, 41 were true. Events of grade 1 hardly change the measurements and are rarely found.
- **Cardiovascular monitoring** reaches only the men with prostate cancer. Of the 286 cardiovascular events of usual care, 147 had a warning phase. Monitoring recognised 39 of them early, by a median of three days, and prevented 14 major events and 3 of 38 cardiovascular deaths. It also recognised 127 of 236 hypertension events early and lowered those of grade 3 or higher from 234 to 143.
- With perfect detection 150 cardiovascular events remain, 25 of them fatal: the events without a warning phase.
- **Symptom monitoring** recognised about 13% of the events early, by a median of three days, because most event types worsen within days and a weekly report often comes too late.
- **Costs.** Against usual care, the combined scenario gains 0.013 quality-adjusted life years per patient for 1273 euros, about 95 000 euros per quality-adjusted life year. Symptom monitoring alone costs about 111 000. The risk-adapted start gains 0.005 for 32 euros, about 6600 euros per quality-adjusted life year; the model-guided start gains 0.004 and saves 189 euros. [Lizée et al. (2019)](../background/references.md#lizee-2019) called 30 000 euros very cost-effective and 90 000 cost-effective.

The effects of the scenarios follow from the assumed parameters of the intervention model. They show how the model behaves, not what an intervention achieves in patients.

## Uncertainty of the parameters

```bash
python3 engine/uncertainty.py --n 1500 --draws 40 --seed 1
```

Every parameter from the literature is an estimate. `uncertainty.py` repeats the simulation with parameters drawn from their published uncertainty and reports, per scenario, the mean and the 95% interval of the key numbers and of their differences to usual care.

- **Ratios with a confidence interval** are drawn from a log-normal distribution: the factors of neutropenia and the effect of G-CSF ([Lyman et al., 2011](../background/references.md#lyman-2011)), the effect of thromboprophylaxis ([Key et al., 2020](../background/references.md#key-2020)), and the effect of an earlier cardiovascular event.
- **Shares** are drawn from the beta distribution of their numbers: the cardiovascular share of the events of HERO, the share of lung toxicity that is recognised late, the excess of major bleeding.
- **Regimen rates** are drawn from the beta distribution of the trial size, for the seven regimens whose safety population is in the references, and the rate of cardiovascular events from the 308 men of HERO.
- The patients and their fixed random numbers are the same in every draw. What differs between two draws is the parameters alone.

A run with 1500 patients and 40 draws (seed 1) gives these differences to usual care, as mean and 95% interval over the draws:

| Scenario | Severe toxicity, 90 days (points) | Deaths from toxicity per 1000 | Hospital days | QALY | Cost (€) |
|---|---|---|---|---|---|
| `risk_adapted_start` | −3.7 (−3.9 to −3.3) | −2.0 (−3.4 to −1.3) | −0.3 (−0.4 to −0.3) | 0.003 (0.002 to 0.005) | 7 (−54 to 62) |
| `model_guided_start` | −4.8 (−5.3 to −4.3) | −3.8 (−5.3 to −2.7) | −0.5 (−0.5 to −0.5) | 0.005 (0.004 to 0.006) | −270 (−314 to −219) |
| `symptom_monitoring` | −1.8 (−2.1 to −1.6) | −4.0 (−4.7 to −3.3) | −0.4 (−0.5 to −0.4) | 0.004 (0.004 to 0.005) | 835 (787 to 890) |
| `combined` | −5.4 (−5.9 to −5.1) | −4.3 (−5.4 to −2.7) | −0.7 (−0.7 to −0.6) | 0.006 (0.005 to 0.007) | 1094 (1037 to 1148) |

The rate of severe toxicity in usual care itself lies between 61.9% and 65.9%. The differences between the scenarios are much more stable than the levels, because every draw moves all scenarios together. The order of the scenarios holds in every draw; whether the risk-adapted start saves or costs money does not.

`config/uncertainty.json` lists the parameters with their intervals and sources. Parameters without a published interval keep their value, among them all assumptions on participation, detection and early treatment, and the calibration is not repeated. The intervals therefore show a part of the uncertainty, and they are narrower than the truth.

## Basis of the parameters

| Part | Basis |
|---|---|
| Event rates per regimen, treatment duration, median survival | Literature, see `config/regimens.json` |
| Hazard ratios, onset distribution, grades and recognition delay of lung toxicity | Literature ([Powell et al., 2022](../background/references.md#powell-2022); [Modi et al., 2022](../background/references.md#modi-2022)) |
| Shares below 95% oxygen saturation, with lung comorbidity and by renal function | Literature ([Powell et al., 2022](../background/references.md#powell-2022)), approximately |
| Rate of cardiovascular events under a GnRH agonist and effect of an antagonist | Literature ([Shore et al., 2020](../background/references.md#shore-2020)) |
| Share of cardiovascular events among the events of HERO; effect of an earlier event | Literature ([Shore et al., 2020](../background/references.md#shore-2020); [Lopes et al., 2021](../background/references.md#lopes-2021)) |
| Patient factors of neutropenia and febrile neutropenia, effect of G-CSF | Literature ([Lyman et al., 2011](../background/references.md#lyman-2011)); odds ratios used as hazard ratios |
| Shares with raised AST and alkaline phosphatase, low white cells and immunosuppressive medication | Literature ([Lyman et al., 2011](../background/references.md#lyman-2011)), approximately |
| Timing of early events | Literature ([Extermann et al., 2012](../background/references.md#extermann-2012)), approximately |
| Share with UGT1A1*28 and the size of its effect on neutropenia and diarrhoea | Assumption; [Bardia et al. (2021)](../background/references.md#bardia-2021) and [Gennari et al. (2021)](../background/references.md#gennari-2021) report the higher risk for sacituzumab govitecan |
| Effects of age, diabetes, hypertension, smoking, renal function, cardiovascular disease without an event and frailty on cardiovascular events | Assumption; the directions follow the ESC guideline ([Lyon et al., 2022](../background/references.md#lyon-2022)) |
| Share and length of the warning phase, grades of cardiovascular events | Assumption |
| Mean age in three subgroups | Literature (median ages in ARASENS, VISION, ASCENT) |
| Shares of the three tumour types | Assumption, very coarse |
| All other baseline distributions | Assumption |
| Effects of frailty, age, bilirubin and the type-specific risk factors on the hazards | Assumption; the directions follow the report |
| Time patterns, grades and actions for events other than lung toxicity | Assumption |
| Choice of regimen and starting dose | Assumption |
| Size of the signals in the measurements, noise and missing weeks | Assumption |
| Recognition delay of lung toxicity | Literature ([Powell et al., 2022](../background/references.md#powell-2022)) |
| Days per grade of the other event types | Assumption |
| Participation, adherence, dropout, attendance, loss to follow-up | Assumption |
| Accuracy of the stand-ins for prediction and detection, false alerts | Assumption |
| Effect of early treatment, adapted start and supportive measures | Assumption, checked against GAP70+ ([Mohile et al., 2021](../background/references.md#mohile-2021)) |
| Rate of venous thromboembolism, Khorana score, effect of thromboprophylaxis and its bleeding risk | Literature ([Key et al., 2020](../background/references.md#key-2020); [de Bono et al., 2020](../background/references.md#de-bono-2020)) |
| Effect of the Khorana points on the hazard, share with thromboprophylaxis in usual care, grades of thromboembolism and bleeding | Assumption |
| Alert fatigue | Assumption |
| Hospital stays and duration of events by grade | Assumption |
| Quality-of-life weights | Literature ([Lloyd et al., 2006](../background/references.md#lloyd-2006)), found for metastatic breast cancer and used for all three tumours |
| Costs of symptom reports and of an unplanned visit | Literature ([Lizée et al., 2019](../background/references.md#lizee-2019)), French health insurance |
| Other unit costs | Placeholder values, not from the literature |

## Simplifications

Where the engine is simpler than reality or than the [intervention model](../background/intervention-model.md).

- Only events that reach grade 3 or higher in usual care are generated, and lung toxicity of any grade. Events that stay mild do not exist in the data.
- The share of cardiovascular events among the events of HERO comes from PRONOUNCE, whose men all had cardiovascular disease and were under the care of a cardiologist.
- The effect of an earlier cardiovascular event pools HERO and PRONOUNCE. The men of PRONOUNCE had atherosclerotic cardiovascular disease, not all of them an earlier event. HERO alone gives a much stronger effect under an agonist (17.8% against 4.2%) from 45 men.
- With the pooled effect the engine gives too many events under an antagonist, because men with an earlier event get an antagonist more often.
- The published odds ratios for neutropenia in the first cycle are used as hazard ratios for neutropenia of grade 3 or higher.
- Earlier chemotherapy is the same for all patients of a subgroup, so its effect on neutropenia cannot be told apart from the regimen.
- The rate of HERO is applied to all five prostate regimens. HERO treated men with advanced prostate cancer with androgen deprivation alone.
- Cardiovascular events start only while the regimen runs, although androgen deprivation continues after it. A patient has at most one cardiovascular event.
- The event types are treated as independent apart from the shared patient factors.
- Venous thromboembolism has a rate only for the pancreatic regimens and olaparib; the other regimens have none in the references. Its effect of thromboprophylaxis comes from a trial of mixed tumours and is used for as long as the therapy runs, the bleeding risk for 26 weeks.
- Bleeding exists only as the excess under thromboprophylaxis. Bleeding without an anticoagulant and contraindications to one are not modelled.
- The median onset of lung toxicity is earlier than published, because many patients stop therapy before.
- Two published risk factors for lung toxicity are not modelled: dose above the standard dose and enrolment in Japan.
- A regimen is one unit. Only the end of docetaxel after 18 weeks is modelled as a part of a combination.
- Median treatment durations from the trials are used for the end of therapy for reasons other than toxicity, although in the trials they include stops for toxicity.
- Blood tests are generated at fixed intervals and in weeks with a severe blood count event. The low point between two tests is not shown.
- There is one therapy line per patient. After its end only death is simulated, with the same hazard as before. Later therapy lines and their toxicity are missing, so the long-term course is coarse.
- Survival depends on tumour, frailty and ECOG, not on the time on therapy or the dose received. An intervention therefore changes survival only through deaths from toxicity. A factor for a faster progression at lower dose exists and is switched off.
- The stand-ins of symptom monitoring and cardiovascular monitoring do not read the generated measurements. They draw alerts from the true stage of an event.
- Home measurements come once a week. The published rule for lung toxicity speaks of a fall over one to three days.
- False alerts cost a contact and, for lung and cardiovascular monitoring, diagnostics. They do not change the therapy. Alert fatigue counts the false alerts of the same patient, not the workload of the team.
- After the end of the therapy line every patient counts as progressive, whatever the reason for the end.
- The first severe toxicity comes earlier and in a narrower time span than published.
- The share of patients flagged as high risk is fixed, so the threshold depends on the cohort.
- Most unit costs are placeholders, and the quality-of-life weights were found for breast cancer. The cost per quality-adjusted life year is therefore not a result.

## Ideas for later

The open extensions of the engine and of the interventions. Open extensions of the risk models are in [risk-model/EXTENSIONS.md](../risk-model/EXTENSIONS.md), topics that the literature does not cover in section 9 of the [toxicity report](../background/toxicity-report.md).

- Further regimens: FOLFIRINOX, gemcitabine alone, ribociclib with endocrine therapy, cabazitaxel.
- A second and third therapy line per patient, with carry-over of toxicity such as neuropathy.
- A link from time on therapy and dose received to progression and survival, so that fewer stops of therapy can show as a gain.
- Drug components of a regimen with their own schedules and dose levels.
- Cycle-based blood counts with a low point between cycles.
- Further event types from the report: QT prolongation, hypokalaemia, single immune-related organs.
- Events that stay at grade 1 or 2 in usual care.
- The single domains of the geriatric assessment, falls, LDH and the diastolic blood pressure, which the CRASH score uses ([Extermann et al., 2012](../background/references.md#extermann-2012)).
- Lung toxicity that depends on the therapy line and the dose: 10.5% in an earlier line against 15% in heavily pretreated patients ([Swain et al., 2022](../background/references.md#swain-2022)).
- Routine imaging as a way to recognise lung toxicity of grade 1, every 9 to 12 weeks in practice and every 6 weeks in trials ([Swain et al., 2022](../background/references.md#swain-2022)).
- Other cardiovascular toxicity from the report: cardiac dysfunction under HER2-targeted therapy, myocarditis under checkpoint inhibitors, ischaemia under fluoropyrimidines.
- A switch from a GnRH agonist to an antagonist for men at high cardiovascular risk as part of the risk-adapted start, as the ESC guideline suggests ([Lyon et al., 2022](../background/references.md#lyon-2022)).
- Lipids, a full SCORE2 risk and a diastolic blood pressure in the baseline record.
- Further signals: weight, temperature, potassium, liver values, troponin, ECOG over time.
- Detection models that read the weekly observations for symptom monitoring and cardiovascular monitoring as well, in place of the stand-ins.
- Alert fatigue that depends on the number of alerts per nurse, and thresholds that adapt to the workload of the care team.
- Automated advice for mild symptoms, which takes alerts off the nurses ([Di Maio et al., 2022](../background/references.md#di-maio-2022)).
- More than one way to report, with different participation by age.
- Interventions for the care team rather than the patient, for example decision support at the tumour board.
- Learning effects: the performance of a risk model improves with the data collected.
- Thresholds for alerts and for the high-risk flag as parameters of a scenario, to study the balance between early recognition and false alerts.
- The remaining unit costs from the literature, quality-of-life weights for pancreatic and prostate cancer, costs of the cancer drugs, and costs from different perspectives: health insurance, hospital, society.
- Ranges for the assumed parameters of participation, detection and early treatment, so that the uncertainty analysis covers the whole chain of effects, and a recalibration within each draw.
- A file with the latent frailty and the true risk of each patient, to test risk models against the truth.
- Dependence between event types beyond the shared patient factors.
- Published estimates in place of the assumptions in the table "Basis of the parameters".
