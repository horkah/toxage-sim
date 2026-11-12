# risk-model

Risk models for toxicity of systemic cancer therapy. They take the baseline record of a patient at the start of a therapy line and return risk scores in the format of the central [schema](../schema/). The app reads these scores.

The first two models follow candidates 1 and 2 of the [toxicity report](../background/toxicity-report.md), section 8:

| Model | Event | Applies to |
|---|---|---|
| Candidate 1 | At least one adverse event of grade 3 to 5 within 90 days | all ten regimens |
| Candidate 2 | Interstitial lung disease or pneumonitis within 730 days, any grade and grade 2 or higher | trastuzumab deruxtecan, single-agent chemotherapy in breast cancer |

Both are baseline models: they estimate the risk before therapy starts. The detection model for lung toxicity named in the report needs measurements during therapy, which schema and engine do not have yet. This and other next steps are listed in [EXTENSIONS.md](EXTENSIONS.md).

## Run

```bash
python3 engine/generate.py --n 20000 --seed 2 --out engine/output/test
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
| `models.py` | The two models, and the class `RiskModel` with `score` and `explain` |
| `config/models.json` | Coefficients, reference rates and risk categories, each with its source or marked as assumption |
| `score.py` | Command line: baseline CSV to risk score CSV |
| `evaluate.py` | Command line: discrimination and calibration against outcomes |
| `fit.py` | Command line: estimates the coefficients from data |
| `glm.py` | Binomial regression with logit and complementary log-log link |
| `metrics.py` | AUC, Brier score, calibration |
| `data.py` | Reads engine output through the schema |
| `tests/test_risk_model.py` | Tests |
| `EXTENSIONS.md` | Possible extensions of both models |

## Use from the app

```python
import sys
sys.path.insert(0, "risk-model")
import models

model = models.RiskModel()          # literature configuration
record = model.score(patient)       # one risk_score record, see schema/risk_score.schema.json
details = model.explain(patient)    # starting risk and the factors that change it
```

`score` returns for each model the risk, the published rate of the regimen for comparison, and a risk category. `explain` returns the starting risk with its source and each factor with its odds ratio or hazard ratio, so the app can show why a patient's risk differs from the regimen rate. Multiplying the starting odds (candidate 1) or applying the hazard ratios (candidate 2) gives back the score exactly.

## Candidate 1: any severe toxicity in 90 days

A logistic model. The published rate of the regimen is the risk of a reference patient: 65 years old, ECOG 0 or 1, no impaired geriatric domain. Patient factors multiply the odds:

| Factor | Odds ratio | Basis |
|---|---|---|
| Age, per 10 years from 65 | 1.2 | assumption |
| ECOG 2 or higher | 2.0 | assumption |
| Each impaired geriatric domain | 1.1 | assumption |

With these values a patient like the average GAP70+ participant (77 years, 4.5 impaired domains, regimen rate 60%) has a risk of 74%. The usual-care arm of that trial had 71% (Mohile et al., 2021). The regimen rates come from the trials listed in `config/models.json`. A missing geriatric assessment counts as no impaired domain.

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

The hazard ratios are the multivariable Cox model of Powell et al. (2022), Figure 2B. `r0` is set so that the mean risk in the pooled population of Powell et al. equals the published rate of the regimen: 12.1% for trastuzumab deruxtecan and 0.6% for single-agent chemotherapy (Modi et al., 2022). The shares of the risk factors in that population come from Powell et al., Table 2, and the factors are treated as independent. This gives `r0` = 4.6% for trastuzumab deruxtecan and 0.2% for single-agent chemotherapy.

The risk of grade 2 or higher is 71.1% of the risk of any grade, the share in Modi et al. (2022), for all patients.

Risk categories: low below 5%, intermediate from 5%, high from 15%. The thresholds are assumptions; 15% is close to the 15.4% incidence in Powell et al. (2022).

## Results on synthetic data

Literature configuration, evaluated on 20 000 patients from `engine/generate.py --seed 2`. "Regimen only" is a comparison model that gives every patient the published rate of the regimen.

| | Candidate 1 | Regimen only | Candidate 2 | Regimen only |
|---|---|---|---|---|
| Patients, events | 20 000, 13 769 | | 3962, 252 | |
| Observed / expected | 1.00 | 1.05 | 0.97 | 0.98 |
| AUC | 0.672 | 0.632 | 0.822 | 0.729 |
| Brier score | 0.198 | 0.204 | 0.053 | 0.057 |
| Calibration slope | 1.00 | 0.97 | 1.01 | 0.91 |

Within single regimens, the AUC of candidate 1 is between 0.56 and 0.62, and the AUC of candidate 2 is 0.70 for trastuzumab deruxtecan.

Fitted on 50 000 patients from seed 1, `fit.py` recovers the parameters of the engine within their confidence intervals, for example 1.19 for age, 1.94 for ECOG and 2.96 for moderate or severe renal decrease.

**These numbers do not show that the models work.** The engine generates outcomes with the same model structure and nearly the same parameters as the literature configuration. The evaluation therefore checks the code, not the medicine. The calibration of candidate 2 is not exact only because the engine sets `r0` on its own generated population, while the risk model uses the population of Powell et al. Real tests need data whose generating process differs from the model, see [EXTENSIONS.md](EXTENSIONS.md).

## Limits

- The effects of age, ECOG and geriatric domains in candidate 1 are assumptions, not estimates.
- Trial rates refer to the whole treatment period and are used as 90-day risks.
- The lung toxicity risk factors were found for trastuzumab deruxtecan and are applied to single-agent chemotherapy as well.
- Dose and enrolment in Japan, two risk factors in Powell et al. (2022), are not in the schema. All patients are treated as receiving the standard dose.
- No lung toxicity risk for checkpoint inhibitors yet, because the references give a rate but no risk model.
- The risk categories are assumptions and are not validated.
