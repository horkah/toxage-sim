# engine

Generator for synthetic patient data. It is a microsimulation: every patient is simulated individually, week by week, from the start of a systemic therapy line until death or for ten years. The same patients are simulated under several intervention scenarios, so that the effect of an intervention can be read off patient by patient. The output follows the central [schema](../schema/).

The engine serves three risk model candidates of the [toxicity report](../background/toxicity-report.md) and the [intervention model](../background/intervention-model.md):

- Candidate 1: any adverse event of grade 3 to 5 within 90 days of therapy start.
- Candidate 2: interstitial lung disease or pneumonitis, including the delay until it is recognised.
- Candidate 5: major cardiovascular events under androgen deprivation for prostate cancer, including the warning phase before an event.
- Interventions: risk prediction at therapy start with an adapted start, and monitoring during therapy with early recognition and early treatment.

## Run

```bash
python3 engine/generate.py --n 3000 --seed 1 --out engine/output
```

This writes `scenario.csv`, `baseline.csv`, `observation.csv`, `event.csv`, `alert.csv`, `outcome.csv` and `metadata.json` to the output folder and prints key numbers per regimen and per scenario. `--scenarios` limits the run to some scenarios, for example `--scenarios usual_care`. The same seed gives the same data. The output folder is not under version control. 3000 patients under all seven scenarios take about 30 seconds.

```bash
python3 engine/calibrate.py
python3 -m unittest discover engine/tests
```

`calibrate.py` matches the event rates of usual care to the literature and writes `config/calibration.json`. It takes about one minute and has to be run again after every change of the model or its parameters. The engine needs Python 3 and no further packages.

## Files

| File | Content |
|---|---|
| `generate.py` | Command line entry: simulates all patients under all scenarios, checks the data against the schema, writes the files |
| `population.py` | Baseline characteristics and choice of therapy |
| `hazards.py` | Weekly hazards of adverse events |
| `draws.py` | Fixed random numbers per patient, purpose and week |
| `interventions.py` | What a scenario means for one patient: participation, adapted start, detection |
| `course.py` | Course of one patient in weekly steps under one scenario, and the outcome summary |
| `measurements.py` | Weekly observations derived from the course |
| `calibrate.py` | Calibration against the literature |
| `config/regimens.json` | Regimens with reference values and sources |
| `config/parameters.json` | Parameters of population, hazards, actions, survival and measurements |
| `config/interventions.json` | Parameters of the intervention model and the list of scenarios |
| `config/calibration.json` | Calibration factors, written by `calibrate.py` |
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

A patient is followed until death or for 520 weeks. Observations are written while the patient is on therapy and for four weeks after. The three tumour types always have equal numbers of patients.

## Patient groups

| Tumour | Subgroup | Share within tumour | Regimens |
|---|---|---|---|
| pancreas | `pancreas_metastatic` | 100% | `nalirifox`, `gemcitabine_nab_paclitaxel` |
| prostate | `prostate_hormone_sensitive` | 50% | `adt_docetaxel`, `adt_docetaxel_abiraterone`, `adt_docetaxel_darolutamide` |
| prostate | `prostate_castration_resistant` | 50% | `lu_psma_617`, `olaparib` |
| breast | `breast_her2_low` | 60% | `trastuzumab_deruxtecan`, `chemotherapy_single_agent` |
| breast | `breast_triple_negative` | 40% | `pembrolizumab_chemotherapy` |

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
| Oxygen saturation | Lung comorbidity, frailty |
| Earlier therapy lines, years since diagnosis | Subgroup |
| Neutrophils, haemoglobin, platelets | Earlier therapy lines, sex, frailty, renal function |
| Regimen | Subgroup; in pancreatic cancer frailty, age and bilirubin; in HER2-low breast cancer lung problems |
| Starting dose level | Frailty, age |
| G-CSF prophylaxis | Regimen (docetaxel) |

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

`neutropenia`, `febrile_neutropenia`, `anaemia`, `thrombocytopenia`, `diarrhoea`, `peripheral_neuropathy`, `hypertension`, `immune_related`, `interstitial_lung_disease`, `cardiovascular_event`, `other`.

