# risk-model

Risk models for toxicity of systemic cancer therapy. They take the baseline record of a patient at the start of a therapy line and return the risk of an outcome. All models share one interface, which the [app](../app/) uses. The scores can also be written as a table of the central [schema](../schema/).

The models follow candidates 1 to 5 of the [toxicity report](../background/toxicity-report.md), section 8:

| Model | Event | Applies to |
|---|---|---|
| Candidate 1 | At least one adverse event of grade 3 to 5 within 90 days | all eleven regimens |
| Candidate 2 | Interstitial lung disease or pneumonitis within 730 days, any grade and grade 2 or higher | trastuzumab deruxtecan, single-agent chemotherapy in breast cancer |
| Candidate 3 | Neutropenia of grade 3 or higher or febrile neutropenia within 90 days | the eight regimens with a published rate of severe neutropenia |
| Candidate 4 | Diarrhoea of grade 3 or higher within 90 days | NALIRIFOX, gemcitabine with nab-paclitaxel, sacituzumab govitecan |
| Candidate 5 | Major cardiovascular event (myocardial infarction, stroke, cardiovascular death) within 364 days | men with prostate cancer under androgen deprivation, all five prostate regimens |

All five are baseline models: they estimate the risk before therapy starts. A sixth model works during therapy: the detection model for lung toxicity reads the weekly home measurements and says when a patient should be examined. Next steps are listed in [EXTENSIONS.md](EXTENSIONS.md).

## Run

```bash
python3 engine/generate.py --n 20000 --seed 2 --scenarios usual_care --out engine/output/test
```

```bash
python3 risk-model/score.py --baseline engine/output/test/baseline.csv --out risk-model/output/risk_score.csv
```

```bash
python3 risk-model/evaluate.py --data engine/output/test
```

```bash
python3 -m unittest discover risk-model/tests
```

```bash
python3 risk-model/detect.py --data engine/output/test
```

`fit.py` estimates the coefficients from data and writes a configuration in the same format as `config/models.json`. `score.py` and `evaluate.py` take it with `--config`:

```bash
python3 risk-model/fit.py --data engine/output/train --out risk-model/output/fitted.json
```

The code needs Python 3 and no further packages. The output folder is not under version control.

## Files

| File | Content |
|---|---|
| `toxage_risk.py` | Common interface to all risk models, used by the app |
| `models.py` | The calculations of the five models, and the class `Scorer`, which writes risk score records |
| `config/models.json` | Coefficients, reference rates and risk categories, each with its source or marked as assumption |
| `detect.py` | Detection model for lung toxicity on weekly observations, and its evaluation |
| `score.py` | Command line: baseline CSV to risk score CSV |
| `evaluate.py` | Command line: discrimination and calibration against outcomes |
| `fit.py` | Command line: estimates the coefficients from data |
| `glm.py` | Binomial regression with logit and complementary log-log link |
| `metrics.py` | AUC, Brier score, calibration |
| `data.py` | Reads engine output through the schema |
| `tests/test_risk_model.py` | Tests of the calculations, fitting and evaluation |
| `tests/test_risk.py` | Tests of the common interface |
| `EXTENSIONS.md` | Possible extensions of the models |

## Interface

All models share one interface in [toxage_risk.py](toxage_risk.py), so that the app and evaluation code can treat them alike:

```python
import toxage_risk                     # with risk-model/ on the Python path

models = toxage_risk.load()           # one instance of every registered model
for model in models:
    model.describe()                  # id, name, outcome field, onset field, window, source
    model.applies(patient)            # does the model give a risk for this patient?
    model.risk(patient)               # probability from 0 to 1, None if not applicable
    model.reference_risk(patient)     # risk of a patient on the same regimen without risk factors
    model.factors(patient)            # list of Factor(name, label, ratio)
```

`patient` is a baseline record of the [schema](../schema/). `load` takes another model configuration as argument, for example one written by `fit.py`.

`Factor.ratio` is an odds ratio or a hazard ratio, as `model.ratio_kind` says. A ratio of 1 means that the factor does not apply to the patient. The reference risk combined with all ratios gives back the risk exactly.

The module also offers `auc`, `brier` and `calibration` in a form that leaves out patients for whom a model gives no risk.

