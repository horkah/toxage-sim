# risk-model

Risk models for toxicity of systemic cancer therapy. They take the baseline record of a patient at the start of a therapy line and return the risk of an outcome. All models share one interface, which the [app](../app/) uses. The scores can also be written as a table of the central [schema](../schema/).

The models follow candidates 1, 2 and 5 of the [toxicity report](../background/toxicity-report.md), section 8:

| Model | Event | Applies to |
|---|---|---|
| Candidate 1 | At least one adverse event of grade 3 to 5 within 90 days | all ten regimens |
| Candidate 2 | Interstitial lung disease or pneumonitis within 730 days, any grade and grade 2 or higher | trastuzumab deruxtecan, single-agent chemotherapy in breast cancer |
| Candidate 5 | Major cardiovascular event (myocardial infarction, stroke, cardiovascular death) within 364 days | men with prostate cancer under androgen deprivation, all five prostate regimens |

All are baseline models: they estimate the risk before therapy starts. The detection model for lung toxicity named in the report would use the weekly observations that schema and engine now provide. This and other next steps are listed in [EXTENSIONS.md](EXTENSIONS.md).

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

`fit.py` estimates the coefficients from data and writes a configuration in the same format as `config/models.json`. `score.py` and `evaluate.py` take it with `--config`:

```bash
python3 risk-model/fit.py --data engine/output/train --out risk-model/output/fitted.json
```

The code needs Python 3 and no further packages. The output folder is not under version control.

## Files

| File | Content |
|---|---|
| `toxage_risk.py` | Common interface to all risk models, used by the app |
| `models.py` | The calculations of the three models, and the class `Scorer`, which writes risk score records |
| `config/models.json` | Coefficients, reference rates and risk categories, each with its source or marked as assumption |
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
| `cv` | major cardiovascular event within 364 days | 5 |

### Adding a model

1. Put the calculation into `models.py` and its coefficients into `config/models.json`.
2. Subclass `RiskModel` in `toxage_risk.py`, set the attributes and implement `risk`, `reference_risk` and `factors` (and `applies` if the model is limited to some patients).
3. Add the class to `MODELS`.

The app then shows the new model in the status bar, as a tab for the charts, in the patient view and as a risk filter.

### Score table

`models.Scorer` computes all models at once and returns one record of the risk_score table of the schema, with the risk, the published rate of the regimen (for candidate 5 of the type of androgen deprivation) and a risk category per model. `score.py` writes this table as CSV. `Scorer.explain` returns the starting risk and the factors of a patient as a dictionary.

The risk models do not import the engine and do not read its parameters.

## Candidate 1: any severe toxicity in 90 days

A logistic model. The published rate of the regimen is the risk of a reference patient: 65 years old, ECOG 0 or 1, no impaired geriatric domain. Patient factors multiply the odds:

| Factor | Odds ratio | Basis |
|---|---|---|
| Age, per 10 years from 65 | 1.2 | assumption |
| ECOG 2 or higher | 2.0 | assumption |
| Each impaired geriatric domain | 1.1 | assumption |

