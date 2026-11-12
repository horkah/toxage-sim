# schema

The central data schema of the project. The engine, the risk model and the app all read field names, types and allowed values from here.

## Tables

| Table | File | Content |
|---|---|---|
| baseline | [baseline.schema.json](baseline.schema.json) | One patient at the start of a systemic therapy line |
| outcome | [outcome.schema.json](outcome.schema.json) | Toxicity outcomes of that patient |
| risk_score | [risk_score.schema.json](risk_score.schema.json) | Risk scores of that patient, computed by the [risk model](../risk-model/) |

All tables have one record per patient and are linked by `patient_id`. Days count from therapy start, which is day 1.

### baseline

| Field | Type | Values |
|---|---|---|
| `patient_id` | string | |
| `tumour_type` | string | `pancreas`, `prostate`, `breast` |
| `regimen` | string | ten regimens, see the schema file |
| `age_years` | integer | 18–100 |
| `sex` | string | `female`, `male` |
| `ecog` | integer | 0–4 |
| `ga_impaired_domains` | integer or null | 0–7, null if no geriatric assessment was done |
| `renal_function` | string | `normal`, `mild_decrease`, `moderate_severe_decrease` |
| `spo2_percent` | integer | 70–100 |
| `lung_comorbidity` | boolean | |
| `years_since_diagnosis` | number | 0 or more |

### outcome

| Field | Type | Values |
|---|---|---|
| `patient_id` | string | |
| `severe_toxicity_90d` | boolean | adverse event of grade 3 to 5 within 90 days |
| `severe_toxicity_day` | integer or null | 1–90 |
| `ild` | boolean | interstitial lung disease or pneumonitis within 730 days |
| `ild_onset_day` | integer or null | 1–730 |
| `ild_grade` | integer or null | 1–5 |

### risk_score

Risks are probabilities between 0 and 1. The `ild_` fields are null if the model does not apply to the regimen.

| Field | Type | Values |
|---|---|---|
| `patient_id` | string | |
| `model_version` | string | version of the model configuration |
| `severe_toxicity_90d_risk` | number | candidate 1: risk of an adverse event of grade 3 to 5 within 90 days |
| `severe_toxicity_90d_regimen_rate` | number | published rate of the regimen, for comparison |
| `severe_toxicity_90d_category` | string | `low`, `intermediate`, `high` |
| `ild_applicable` | boolean | candidate 2 has a rate for the regimen |
| `ild_risk` | number or null | candidate 2: risk of lung toxicity of any grade within 730 days |
| `ild_grade2plus_risk` | number or null | the same for grade 2 or higher |
| `ild_regimen_rate` | number or null | published rate of the regimen, for comparison |
| `ild_category` | string or null | `low`, `intermediate`, `high` |

## Format

The schema files are JSON Schema (draft 2020-12), so any language can read them. All fields are flat, so a table can be stored as CSV with the field names as header. In CSV, null is an empty cell and booleans are `true` and `false`.

Each schema file carries a `version`. Adding an optional field raises the minor version. Renaming or removing a field, or changing its meaning, raises the major version.

## Use from Python

[toxage_schema.py](toxage_schema.py) loads the schema and checks records. It needs only the standard library.

```python
from schema import toxage_schema

toxage_schema.fields("baseline")                      # field names in order
toxage_schema.allowed_values("baseline", "regimen")   # values of an enumerated field
toxage_schema.errors("outcome", record)               # list of problems, empty if valid
toxage_schema.validate("baseline", records)           # raises ValueError at the first invalid record
toxage_schema.write_csv(path, "baseline", records)    # write a table as CSV
toxage_schema.read_csv(path, "baseline")              # read a CSV with typed values, validated
```

## Extending the schema

- Add the field to the schema file with type, allowed range and description.
- Raise the version.
- Add the field to the table in this README.
- Let the engine fill the field. Its tests check every generated record against the schema.
- For the risk_score table, let the risk model fill the field.