| id | Outcome | Candidate |
|---|---|---|
| `severe90` | any adverse event of grade 3 to 5 within 90 days | 1 |
| `ild` | interstitial lung disease or pneumonitis within 730 days | 2 |
| `neutropenia` | neutropenia of grade 3 or higher or febrile neutropenia within 90 days | 3 |
| `diarrhoea` | diarrhoea of grade 3 or higher within 90 days | 4 |
| `cv` | major cardiovascular event within 364 days | 5 |

Two models answer further questions:

```python
lung.risk_by_day(patient, 180)               # risk of lung toxicity up to day 180
lung.remaining_risk(patient, 180)            # risk in the rest of the window if free of it on day 180
heart.risk_on(patient, "gnrh_antagonist")    # risk of the same man on the other type of androgen deprivation
```

### Adding a model

1. Put the calculation into `models.py` and its coefficients into `config/models.json`.
2. Subclass `RiskModel` in `toxage_risk.py`, set the attributes and implement `risk`, `reference_risk` and `factors` (and `applies` if the model is limited to some patients).
3. Add the class to `MODELS`.

The app then shows the new model in the status bar, as a tab for the charts, in the patient view and as a risk filter.

### Score table

`models.Scorer` computes all models at once and returns one record of the risk_score table of the schema, with the risk, the published rate of the regimen (for candidate 5 of the type of androgen deprivation, brought to cardiovascular events) and a risk category per model. `score.py` writes this table as CSV. `Scorer.explain` returns the starting risk and the factors of a patient as a dictionary.

The risk models do not import the engine and do not read its parameters. The engine imports the risk models: its scenario "model-guided start" flags patients with candidate 1 and decides on G-CSF with candidate 3, and its lung monitoring uses the detection model.

## Candidate 1: any severe toxicity in 90 days

A logistic model. The published rate of the regimen is the risk of a reference patient: 65 years old, ECOG 0 or 1, no impaired geriatric domain, haemoglobin 12.3 g/dl, albumin 38 g/l, full starting dose. Patient factors multiply the odds:

