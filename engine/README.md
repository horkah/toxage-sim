# engine

Generator for synthetic patient data. It is a microsimulation: every patient is simulated individually, week by week, from the start of a systemic therapy line. The output follows the central [schema](../schema/).

The engine serves the first two risk model candidates of the [toxicity report](../background/toxicity-report.md):

- Candidate 1: any adverse event of grade 3 to 5 within 90 days of therapy start.
- Candidate 2: interstitial lung disease or pneumonitis, including the delay until it is recognised.

## Run

```bash
python3 engine/generate.py --n 3000 --seed 1 --out engine/output
```

This writes `baseline.csv`, `observation.csv`, `event.csv`, `outcome.csv` and `metadata.json` to the output folder and prints key rates per regimen. The same seed gives the same data. The output folder is not under version control.

```bash
python3 engine/calibrate.py
python3 -m unittest discover engine/tests
```

`calibrate.py` matches the event rates to the literature and writes `config/calibration.json`. It has to be run again after every change of the model or its parameters. The engine needs Python 3 and no further packages.

## Files

| File | Content |
|---|---|
| `generate.py` | Command line entry: simulates all patients, checks the data against the schema, writes the files |
| `population.py` | Baseline characteristics and choice of therapy |
| `hazards.py` | Weekly hazards of adverse events |
| `course.py` | Course of one patient in weekly steps, and the outcome summary |
| `measurements.py` | Weekly observations derived from the course |
| `calibrate.py` | Calibration against the literature |
| `config/regimens.json` | Regimens with reference values and sources |
| `config/parameters.json` | All other parameters, each block marked as literature value or assumption |
| `config/calibration.json` | Calibration factors, written by `calibrate.py` |
| `tests/test_engine.py` | Tests |

## Structure of the simulation

```
latent frailty ──► baseline characteristics ──► choice of regimen and starting dose
       │                    │                              │
       └────────────────────┴───────────┬──────────────────┘
                                        ▼
        every week:   hazards of adverse events  ◄── dose level, time on therapy
                                        │
                              event with grade and action
                                        │
              dose reduction, interruption or end of therapy, death
                                        │
                                        ▼
        observations of the week: blood values, oxygen saturation, symptoms
```

A patient is followed for 52 weeks or until death. The three tumour types always have equal numbers of patients.

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
| Fatigue, diarrhoea | Exposure, frailty, events |
| Death | Tumour, frailty, ECOG, fatal adverse events |

### Event types

`neutropenia`, `febrile_neutropenia`, `anaemia`, `thrombocytopenia`, `diarrhoea`, `peripheral_neuropathy`, `hypertension`, `immune_related`, `interstitial_lung_disease`, `other`.

The engine records events of grade 3 to 5, and interstitial lung disease of any grade.

## Covariate mechanisms

These mechanisms make the data behave like real data rather than like independent random columns.

1. **Latent frailty.** Frailty drives ECOG, geriatric impairments, albumin, body mass index, haemoglobin and oxygen saturation, and it raises the hazards of adverse events and death. The observed variables are therefore correlated with each other and predict toxicity, but none of them explains it fully.
2. **Age effects.** Age lowers renal function, raises the rates of diabetes and cardiovascular disease, and adds to frailty and to the toxicity hazards.
3. **Tumour-specific patterns.** Pancreatic cancer comes with more frailty, lower albumin and weight, more diabetes and, in some patients, raised bilirubin. Castration-resistant prostate cancer and HER2-low breast cancer come with earlier therapy lines and lower blood counts.
4. **Treatment by indication.** Fitter and younger pancreatic patients more often get NALIRIFOX. Patients with lung problems less often get trastuzumab deruxtecan. Frail and older patients more often start with a reduced dose. Regimen and dose are therefore not independent of the patient's risk.
5. **Type-specific risk factors.** Low baseline neutrophils and earlier therapy lines raise the hazard of neutropenia, G-CSF lowers it. Low haemoglobin and renal impairment raise the hazard of anaemia. Diabetes raises the hazard of neuropathy, cardiovascular disease that of hypertension. The six published risk factors raise the hazard of lung toxicity.
6. **Time patterns.** Neutropenia, diarrhoea and unspecified events occur mainly in the first weeks. Anaemia, low platelets, hypertension and immune-related events peak around week 8. Neuropathy grows with time on therapy. Lung toxicity follows the published onset distribution. Toxicity from docetaxel ends after 18 weeks.
7. **Feedback.** A severe event can lead to an interruption, a dose reduction or the end of therapy. A lower dose lowers the hazard of later events. A patient who stops therapy has no further therapy-related events.
8. **Competing events.** Progression, the planned end of therapy and death end the time at risk.
9. **Delayed recognition.** Lung toxicity has a true onset day and a recognition day. In 53% of cases recognition is delayed, with a median of 43 days. Therapy continues until recognition.
10. **Signals in the measurements.** Blood values fall with exposure, more so in patients with a high hazard, and show the event in the event week. Oxygen saturation falls and cough and shortness of breath rise from the true onset of lung toxicity, so they can show it before it is recognised. Diarrhoea rises in the week before a diarrhoea event. Measurements have noise, and some weeks are missing.

## Hazard model

For each patient, week and event type:

```
hazard = target hazard of the regimen
         × time weight of the week
         × patient multiplier
         × dose level ^ 2
         × calibration factor
```

