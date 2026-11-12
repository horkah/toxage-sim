# risk-model

Risk models for therapy toxicity, based on clinical and other personal data. They are developed and tested on synthetic data from [../engine](../engine).

## Interface

All models share one interface in [toxage_risk.py](toxage_risk.py), so that the app and later evaluation code can treat them alike:

```python
import toxage_risk                     # with risk-model/ on the Python path

models = toxage_risk.load(metadata)   # one instance of every registered model
for model in models:
    model.describe()                  # id, name, outcome field, onset field, window, source
    model.applies(patient)            # does the model give a risk for this patient?
    model.risk(patient)               # probability from 0 to 1, None if not applicable
    model.reference_risk(patient)     # risk of a patient on the same regimen without risk factors
    model.factors(patient)            # list of Factor(name, label, ratio)
```

`patient` is a baseline record of the [schema](../schema/). `metadata` is the metadata of the generated data set; the lung toxicity model takes its calibrated baseline risks from it.

`Factor.ratio` is an odds ratio or a hazard ratio, as `model.ratio_kind` says. A ratio of 1 means that the factor does not apply to the patient.

The module also has metrics that compare risks with outcomes: `auc` (area under the ROC curve), `brier` (Brier score) and `calibration` (mean risk and observed rate in groups of equal size).

### Adding a model

1. Subclass `RiskModel`, set the attributes and implement `risk`, `reference_risk` and `factors` (and `applies` if the model is limited to some patients).
2. Add the class to `MODELS`.

The app then shows the new model in the status bar, as a tab for the charts, in the patient view and as a risk filter.

## Models

| id | Outcome | Candidate | Model |
|---|---|---|---|
| `severe90` | any adverse event of grade 3 to 5 within 90 days | 1 | logistic model of the engine |
| `ild` | interstitial lung disease or pneumonitis within 730 days | 2 | proportional hazards model of the engine, only for regimens with a known rate |

Both models are the models that the engine uses to generate the outcomes. On the synthetic data they therefore show the best performance any model can reach with these predictors. They are the reference against which models fitted to the data will be compared.

## Tests

```bash
python3 -m unittest discover risk-model/tests
```