The engine generates events that reach grade 3 to 5 in usual care, and interstitial lung disease of any grade. With monitoring such an event can be recognised at grade 1 or 2.

A `cardiovascular_event` is a myocardial infarction, a stroke or cardiovascular death in a man under androgen deprivation. In usual care it has grade 3, 4 or 5. If monitoring catches its warning phase and treatment works, it is recorded at grade 1 or 2 and no major event follows.

## Covariate mechanisms

These mechanisms make the data behave like real data rather than like independent random columns.

1. **Latent frailty.** Frailty drives ECOG, geriatric impairments, albumin, body mass index, haemoglobin and oxygen saturation, and it raises the hazards of adverse events and death. The observed variables are therefore correlated with each other and predict toxicity, but none of them explains it fully.
2. **Age effects.** Age lowers renal function, raises the rates of diabetes and cardiovascular disease, and adds to frailty and to the toxicity hazards.
3. **Tumour-specific patterns.** Pancreatic cancer comes with more frailty, lower albumin and weight, more diabetes and, in some patients, raised bilirubin. Castration-resistant prostate cancer and HER2-low breast cancer come with earlier therapy lines and lower blood counts.
4. **Treatment by indication.** Fitter and younger pancreatic patients more often get NALIRIFOX. Patients with lung problems less often get trastuzumab deruxtecan. Men with an earlier cardiovascular event more often get a GnRH antagonist instead of an agonist. Frail and older patients more often start with a reduced dose. Regimen and dose are therefore not independent of the patient's risk.
5. **Type-specific risk factors.** Low baseline neutrophils and earlier therapy lines raise the hazard of neutropenia, G-CSF lowers it. Low haemoglobin and renal impairment raise the hazard of anaemia. Diabetes raises the hazard of neuropathy, cardiovascular disease that of hypertension. The six published risk factors raise the hazard of lung toxicity. For cardiovascular events an earlier event raises the hazard strongly under a GnRH agonist and hardly under an antagonist, as in HERO (Shore et al., 2020); age, diabetes, hypertension, smoking, renal function, cardiovascular disease without an event and frailty add to it.
6. **Time patterns.** Neutropenia, diarrhoea and unspecified events occur mainly in the first weeks. Anaemia, low platelets, hypertension and immune-related events peak around week 8. Neuropathy grows with time on therapy. Lung toxicity follows the published onset distribution. Cardiovascular events have a constant hazard while the patient is on therapy. Toxicity from docetaxel ends after 18 weeks.
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

- **Target hazard.** From the share of trial patients with a severe event of that type, see `config/regimens.json`. The type `other` is set so that all types together give the overall rate of severe toxicity of the trial. For cardiovascular events the target is the rate of the leuprolide arm of HERO, 6.2% in 48 weeks, for all five prostate regimens.
- **Patient multiplier.** The product of the general factors (frailty, age, bilirubin above 1.5 times the upper limit) and the type-specific factors. For lung toxicity only the published hazard ratios apply. Cardiovascular events have risk factors of their own as well; the dose of the cancer therapy does not change their hazard.
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
| `risk_adapted_start` | A risk prediction at therapy start flags 30% of the patients as high risk. Flagged patients who take part get a reduced starting dose (probability 0.5), G-CSF with regimens that often cause neutropenia (0.7), supportive measures (all hazards except lung toxicity and cardiovascular events × 0.75) and weekly symptom reports. |
| `symptom_monitoring` | All patients are offered weekly symptom reports during therapy. An alert leads to contact and, if the patient attends and the team acts, to recognition on the next day. |
| `lung_monitoring` | Patients on trastuzumab deruxtecan are offered home monitoring of oxygen saturation and symptoms with a detection model for lung toxicity. |
| `cardiovascular_monitoring` | Men with prostate cancer under androgen deprivation are offered home monitoring of blood pressure and chest symptoms with a detection model. It can catch cardiovascular events that have a warning phase, and hypertension. |
| `combined` | All four |
| `perfect_detection` | As combined, with full participation, a predictor without noise, detection of every event at its first stage, early treatment that always works, and no false alerts. Cardiovascular events without a warning phase cannot be seen in advance and remain. Upper limit. |