- **Target hazard.** From the share of trial patients with a severe event of that type, see `config/regimens.json`. The type `other` is set so that all types together give the overall rate of severe toxicity of the trial.
- **Patient multiplier.** The product of the general factors (frailty, age, bilirubin above 1.5 times the upper limit) and the type-specific factors. For lung toxicity only the published hazard ratios apply.
- **Calibration factor.** Set by `calibrate.py` so that generated patients with ECOG 0 or 1, who resemble trial patients, reach the published rates within the 52 weeks.

In each week at most one new event starts per patient.

## Reference values and how well they are met

Values from a run with 30 000 patients, all ECOG levels included:

| Regimen | Trial: any severe toxicity | Generated: any severe toxicity | Generated: within 90 days | Generated: stopped for toxicity |
|---|---|---|---|---|
| `nalirifox` | 87% | 90% | 89% | 27% |
| `gemcitabine_nab_paclitaxel` | 86% | 89% | 89% | 25% |
| `adt_docetaxel` | 63.5% | 68% | 63% | 9% |
| `adt_docetaxel_abiraterone` | 63% | 67% | 59% | 10% |
| `adt_docetaxel_darolutamide` | 66.1% | 73% | 69% | 10% |
| `lu_psma_617` | 52.7% | 58% | 52% | 11% |
| `olaparib` | 51% | 55% | 49% | 12% |
| `trastuzumab_deruxtecan` | 52.6% | 57% | 53% | 15% |
| `chemotherapy_single_agent` | 67.4% | 70% | 68% | 10% |
| `pembrolizumab_chemotherapy` | 68.1% | 69% | 66% | 15% |

The generated rates are above the trial rates because the generated population includes patients with ECOG 2, who would not have entered the trials.

Further checks against the literature:

| Quantity | Literature | Generated |
|---|---|---|
| Severe toxicity within 90 days in patients aged 70 or older with at least one impaired geriatric domain | 71% (Mohile et al., 2021, usual care) | about 74% |
| Reduced starting dose in the same group | 35% (Mohile et al., 2021, usual care) | about 31% |
| Dose reduction with NALIRIFOX | 60% (Wainberg et al., 2023) | about 56% |
| Therapy stopped because of adverse events with NALIRIFOX | 32% (Wainberg et al., 2023) | about 27% |
| Lung toxicity with trastuzumab deruxtecan within 52 weeks | 10.5% (12.1% overall, 87% of events within 12 months) | about 10% |
| Share of lung toxicity recognised late | 53% (Powell et al., 2022) | about 53% |
| Median day of onset of lung toxicity | 129 (Modi et al., 2022) | about 90 |

## Basis of the parameters

| Part | Basis |
|---|---|
| Event rates per regimen, treatment duration, median survival | Literature, see `config/regimens.json` |
| Hazard ratios, onset distribution, grades and recognition delay of lung toxicity | Literature (Powell et al., 2022; Modi et al., 2022) |
| Shares below 95% oxygen saturation, with lung comorbidity and by renal function | Literature (Powell et al., 2022), approximately |
| Mean age in three subgroups | Literature (median ages in ARASENS, VISION, ASCENT) |
| All other baseline distributions | Assumption |
| Effects of frailty, age, bilirubin and the type-specific risk factors on the hazards | Assumption; the directions follow the report |
| Time patterns, grades and actions for events other than lung toxicity | Assumption |
| Choice of regimen and starting dose | Assumption |
| Size of the signals in the measurements, noise and missing weeks | Assumption |

## Simplifications

- Events of grade 1 and 2 are not generated, except for lung toxicity.
- The event types are treated as independent apart from the shared patient factors.
- The median onset of lung toxicity is earlier than published, because follow-up ends after 52 weeks and many patients stop therapy before.
- Two published risk factors for lung toxicity are not modelled: dose above the standard dose and enrolment in Japan.
- The risk factors for lung toxicity were found for trastuzumab deruxtecan. The engine applies them to single-agent chemotherapy as well.
- A regimen is one unit. Only the end of docetaxel after 18 weeks is modelled as a part of a combination.
- Median treatment durations from the trials are used for the end of therapy for reasons other than toxicity, although in the trials they include stops for toxicity.
- Blood tests are generated at fixed intervals and in weeks with a blood count event. The low point between two tests is not shown.
- There is one therapy line per patient. What happens after the end of therapy is not simulated, apart from death.

## Ideas for later

- Further regimens: FOLFIRINOX, gemcitabine alone, sacituzumab govitecan, ribociclib with endocrine therapy, cabazitaxel.
- A second and third therapy line per patient, with carry-over of toxicity such as neuropathy.
- Drug components of a regimen with their own schedules and dose levels.
- Cycle-based blood counts with a low point between cycles.
- Further event types from the report: cardiovascular events under androgen deprivation, venous thromboembolism, QT prolongation, hypokalaemia, single immune-related organs.
- Events of grade 1 and 2 and the worsening of an event over time, for example of lung toxicity that is recognised late.
- Genetic factors such as UGT1A1.
- Further signals: weight, temperature, blood pressure, potassium, liver values, troponin, ECOG over time.
- Unplanned visits and hospital stays as outcomes.
- An intervention arm, for example geriatric assessment with adapted therapy or symptom monitoring with alerts, to study what earlier detection gains.
- A file with the latent frailty and the true risk of each patient, to test risk models against the truth.
- Dependence between event types beyond the shared patient factors.
- Replacing assumed parameters by published estimates.