| Factor | Odds ratio | Basis |
|---|---|---|
| Age, per 10 years from 65 | 1.1 | assumption; [Extermann et al. (2012)](../background/references.md#extermann-2012) found no effect of age among patients of 70 or older once the regimen was taken into account |
| ECOG 2 or higher | 2.0 | assumption |
| Each impaired geriatric domain | 1.1 | assumption |
| Haemoglobin, per g/dl below 12.3 | 1.11 | [Extermann et al. (2012)](../background/references.md#extermann-2012), Table 2: 0.90 per g/dl, P = .12 |
| Albumin, per 10 g/l below 38 | 1.35 | [Extermann et al. (2012)](../background/references.md#extermann-2012), Table 2: 0.74 per g/dl, P = .22 |
| Reduced starting dose | 0.75 | assumption |

Haemoglobin and albumin count in both directions: values above the reference lower the risk. Both odds ratios were found for non-haematological toxicity of grade 3 or 4 in patients aged 70 or older and were not statistically significant there.

With these values a patient like the average GAP70+ participant (77 years, 4.5 impaired domains, regimen rate 60%) has a risk of 72%. The usual-care arm of that trial had 71% ([Mohile et al., 2021](../background/references.md#mohile-2021)). The regimen rates come from the trials listed in `config/models.json`. A missing geriatric assessment counts as no impaired domain.

Risk categories: low below 50%, intermediate from 50%, high from 70%. The thresholds are assumptions, oriented on the two arms of GAP70+ (51% and 71%). Because the regimen rates lie between 51% and 87%, most patients are intermediate or high, and both pancreatic regimens are high for nearly everyone. This reflects the trial data.

The CRASH score of [Extermann et al. (2012)](../background/references.md#extermann-2012) is the closest published tool. It reached a c-statistic of 0.65 for any severe toxicity in its derivation sample and 0.64 in its validation sample, and it found that patient differences count two to three times more than regimen differences.

## Candidate 2: lung toxicity

A proportional hazards model: risk = 1 − (1 − r0)^HR. `r0` is the risk of a patient without any risk factor on the regimen, `HR` the product of the hazard ratios that apply:

| Risk factor | Hazard ratio |
|---|---|
| Age below 65 | 1.56 |
| Lung comorbidity | 1.75 |
| Renal function, mild decrease | 1.24 |
| Renal function, moderate or severe decrease | 2.73 |
| More than 4 years since diagnosis | 1.82 |
| Oxygen saturation below 95% | 2.14 |

The hazard ratios are the multivariable Cox model of [Powell et al. (2022)](../background/references.md#powell-2022), Figure 2B. They were found for trastuzumab deruxtecan and apply to this regimen only. `r0` is set so that the mean risk in the pooled population of Powell et al. equals the published rate of 12.1% ([Modi et al., 2022](../background/references.md#modi-2022)). The shares of the risk factors in that population come from Powell et al., Table 2, and the factors are treated as independent. This gives `r0` = 4.6%. Every patient on single-agent chemotherapy gets the published rate of 0.6%.

The risk of grade 2 or higher is 71.1% of the risk of any grade, the share in [Modi et al. (2022)](../background/references.md#modi-2022), for all patients. The eight pooled studies in [Swain et al. (2022)](../background/references.md#swain-2022) give the same share, 99 of 139.

**Risk over time.** The onset time is log-normal with a median of 129 days ([Modi et al., 2022](../background/references.md#modi-2022)) and 87% of the events within 12 months ([Powell et al., 2022](../background/references.md#powell-2022)). From this the model gives the risk up to any day and the remaining risk of a patient who is still free of lung toxicity. For a patient who is free of lung toxicity after one year, about a tenth of the risk remains. [Swain et al. (2022)](../background/references.md#swain-2022) report 97% of the events within 12 months and a risk of 1.8% for patients who were still on treatment then.

Risk categories: low below 5%, intermediate from 5%, high from 15%. The thresholds are assumptions; 15% is close to the 15.4% incidence in [Powell et al. (2022)](../background/references.md#powell-2022).

## Detection model for lung toxicity

The baseline model of candidate 2 says who is at risk. The detection model follows a patient on trastuzumab deruxtecan week by week and gives an alert when the patient should be examined. It reads three values of the observation table: oxygen saturation, cough and breathlessness.

The rule follows an expert panel: a fall of the oxygen saturation at rest by 2 to 4 points against the patient's own value should lead to an examination ([Swain et al., 2022](../background/references.md#swain-2022)). For one report per week it reads:

- alert if the saturation is 4 points or more below the patient's reference, or
- 2 points or more below it in two reports in a row, or
- 2 points or more below it together with cough or breathlessness that is 2 levels or more above the patient's reference.

The reference is the first report of the patient. After an alert the patient is examined, and the detector starts again from the current report. A report without a saturation says nothing. The confirmation by a second report or by symptoms keeps single noisy values from giving alerts; it is an assumption, as is the size of the symptom rise.

```python
import detect

detector = detect.LungDetector()
detector.report({"spo2_percent": 98, "pro_cough": 0, "pro_dyspnoea": 1})   # False, sets the reference
detector.report({"spo2_percent": 96, "pro_cough": 0, "pro_dyspnoea": 3})   # True
```

The engine uses this model for its scenario "lung monitoring": the alerts of the scenario, true and false, follow from the generated measurements. `detect.evaluate` measures the model on data of usual care: the share of lung toxicity events with an alert before usual care recognises them, the days gained, and the false alerts per patient-week.

Lung toxicity of grade 1 has no symptoms and shows only in imaging ([Swain et al., 2022](../background/references.md#swain-2022)). The engine gives such events a small fall of the saturation, so the model finds few of them. This limit belongs to home measurements, not to the rule.

## Candidate 3: severe or febrile neutropenia

A logistic model with the patient factors of [Lyman et al. (2011)](../background/references.md#lyman-2011). That study followed 3760 patients who started chemotherapy in 115 US practices and predicted severe or febrile neutropenia in the first cycle with an area under the curve of 0.83 in the derivation sample and 0.81 in the validation sample.

| Factor | Odds ratio | Basis |
|---|---|---|
| Earlier chemotherapy | 1.925 | Lyman et al., Table 3 |
| Age 65 or older | 1.297 | Lyman et al., Table 3; 95% confidence interval 0.96 to 1.75 |
| AST above 35 U/l | 1.422 | Lyman et al., Table 3; 95% confidence interval 0.99 to 2.04 |
| Alkaline phosphatase above 120 U/l | 1.469 | Lyman et al., Table 3 |
| Bilirubin above normal | 2.152 | Lyman et al., Table 3, bilirubin above 1 mg/dl |
| Renal function, per ml/min of eGFR from 80 | 0.993 | Lyman et al., Table 3 |
| White cells, per 10^9/l from 7 | 0.930 | Lyman et al., Table 3 |
| Immunosuppressive medication | 1.554 | Lyman et al., Table 3 |
| Reduced starting dose | 0.496 | Lyman et al., Table 3: 2.018 for a planned dose intensity of 85% or more |
| G-CSF prophylaxis | 0.120 | Lyman et al., Table 3 |
| UGT1A1*28 homozygous, with irinotecan | 2.0 | assumption |

The drug classes of the published model are not used: the published rate of the regimen takes their place. The risk of the reference patient is set so that the mean risk in a reference population equals that rate. The reference patient has none of the yes-or-no factors, an eGFR of 80 ml/min and white cells of 7. The shares with raised liver values and immunosuppressive medication in the reference population are those of Lyman et al., Table 1. The shares with earlier chemotherapy, G-CSF and an age of 65 or older belong to the trial of each regimen and are partly assumptions; `config/models.json` lists them.

For the two regimens with docetaxel from ARASENS and for sacituzumab govitecan the rate combines neutropenia and febrile neutropenia of grade 3 or 4 as if they were independent.

Risk categories: low below 10%, intermediate from 10%, high from 20%. The thresholds are assumptions: 10% separated low from high risk in Lyman et al., and 20% is the risk of febrile neutropenia from which guidelines recommend G-CSF from the first cycle, as cited there.

## Candidate 4: severe diarrhoea

A logistic model for the two pancreatic regimens, with 20% and 5% severe diarrhoea in NAPOLI 3 ([Wainberg et al., 2023](../background/references.md#wainberg-2023)), and for sacituzumab govitecan, with 10% in ASCENT ([Bardia et al., 2021](../background/references.md#bardia-2021)). The references name risk factors but give no effect sizes, so all odds ratios are assumptions:

| Factor | Odds ratio |
|---|---|
| Age 70 or older | 1.3 |
| ECOG 2 or higher | 1.5 |
| Albumin below 35 g/l | 1.3 |
| UGT1A1*28 homozygous, with irinotecan | 2.0 |

The higher risk with two copies of UGT1A1*28 is reported for sacituzumab govitecan ([Bardia et al., 2021](../background/references.md#bardia-2021); [Gennari et al., 2021](../background/references.md#gennari-2021)), without an effect size. The same factor is applied to the irinotecan in NALIRIFOX, because both drugs act through SN-38. As in candidate 3, the risk of the reference patient is set so that the mean risk in a reference population equals the regimen rate.

Risk categories: low below 10%, intermediate from 10%, high from 20%. The thresholds are assumptions. This model has the weakest basis of the five.

## Candidate 5: cardiovascular events under androgen deprivation

The ESC guideline states that no dedicated risk calculator exists for patients under androgen deprivation ([Lyon et al., 2022](../background/references.md#lyon-2022)). This model is a first one, built on the trials HERO ([Shore et al., 2020](../background/references.md#shore-2020)) and PRONOUNCE ([Lopes et al., 2021](../background/references.md#lopes-2021)).

The event is a major adverse cardiovascular event within 364 days of therapy start: myocardial infarction, stroke or cardiovascular death. The model is a proportional hazards model like candidate 2: risk = 1 − (1 − r0)^HR.

- **Rates.** The starting point is the type of androgen deprivation. HERO found events in 6.2% of the men on the GnRH agonist leuprolide and in 2.9% of the men on the antagonist relugolix within 48 weeks. HERO counted death from any cause as an event. In PRONOUNCE 16 of the 26 men with such an event had cardiovascular death, myocardial infarction or stroke. The model uses this share of 61.5% and brings the rates to 52 weeks: 4.1% and 1.9%.
- **Earlier event.** Under leuprolide HERO saw events in 8 of 45 men with and 11 of 263 men without an earlier myocardial infarction or stroke; under relugolix in 3 of 84 and 15 of 538. PRONOUNCE enrolled only men with atherosclerotic cardiovascular disease and saw events in 11 of 269 under leuprolide and 15 of 275 under the antagonist degarelix. The model counts these men as men with an earlier event and pools both trials.
- **Age** enters as a continuous factor, with 71 years, the median age in HERO, as reference.

| Risk factor | Hazard ratio | Basis |
|---|---|---|
| Earlier myocardial infarction or stroke, under a GnRH agonist | 1.46 | HERO and PRONOUNCE: 19 of 314 against 11 of 263 |
| Earlier myocardial infarction or stroke, under a GnRH antagonist | 1.82 | HERO and PRONOUNCE: 18 of 359 against 15 of 538 |
| Age, per 10 years from 71 | 1.4 | assumption |
| Diabetes | 1.5 | assumption |
| Arterial hypertension | 1.4 | assumption |
| Current smoker | 1.7 | assumption |
| Former smoker | 1.2 | assumption |
| Renal function, moderate or severe decrease | 1.4 | assumption |
| Cardiovascular disease without an earlier event | 1.5 | assumption |

The two pooled hazard ratios are ratios of the cumulative hazards of the groups. HERO alone gives 4.57 under an agonist and 1.29 under an antagonist, from 45 and 84 men. With PRONOUNCE the advantage of an antagonist for men with an earlier event shrinks: in the model their risk is lower by somewhat less than half, where HERO alone shows four fifths (3.6% against 17.8%). PRONOUNCE itself found no difference (hazard ratio 1.28, 95% confidence interval 0.59 to 2.79) and calls the question unresolved. The assumed factors are the risk factors the ESC guideline names for these patients; their sizes are not from the literature.

`r0` is the risk of a 71-year-old man without any of these factors. It is set so that the mean risk in a reference population equals the rate of the type of androgen deprivation: 2.3% for an agonist and 1.0% for an antagonist. The share with an earlier event in that population is from HERO (14.6% and 13.5%). Diabetes (16%) and hypertension (45%) come from a cohort of 2492 men with prostate cancer that [Lopes et al. (2021)](../background/references.md#lopes-2021) report; current (15%) and former smoking (39%) from PRONOUNCE. The shares with reduced renal function (20%) and with cardiovascular disease without an earlier event (8%) are assumptions.

Risk categories: low below 5%, intermediate from 5%, high from 10%. The thresholds are assumptions.

## Results on synthetic data

Literature configuration, evaluated on 20 000 patients under usual care from `engine/generate.py --seed 2 --scenarios usual_care`. "Rate only" is a comparison model that gives every patient the published rate of the regimen or, for candidate 5, of the type of androgen deprivation.

| | Candidate 1 | Rate only | Candidate 2 | Rate only | Candidate 3 | Rate only | Candidate 4 | Rate only | Candidate 5 | Rate only |
|---|---|---|---|---|---|---|---|---|---|---|
| Patients, events | 20 000, 13 473 | | 3983, 243 | | 14 018, 4073 | | 6667, 790 | | 6667, 285 | |
| Observed / expected | 0.98 | 0.97 | 0.88 | 0.85 | 0.97 | 1.01 | 0.87 | 0.94 | 1.15 | 1.15 |
| AUC | 0.710 | 0.692 | 0.789 | 0.717 | 0.738 | 0.660 | 0.712 | 0.686 | 0.644 | 0.516 |
| Brier score | 0.195 | 0.198 | 0.054 | 0.055 | 0.175 | 0.192 | 0.099 | 0.099 | 0.041 | 0.041 |
| Calibration slope | 0.91 | 1.06 | 1.00 | 1.18 | 1.01 | 1.03 | 1.12 | 1.13 | 0.82 | 0.30 |

Within single regimens, the AUC of candidate 1 is between 0.54 and 0.63, of candidate 2 0.63 for trastuzumab deruxtecan, of candidate 3 between 0.63 and 0.76, of candidate 4 0.55 and 0.57, and of candidate 5 between 0.62 and 0.68.

How to read this:

- The engine does not generate outcomes with the models used here. Severe toxicity comes from a latent frailty, type-specific hazards, dose changes and competing events. Age, ECOG, geriatric domains, haemoglobin and albumin predict it only because they are linked to frailty. Candidate 1 gains little over the regimen rate. This is a result, not an artefact, and it agrees with the published scores for this event.
- For lung toxicity the engine uses the same published hazard ratios as candidate 2, so the ranking of patients is good by construction.
- For neutropenia the engine uses the published odds ratios of candidate 3 as hazard ratios, so the ranking is good by construction as well. G-CSF alone separates the patients on docetaxel clearly. The model predicts too many events with docetaxel and abiraterone (16.3% against 9.4%).
- Candidate 4 separates the two regimens and little else. Within a regimen only the UGT1A1 genotype and age carry information, and the engine has no effect of ECOG or albumin of its own.
- For cardiovascular events the engine uses the same pooled hazard ratios and the same assumed factors as candidate 5. It adds frailty, which the model does not know. The model therefore predicts too few events (observed to expected 1.15). With the pooled effect of an earlier event the patients differ less in risk than with HERO alone, and the AUC is lower than a model built on HERO alone would reach on data built on HERO alone.
- Candidate 1 overestimates the risk for olaparib and lutetium-177–PSMA-617 (predicted 55% and 56%, observed 46% and 49%). The published rates cover the whole treatment period, and with these regimens the engine places a larger share of the events after day 90.

Fitted on 50 000 patients from seed 1, `fit.py` gives:

- Candidate 1: odds ratios of 1.19 for age, 1.15 for ECOG 2, 1.07 per geriatric domain, 1.09 per g/dl of haemoglobin, 1.67 per 10 g/l of albumin and 0.62 for a reduced starting dose.
- Candidate 2: hazard ratios near the published ones, with wide intervals because there are few events, for example 2.35 for moderate or severe renal decrease (published 2.73) and 1.58 for low oxygen saturation (published 2.14; 95% confidence interval 0.99 to 2.55, as few patients have it).
- Candidate 3: odds ratios near the published ones, for example 0.19 for G-CSF (published 0.12), 2.32 for raised bilirubin (2.15), 1.61 for immunosuppressive medication (1.55) and 2.05 for UGT1A1 with irinotecan (assumed 2.0). A reduced starting dose gives 0.78 (published 0.50). Earlier chemotherapy cannot be estimated, because it is the same for all patients of a regimen.
- Candidate 4: 1.42 for an age of 70 or older, 2.16 for UGT1A1 with irinotecan, 1.21 for low albumin and 1.05 for ECOG 2 (95% confidence interval 0.93 to 1.20).
- Candidate 5: a hazard ratio of 1.05 for an earlier event under an agonist (95% confidence interval 0.81 to 1.38) and 1.89 under an antagonist, and 1.44 for age, 1.27 for diabetes, 1.38 for hypertension, 1.40 for current smoking, 1.42 for reduced renal function and 1.44 for cardiovascular disease without an event.

On the 20 000 test patients the fitted configuration reaches an observed to expected ratio of 0.99, 0.95, 1.00, 0.92 and 1.02 and an AUC of 0.722, 0.790, 0.747, 0.713 and 0.644.

The models describe the risk without an intervention. `data.load` therefore reads the outcomes of usual care unless another scenario is named.

**These numbers do not show that the models work in patients.** All data are synthetic, and the engine rests on the same literature and on assumptions of this project.

## Limits

- The effects of age, ECOG, geriatric domains and starting dose in candidate 1 are assumptions. The effects of haemoglobin and albumin come from one study of patients aged 70 or older, for non-haematological toxicity, and were not statistically significant there.
- Trial rates refer to the whole treatment period and are used as 90-day risks.
- Dose and enrolment in Japan, two risk factors in [Powell et al. (2022)](../background/references.md#powell-2022), are not in the schema. All patients are treated as receiving the standard dose.
- Candidate 2 gives the risk within 730 days. The engine follows patients for up to ten years, so a few events fall outside the window.
- No lung toxicity risk for checkpoint inhibitors, because the references give a rate but no risk model.
- Candidate 3 uses odds ratios that were found for neutropenia with a neutrophil count below 0.5 or febrile neutropenia in the first cycle, in breast, lung, colorectal and ovarian cancer and lymphoma. The model applies them to neutropenia of grade 3 or higher within 90 days in pancreatic, prostate and breast cancer.
- The trial shares with G-CSF and with an age of 65 or older in candidate 3 are assumptions.
- Candidate 3 has no rate for lutetium-177–PSMA-617, olaparib and pembrolizumab with chemotherapy.
- All effect sizes of candidate 4 are assumptions, and it covers three regimens.
- Candidate 5 rests on two trials. PRONOUNCE was stopped early, its men were under the care of a cardiologist, and they had cardiovascular disease, not all of them an earlier event.
- HERO treated men with androgen deprivation alone. The model applies its rates to men who also get docetaxel, abiraterone, darolutamide, olaparib or lutetium-177–PSMA-617.
- The effects of age, diabetes, hypertension, smoking, renal function and cardiovascular disease without an event in candidate 5 are assumptions. Lipids, blood pressure as a number, LVEF, troponin and natriuretic peptides are not used.
- The risk categories are assumptions and are not validated.