The components of a scenario and all their parameters are in `config/interventions.json`. A new scenario is a new entry there.

**Fixed random numbers.** Every random decision of a patient is tied to a purpose and a week (`draws.py`). A scenario changes probabilities, not the random numbers. A patient whom an intervention does not reach has exactly the same course as in usual care, and a patient who is reached differs only from the point where the intervention acts. The tests check this.

**Stand-ins for the risk models.** The prediction at therapy start is the true patient-related risk plus noise; the noise sets its accuracy. The detection during therapy is a sensitivity per stage of an event, times the share of events of a type that show in symptoms, plus a rate of false alerts. Real risk models can take their place in `interventions.py`.

**Participation.** Whether a patient takes part depends on frailty and age. Reports are missing in some weeks, more often in frail patients. Each week a patient can drop out of the monitoring for good. After an alert the patient may not attend, and the team may not act. In all scenarios, including usual care, a patient on therapy can be lost to follow-up: therapy ends, and only events of grade 4 or 5 are still recognised.

**Consequences.** The grade at recognition decides the change of therapy, the probability and length of a hospital stay, intensive care, the duration of the event and the loss of quality of life. Costs are counted for unplanned visits, hospital days, diagnostics after alerts, risk assessment, set-up, monitoring weeks and the handling of alerts. The costs of the cancer drugs are not included.

## Reference values and how well they are met

Usual care, from a run with 9000 patients (seed 1), all ECOG levels included:

| Regimen | Trial: any severe toxicity | Generated: any severe toxicity | Generated: within 90 days | Generated: stopped for toxicity |
|---|---|---|---|---|
| `nalirifox` | 87% | 88% | 86% | 24% |
| `gemcitabine_nab_paclitaxel` | 86% | 84% | 82% | 22% |
| `adt_docetaxel` | 63.5% | 69% | 62% | 13% |
| `adt_docetaxel_abiraterone` | 63% | 70% | 57% | 12% |
| `adt_docetaxel_darolutamide` | 66.1% | 73% | 64% | 15% |
| `lu_psma_617` | 52.7% | 53% | 45% | 11% |
| `olaparib` | 51% | 53% | 42% | 12% |
| `trastuzumab_deruxtecan` | 52.6% | 57% | 51% | 15% |
| `chemotherapy_single_agent` | 67.4% | 70% | 68% | 9% |
| `pembrolizumab_chemotherapy` | 68.1% | 69% | 66% | 14% |

The calibration matches each event type to the literature within 0.3 percentage points in generated patients with ECOG 0 or 1 during the first 52 weeks. The table differs from the trial rates because it includes patients with ECOG 2 and events after week 52.

Further checks against the literature:

| Quantity | Literature | Generated |
|---|---|---|
| Severe toxicity within 90 days in patients aged 70 or older with at least one impaired geriatric domain, usual care | 71% (Mohile et al., 2021, usual care) | about 68% |
| The same in flagged patients who take part in the risk-adapted start, against usual care | relative risk 0.74 (Mohile et al., 2021) | 57% against 70%, relative risk 0.81 |
| Dose reduction with NALIRIFOX | 60% (Wainberg et al., 2023) | about 50% |
| Therapy stopped because of adverse events with NALIRIFOX | 32% (Wainberg et al., 2023) | about 24% |
| Lung toxicity with trastuzumab deruxtecan within 52 weeks | 10.5% (12.1% overall, 87% of events within 12 months) | about 11% |
| Share of lung toxicity recognised late | 53% (Powell et al., 2022) | about 47% |
| Median day of onset of lung toxicity | 129 (Modi et al., 2022) | about 108 |
| Cardiovascular events within 48 weeks under a GnRH agonist | 6.2% (Shore et al., 2020) | 6.5% |
| The same in men without and with an earlier event | 4.2% and 17.8% (Shore et al., 2020; 11 of 263 and 8 of 45) | 4.2% and 29% |
| Cardiovascular events within 48 weeks under a GnRH antagonist | 2.9% (Shore et al., 2020) | 4.9% |
| Share of men with an earlier cardiovascular event | 13.9% (Shore et al., 2020) | 12.4% |

