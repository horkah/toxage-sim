# schema

The central data schema of the project. The engine, the risk model and the app all read field names, types and allowed values from here.

## Tables

| Table | File | Content | Records |
|---|---|---|---|
| baseline | [baseline.schema.json](baseline.schema.json) | One patient at the start of a systemic therapy line | one per patient |
| observation | [observation.schema.json](observation.schema.json) | Therapy status, measurements and patient-reported symptoms in one week | one per patient and week |
| event | [event.schema.json](event.schema.json) | One adverse event | none, one or several per patient |
| outcome | [outcome.schema.json](outcome.schema.json) | Summary of the course of the patient | one per patient |
| risk_score | [risk_score.schema.json](risk_score.schema.json) | Risk scores at therapy start, computed by the [risk model](../risk-model/) | one per patient |

All tables are linked by `patient_id`. Days count from therapy start, which is day 1. Week 0 covers days 1 to 7.

The schema files hold the full description and unit of every field. The tables below give an overview.

### baseline

| Field | Type | Values |
|---|---|---|
| `patient_id` | string |  |
| `tumour_type` | string | `pancreas`, `prostate`, `breast` |
| `subgroup` | string | `pancreas_metastatic`, `prostate_hormone_sensitive`, `prostate_castration_resistant`, `breast_her2_low`, `breast_triple_negative` |
| `regimen` | string | 10 values, see the schema file |
| `prior_therapy_lines` | integer | 0 or more |
| `starting_dose_level` | number | 0.1–1.0 |
| `gcsf_prophylaxis` | boolean |  |
| `age_years` | integer | 18–100 |
| `sex` | string | `female`, `male` |
| `ecog` | integer | 0–4 |
| `ga_impaired_domains` | integer or null | 0–7 |
| `bmi` | number | 10–60 |
| `albumin_g_l` | number | 10–60 |
| `egfr_ml_min` | integer | 5–150 |
| `renal_function` | string | `normal`, `mild_decrease`, `moderate_severe_decrease` |
| `bilirubin_ratio_uln` | number | 0 or more |
| `neutrophils_10e9_l` | number | 0 or more |
| `haemoglobin_g_dl` | number | 0 or more |
| `platelets_10e9_l` | integer | 0 or more |
| `spo2_percent` | integer | 70–100 |
| `lung_comorbidity` | boolean |  |
| `diabetes` | boolean |  |
| `cardiovascular_disease` | boolean |  |
| `years_since_diagnosis` | number | 0 or more |

### observation

| Field | Type | Values |
|---|---|---|
| `patient_id` | string |  |
| `week` | integer | 0 or more |
| `day` | integer | 1 or more |
| `treatment_status` | string | `on_treatment`, `interrupted`, `stopped` |
| `dose_level` | number or null | 0.1–1.0 |
| `neutrophils_10e9_l` | number or null | 0 or more |
| `haemoglobin_g_dl` | number or null | 0 or more |
| `platelets_10e9_l` | integer or null | 0 or more |
| `spo2_percent` | integer or null | 50–100 |
| `pro_fatigue` | integer or null | 0–4 |
| `pro_diarrhoea` | integer or null | 0–4 |
| `pro_cough` | integer or null | 0–4 |
| `pro_dyspnoea` | integer or null | 0–4 |

### event

| Field | Type | Values |
|---|---|---|
| `patient_id` | string |  |
| `event_type` | string | 10 values, see the schema file |
| `grade` | integer | 1–5 |
| `onset_day` | integer | 1 or more |
| `day` | integer | 1 or more |
| `action` | string | `none`, `interruption`, `dose_reduction`, `discontinuation` |

`onset_day` is the day the event actually started, `day` the day it was recognised. They differ when recognition was delayed.

### outcome

| Field | Type | Values |
|---|---|---|
| `patient_id` | string |  |
| `follow_up_days` | integer | 1 or more |
| `severe_toxicity_90d` | boolean |  |
| `severe_toxicity_day` | integer or null | 1–90 |
| `ild` | boolean |  |
| `ild_onset_day` | integer or null | 1 or more |
| `ild_diagnosis_day` | integer or null | 1 or more |
| `ild_grade` | integer or null | 1–5 |
| `treatment_end_day` | integer or null | 1 or more |
| `treatment_end_reason` | string | `ongoing`, `progression`, `toxicity`, `completed`, `death` |
| `death_day` | integer or null | 1 or more |

The outcome table is derived from the event and observation tables. It holds the targets of the risk models.

### risk_score

| Field | Type | Values |
|---|---|---|
| `patient_id` | string |  |
| `model_version` | string |  |
| `severe_toxicity_90d_risk` | number | 0–1 |
| `severe_toxicity_90d_regimen_rate` | number | 0–1 |
| `severe_toxicity_90d_category` | string | `low`, `intermediate`, `high` |
| `ild_applicable` | boolean |  |
| `ild_risk` | number or null | 0–1 |
| `ild_grade2plus_risk` | number or null | 0–1 |
| `ild_regimen_rate` | number or null | 0–1 |
| `ild_category` | string or null | `low`, `intermediate`, `high` |

Risks are probabilities. The `ild_` fields are null if the lung toxicity model does not apply to the regimen. The baseline, observation, event and outcome tables are written by the engine, the risk_score table by the risk model.

## Format

The schema files are JSON Schema (draft 2020-12), so any language can read them. All fields are flat, so a table can be stored as CSV with the field names as header. In CSV, null is an empty cell and booleans are `true` and `false`.

Each schema file carries a `version`, currently 0.2.1 for the four tables of the engine and 0.1.1 for risk_score. Adding an optional field raises the minor version. Renaming or removing a field, or changing its meaning, raises the major version. Changes that leave the data as they are, such as a new `title`, raise the patch version.

Every field has a `title`, which the app shows as its label, and a `unit` where one applies.

## Use from Python

[toxage_schema.py](toxage_schema.py) loads the schema and checks records. It needs only the standard library.

```python
from schema import toxage_schema

toxage_schema.TABLES                                  # names of the tables
toxage_schema.fields("baseline")                      # field names in order
toxage_schema.allowed_values("baseline", "regimen")   # values of an enumerated field
toxage_schema.errors("outcome", record)               # list of problems, empty if valid
toxage_schema.validate("baseline", records)           # raises ValueError at the first invalid record
toxage_schema.write_csv(path, "baseline", records)    # write a table as CSV
toxage_schema.read_csv(path, "baseline")              # read a CSV with typed values, validated
```

## Extending the schema

- Add the field to the schema file with title, type, allowed range, unit and description.
- Raise the version.
- Update the tables in this README.
- Let the engine fill the field, or the risk model for the risk_score table. Their tests check generated records against the schema.
- The app picks up a new field of the baseline or outcome table by itself: it gets a filter and a chart.