With these values a patient like the average GAP70+ participant (77 years, 4.5 impaired domains, regimen rate 60%) has a risk of 74%. The usual-care arm of that trial had 71% ([Mohile et al., 2021](../background/references.md#mohile-2021)). The regimen rates come from the trials listed in `config/models.json`. A missing geriatric assessment counts as no impaired domain.

Risk categories: low below 50%, intermediate from 50%, high from 70%. The thresholds are assumptions, oriented on the two arms of GAP70+ (51% and 71%). Because the regimen rates lie between 51% and 87%, most patients are intermediate or high, and both pancreatic regimens are high for nearly everyone. This reflects the trial data.

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

The hazard ratios are the multivariable Cox model of [Powell et al. (2022)](../background/references.md#powell-2022), Figure 2B. `r0` is set so that the mean risk in the pooled population of Powell et al. equals the published rate of the regimen: 12.1% for trastuzumab deruxtecan and 0.6% for single-agent chemotherapy ([Modi et al., 2022](../background/references.md#modi-2022)). The shares of the risk factors in that population come from Powell et al., Table 2, and the factors are treated as independent. This gives `r0` = 4.6% for trastuzumab deruxtecan and 0.2% for single-agent chemotherapy.

The risk of grade 2 or higher is 71.1% of the risk of any grade, the share in [Modi et al. (2022)](../background/references.md#modi-2022), for all patients.

Risk categories: low below 5%, intermediate from 5%, high from 15%. The thresholds are assumptions; 15% is close to the 15.4% incidence in [Powell et al. (2022)](../background/references.md#powell-2022).

## Candidate 5: cardiovascular events under androgen deprivation

The ESC guideline states that no dedicated risk calculator exists for patients under androgen deprivation ([Lyon et al., 2022](../background/references.md#lyon-2022)). This model is a first one, built on the HERO trial ([Shore et al., 2020](../background/references.md#shore-2020)).

The event is a major adverse cardiovascular event within 364 days of therapy start: myocardial infarction, stroke or cardiovascular death. The model is a proportional hazards model like candidate 2: risk = 1 − (1 − r0)^HR. It differs in three points:

- The starting point is the type of androgen deprivation, not the regimen. HERO found events in 6.2% of the men on the GnRH agonist leuprolide and in 2.9% of the men on the antagonist relugolix within 48 weeks. The model brings these rates to 52 weeks (6.7% and 3.1%).
- The effect of an earlier myocardial infarction or stroke depends on the type. Under leuprolide 17.8% of the men with and 4.2% of the men without an earlier event had a new one; under relugolix 3.6% and 2.8%.
- Age enters as a continuous factor, with 71 years, the median age in HERO, as reference.

| Risk factor | Hazard ratio | Basis |
|---|---|---|
| Earlier myocardial infarction or stroke, under a GnRH agonist | 4.57 | [Shore et al. (2020)](../background/references.md#shore-2020), Table 3: 8 of 45 against 11 of 263 |
| Earlier myocardial infarction or stroke, under a GnRH antagonist | 1.29 | [Shore et al. (2020)](../background/references.md#shore-2020), Table 3: 3 of 84 against 15 of 538 |
| Age, per 10 years from 71 | 1.4 | assumption |
| Diabetes | 1.5 | assumption |
| Arterial hypertension | 1.4 | assumption |
| Current smoker | 1.7 | assumption |
| Renal function, moderate or severe decrease | 1.4 | assumption |

The two hazard ratios from HERO are ratios of the cumulative hazards of the groups. They rest on few events. The assumed factors are the risk factors the ESC guideline names for these patients; their sizes are not from the literature.

`r0` is the risk of a 71-year-old man without any of these factors. It is set so that the mean risk in a reference population equals the rate of the type of androgen deprivation: 2.8% for an agonist and 1.9% for an antagonist. The share with an earlier event in that population is from HERO (14.6% and 13.5%). The shares with diabetes (20%), hypertension (60%), current smoking (15%) and reduced renal function (20%) are assumptions, because HERO reports the risk factors only in groups.

Risk categories: low below 5%, intermediate from 5%, high from 10%. The thresholds are assumptions.

## Results on synthetic data

Literature configuration, evaluated on 20 000 patients under usual care from `engine/generate.py --seed 2 --scenarios usual_care`. "Rate only" is a comparison model that gives every patient the published rate of the regimen or, for candidate 5, of the type of androgen deprivation.

| | Candidate 1 | Rate only | Candidate 2 | Rate only | Candidate 5 | Rate only |
|---|---|---|---|---|---|---|
| Patients, events | 20 000, 13 134 | | 3994, 276 | | 6667, 402 | |
| Observed / expected | 0.92 | 0.95 | 1.02 | 0.97 | 1.10 | 1.00 |
| AUC | 0.696 | 0.693 | 0.810 | 0.723 | 0.697 | 0.547 |
| Brier score | 0.206 | 0.203 | 0.059 | 0.061 | 0.054 | 0.057 |
| Calibration slope | 0.87 | 1.07 | 1.20 | 1.23 | 0.90 | 1.01 |

Within single regimens, the AUC of candidate 1 is between 0.50 and 0.62, the AUC of candidate 2 is 0.66 for trastuzumab deruxtecan, and the AUC of candidate 5 is between 0.62 and 0.73.

How to read this:

- The engine does not generate outcomes with the models used here. Severe toxicity comes from a latent frailty, type-specific hazards, dose changes and competing events. Age, ECOG and geriatric domains predict it only because they are linked to frailty. Candidate 1 gains almost nothing over the regimen rate. This is a result, not an artefact.
- For lung toxicity the engine uses the same published hazard ratios as candidate 2, so the ranking of patients is good by construction.
- For cardiovascular events the engine uses the same hazard ratios from HERO and the same assumed factors as candidate 5, so the ranking is good by construction as well. The engine adds three things the model does not know: frailty, former smoking and cardiovascular disease without an earlier event. The model therefore predicts too few events (observed to expected 1.10), most clearly for the regimens with docetaxel (predicted 4.9%, observed 5.3% to 6.2%).
- Candidate 1 overestimates the risk for olaparib and lutetium-177–PSMA-617 (predicted 60% and 61%, observed 43% and 45%). The published rates cover the whole treatment period, and with these regimens the engine places a larger share of the events after day 90. The model also raises the risk because these patients are older than the reference patient.

Fitted on 50 000 patients from seed 1, `fit.py` gives:

- Candidate 1: odds ratios of 1.16 for age, 1.29 for ECOG 2 and 1.08 per geriatric domain.
- Candidate 2: hazard ratios near the published ones, with wide intervals because there are few events, for example 2.59 for moderate or severe renal decrease (published 2.73) and 1.27 for low oxygen saturation (published 2.14; 95% confidence interval 0.78 to 2.08, as few patients have it).
- Candidate 5: a hazard ratio of 4.23 for an earlier event under an agonist and 1.48 under an antagonist (95% confidence interval 1.05 to 2.11), and 1.45 for age, 1.41 for diabetes, 1.45 for hypertension, 1.42 for current smoking and 1.26 for reduced renal function.

On the 20 000 test patients the fitted configuration reaches an observed to expected ratio of 1.00, 1.10 and 0.93 and an AUC of 0.710, 0.811 and 0.696.

The models describe the risk without an intervention. `data.load` therefore reads the outcomes of usual care unless another scenario is named.

**These numbers do not show that the models work in patients.** All data are synthetic, and the engine rests on the same literature and on assumptions of this project.

## Limits

- The effects of age, ECOG and geriatric domains in candidate 1 are assumptions, not estimates.
- Trial rates refer to the whole treatment period and are used as 90-day risks.
- The lung toxicity risk factors were found for trastuzumab deruxtecan and are applied to single-agent chemotherapy as well.
- Dose and enrolment in Japan, two risk factors in [Powell et al. (2022)](../background/references.md#powell-2022), are not in the schema. All patients are treated as receiving the standard dose.
- The models use only part of the baseline record. Fields such as bilirubin, blood values, earlier therapy lines and starting dose are not used yet.
- Candidate 2 gives the risk within 730 days. The engine follows patients for up to ten years, so a few events fall outside the window.
- No lung toxicity risk for checkpoint inhibitors yet, because the references give a rate but no risk model.
- Candidate 5 rests on one trial. The two groups with an earlier event had 45 and 84 men, so the effect of an earlier event is uncertain.
- HERO counted death from any cause as an event. The rates of candidate 5 are therefore an upper limit for cardiovascular events alone.
- HERO treated men with androgen deprivation alone. The model applies its rates to men who also get docetaxel, abiraterone, darolutamide, olaparib or lutetium-177–PSMA-617.
- The effects of age, diabetes, hypertension, smoking and renal function in candidate 5 are assumptions. Lipids, blood pressure as a number, LVEF, troponin and natriuretic peptides are not used.
- The risk categories are assumptions and are not validated.