Scenarios, from the same run, per patient of the whole cohort:

| Scenario | Taking part | Severe toxicity, 90 days | Severe events | Cardiovascular events | Deaths from toxicity | Hospital days | Alerts | QALY | Cost of care (€) | Cost of intervention (€) |
|---|---|---|---|---|---|---|---|---|---|---|
| `usual_care` | 0% | 66.2% | 1.21 | 299 | 194 | 3.88 | 0 | 1.788 | 4092 | 0 |
| `risk_adapted_start` | 21.2% | 62.7% | 1.11 | 298 | 169 | 3.55 | 0.60 | 1.794 | 3740 | 166 |
| `symptom_monitoring` | 78.1% | 63.8% | 1.14 | 293 | 152 | 3.42 | 2.65 | 1.796 | 3586 | 358 |
| `lung_monitoring` | 9.2% | 66.2% | 1.21 | 299 | 192 | 3.87 | 0.07 | 1.789 | 4105 | 59 |
| `cardiovascular_monitoring` | 25.0% | 66.0% | 1.20 | 283 | 191 | 3.86 | 0.57 | 1.789 | 4200 | 180 |
| `combined` | 78.1% | 60.8% | 1.05 | 283 | 145 | 3.21 | 3.28 | 1.800 | 3501 | 639 |
| `perfect_detection` | 100% | 0.4% | 0.02 | 174 | 29 | 0.15 | 1.32 | 1.839 | 183 | 844 |

Cardiovascular events and deaths from toxicity are counts among the 9000 patients, over the whole follow-up.

- Lung monitoring reaches only the patients on trastuzumab deruxtecan. Among them it recognised 37 of 118 lung toxicity events early, by a median of about three weeks, and lowered the events of grade 3 or higher from 14 to 11.
- Cardiovascular monitoring reaches only the men with prostate cancer. Of the 299 cardiovascular events of usual care, 142 had a warning phase. Monitoring recognised 47 of them early, by a median of five days, and prevented 16 major events and 3 of 38 cardiovascular deaths. It also recognised 112 of 215 hypertension events early and lowered those of grade 3 or higher from 213 to 137.
- With perfect detection 174 cardiovascular events remain, 29 of them fatal: the events without a warning phase.
- Symptom monitoring recognised about 14% of the events early, by a median of three days, because most event types worsen within days and a weekly report often comes too late.

The effects of the scenarios follow from the assumed parameters of the intervention model. They show how the model behaves, not what an intervention achieves in patients.

## Basis of the parameters

| Part | Basis |
|---|---|
| Event rates per regimen, treatment duration, median survival | Literature, see `config/regimens.json` |
| Hazard ratios, onset distribution, grades and recognition delay of lung toxicity | Literature (Powell et al., 2022; Modi et al., 2022) |
| Shares below 95% oxygen saturation, with lung comorbidity and by renal function | Literature (Powell et al., 2022), approximately |
| Rate of cardiovascular events under a GnRH agonist, effect of an earlier event and of an antagonist | Literature (Shore et al., 2020); the groups with an earlier event are small |
| Effects of age, diabetes, hypertension, smoking, renal function, cardiovascular disease without an event and frailty on cardiovascular events | Assumption; the directions follow the ESC guideline (Lyon et al., 2022) |
| Share and length of the warning phase, grades of cardiovascular events | Assumption |
| Mean age in three subgroups | Literature (median ages in ARASENS, VISION, ASCENT) |
| All other baseline distributions | Assumption |
| Effects of frailty, age, bilirubin and the type-specific risk factors on the hazards | Assumption; the directions follow the report |
| Time patterns, grades and actions for events other than lung toxicity | Assumption |
| Choice of regimen and starting dose | Assumption |
| Size of the signals in the measurements, noise and missing weeks | Assumption |
| Recognition delay of lung toxicity | Literature (Powell et al., 2022) |
| Days per grade of the other event types | Assumption |
| Participation, adherence, dropout, attendance, loss to follow-up | Assumption |
| Accuracy of the stand-ins for prediction and detection, false alerts | Assumption |
| Effect of early treatment, adapted start and supportive measures | Assumption, checked against GAP70+ (Mohile et al., 2021) |
| Hospital stays and duration of events by grade | Assumption |
| Unit costs and quality-of-life weights | Placeholder values, not from the literature |

## Simplifications

- Only events that reach grade 3 or higher in usual care are generated, and lung toxicity of any grade. Events that stay mild do not exist in the data.
- HERO counted non-fatal myocardial infarction, non-fatal stroke and death from any cause as major cardiovascular events. The engine uses its rate for cardiovascular events alone, which makes them somewhat too frequent.
- The rate of HERO is applied to all five prostate regimens. HERO treated men with advanced prostate cancer with androgen deprivation alone.
- Cardiovascular events start only while the regimen runs, although androgen deprivation continues after it. A patient has at most one cardiovascular event.
- The event types are treated as independent apart from the shared patient factors.
- The median onset of lung toxicity is earlier than published, because many patients stop therapy before.
- Two published risk factors for lung toxicity are not modelled: dose above the standard dose and enrolment in Japan.
- The risk factors for lung toxicity were found for trastuzumab deruxtecan. The engine applies them to single-agent chemotherapy as well.
- A regimen is one unit. Only the end of docetaxel after 18 weeks is modelled as a part of a combination.
- Median treatment durations from the trials are used for the end of therapy for reasons other than toxicity, although in the trials they include stops for toxicity.
- Blood tests are generated at fixed intervals and in weeks with a severe blood count event. The low point between two tests is not shown.
- There is one therapy line per patient. After its end only death is simulated, with the same hazard as before. Later therapy lines and their toxicity are missing, so the long-term course is coarse.
- Survival depends on tumour, frailty and ECOG, not on the time on therapy or the dose received. An intervention therefore changes survival only through deaths from toxicity. A factor for a faster progression at lower dose exists and is switched off.
- The detection stand-ins do not read the generated measurements. They draw alerts from the true stage of an event.
- False alerts cost a contact and, for lung and cardiovascular monitoring, diagnostics. They do not change the therapy.
- The share of patients flagged as high risk is fixed, so the threshold depends on the cohort.
- Costs and quality-of-life weights are placeholders. The cost per quality-adjusted life year is therefore not a result.

## Ideas for later

- Further regimens: FOLFIRINOX, gemcitabine alone, sacituzumab govitecan, ribociclib with endocrine therapy, cabazitaxel.
- A second and third therapy line per patient, with carry-over of toxicity such as neuropathy.
- A link from time on therapy and dose received to progression and survival, so that fewer stops of therapy can show as a gain.
- Drug components of a regimen with their own schedules and dose levels.
- Cycle-based blood counts with a low point between cycles.
- Further event types from the report: venous thromboembolism, QT prolongation, hypokalaemia, single immune-related organs.
- Events that stay at grade 1 or 2 in usual care.
- Genetic factors such as UGT1A1.
- Other cardiovascular toxicity from the report: cardiac dysfunction under HER2-targeted therapy, myocarditis under checkpoint inhibitors, ischaemia under fluoropyrimidines.
- A switch from a GnRH agonist to an antagonist for men at high cardiovascular risk as part of the risk-adapted start, as the ESC guideline suggests (Lyon et al., 2022).
- Lipids, a full SCORE2 risk and a diastolic blood pressure in the baseline record.
- Further signals: weight, temperature, potassium, liver values, troponin, ECOG over time.
- Detection by real risk models that read the weekly observations, in place of the stand-ins.
- Alert fatigue: the share of alerts acted on falls with the number of alerts.
- Thresholds for alerts and for the high-risk flag as parameters of a scenario, to study the balance between early recognition and false alerts.
- Unit costs and quality-of-life weights from the literature, and costs of the cancer drugs.
- Uncertainty: repeated runs with parameters drawn from ranges.
- A file with the latent frailty and the true risk of each patient, to test risk models against the truth.
- Dependence between event types beyond the shared patient factors.
- Replacing assumed parameters by published estimates.
