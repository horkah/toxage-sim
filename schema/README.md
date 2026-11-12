# schema

The central data schema of the project. The engine, the risk model and the app all read field names, titles, types and allowed values from here.

## Tables

| Table | File | Content | Records |
|---|---|---|---|
| scenario | [scenario.schema.json](scenario.schema.json) | One intervention scenario | one per scenario |
| baseline | [baseline.schema.json](baseline.schema.json) | One patient at the start of a systemic therapy line | one per patient, shared by all scenarios |
| observation | [observation.schema.json](observation.schema.json) | Therapy status, measurements and patient-reported symptoms in one week | one per scenario, patient and week |
| event | [event.schema.json](event.schema.json) | One adverse event | none, one or several per scenario and patient |
| alert | [alert.schema.json](alert.schema.json) | One alert of a monitoring component | none, one or several per scenario and patient |
| outcome | [outcome.schema.json](outcome.schema.json) | Summary of the course of the patient | one per scenario and patient |
| risk_score | [risk_score.schema.json](risk_score.schema.json) | Risk scores at therapy start, computed by the [risk model](../risk-model/) | one per patient |

Tables are linked by `patient_id` and, where a table depends on the scenario, by `scenario_id`. The reference scenario without intervention is `usual_care`. Days count from therapy start, which is day 1. Week 0 covers days 1 to 7.

All scenarios are simulated for the same patients. Comparing the records of one patient across scenarios shows what an intervention changed for this patient.

The schema files hold the full description and unit of every field. The tables below give an overview.

### scenario

| Field | Title | Type | Values |
|---|---|---|---|
| `scenario_id` | Scenario | string |  |
| `title` | Title | string |  |
| `description` | Description | string |  |
| `risk_adapted_start` | Risk-adapted start | boolean |  |
| `symptom_monitoring` | Symptom monitoring | boolean |  |
| `lung_monitoring` | Lung monitoring | boolean |  |

### baseline

| Field | Title | Type | Values |
|---|---|---|---|
| `patient_id` | Patient ID | string |  |
| `tumour_type` | Tumour type | string | `pancreas`, `prostate`, `breast` |
| `subgroup` | Subgroup | string | `pancreas_metastatic`, `prostate_hormone_sensitive`, `prostate_castration_resistant`, `breast_her2_low`, `breast_triple_negative` |
| `regimen` | Regimen | string | 10 values, see the schema file |
| `prior_therapy_lines` | Earlier therapy lines | integer | 0 or more |
| `starting_dose_level` | Starting dose level | number | 0.1–1.0 |
| `gcsf_prophylaxis` | G-CSF prophylaxis | boolean |  |
| `age_years` | Age | integer | 18–100 |
| `sex` | Sex | string | `female`, `male` |
| `ecog` | ECOG | integer | 0–4 |
| `ga_impaired_domains` | Impaired geriatric domains | integer or null | 0–7 |
| `bmi` | Body mass index | number | 10–60 |
| `albumin_g_l` | Albumin | number | 10–60 |
| `egfr_ml_min` | eGFR | integer | 5–150 |
| `renal_function` | Renal function | string | `normal`, `mild_decrease`, `moderate_severe_decrease` |
| `bilirubin_ratio_uln` | Bilirubin | number | 0 or more |
| `neutrophils_10e9_l` | Neutrophils | number | 0 or more |
| `haemoglobin_g_dl` | Haemoglobin | number | 0 or more |
| `platelets_10e9_l` | Platelets | integer | 0 or more |
| `spo2_percent` | Oxygen saturation | integer | 70–100 |
| `lung_comorbidity` | Lung comorbidity | boolean |  |
| `diabetes` | Diabetes | boolean |  |
| `cardiovascular_disease` | Cardiovascular disease | boolean |  |
| `years_since_diagnosis` | Years since diagnosis | number | 0 or more |

The baseline record describes the plan in usual care. A scenario can adapt the starting dose and the G-CSF prophylaxis of a patient; the observation records show the dose that was given.

### observation

| Field | Title | Type | Values |
|---|---|---|---|
| `scenario_id` | Scenario | string |  |
| `patient_id` | Patient ID | string |  |
| `week` | Week | integer | 0 or more |
| `day` | Day | integer | 1 or more |
| `treatment_status` | Therapy status | string | `on_treatment`, `interrupted`, `stopped` |
| `dose_level` | Dose level | number or null | 0.1–1.0 |
| `neutrophils_10e9_l` | Neutrophils | number or null | 0 or more |
| `haemoglobin_g_dl` | Haemoglobin | number or null | 0 or more |
| `platelets_10e9_l` | Platelets | integer or null | 0 or more |
| `spo2_percent` | Oxygen saturation | integer or null | 50–100 |
| `pro_fatigue` | Fatigue | integer or null | 0–4 |
| `pro_diarrhoea` | Diarrhoea | integer or null | 0–4 |
| `pro_cough` | Cough | integer or null | 0–4 |
| `pro_dyspnoea` | Shortness of breath | integer or null | 0–4 |

Observations are written from therapy start until a few weeks after the end of therapy, or until death.

### event

| Field | Title | Type | Values |
|---|---|---|---|
| `scenario_id` | Scenario | string |  |
| `patient_id` | Patient ID | string |  |
| `event_type` | Event type | string | 10 values, see the schema file |
| `grade` | Grade | integer | 1–5 |
| `onset_day` | Day of onset | integer | 1 or more |
| `day` | Day of recognition | integer | 1 or more |
| `detected_by` | Recognised through | string | `routine`, `monitoring` |
| `usual_care_day` | Day of recognition in usual care | integer | 1 or more |
| `usual_care_grade` | Grade in usual care | integer | 1–5 |
| `action` | Action | string | `none`, `interruption`, `dose_reduction`, `discontinuation` |
| `hospital_days` | Hospital days | integer | 0 or more |
| `icu_days` | Intensive care days | integer | 0 or more |
| `unplanned_visit` | Unplanned visit | boolean |  |

`onset_day` is the day the event actually started, `day` the day it was recognised. `usual_care_day` and `usual_care_grade` say when and at which grade the event would have been recognised without monitoring. For an event recognised through monitoring, the difference shows what the early recognition gained.

### alert

| Field | Title | Type | Values |
|---|---|---|---|
| `scenario_id` | Scenario | string |  |
| `patient_id` | Patient ID | string |  |
| `day` | Day | integer | 1 or more |
| `source` | Source | string | `symptom_report`, `lung_monitoring` |
| `true_alert` | True alert | boolean |  |
| `event_type` | Event type | string or null |  |
| `attended` | Attended | boolean |  |
| `acted` | Acted on | boolean |  |

### outcome

| Field | Title | Type | Values |
|---|---|---|---|
| `scenario_id` | Scenario | string |  |
| `patient_id` | Patient ID | string |  |
| `follow_up_days` | Follow-up | integer | 1 or more |
| `high_risk_flag` | Flagged as high risk | boolean |  |
| `participating` | Taking part | boolean |  |
| `severe_toxicity_90d` | Severe toxicity in 90 days | boolean |  |
| `severe_toxicity_day` | Day of severe toxicity | integer or null | 1–90 |
| `ild` | Lung toxicity | boolean |  |
| `ild_onset_day` | Day of lung toxicity | integer or null | 1 or more |
| `ild_diagnosis_day` | Day lung toxicity was recognised | integer or null | 1 or more |
| `ild_grade` | Grade of lung toxicity | integer or null | 1–5 |
| `treatment_end_day` | Day of therapy end | integer or null | 1 or more |
| `treatment_end_reason` | Reason for therapy end | string | `ongoing`, `progression`, `toxicity`, `completed`, `lost_to_follow_up`, `death` |
| `death_day` | Day of death | integer or null | 1 or more |
| `death_from_toxicity` | Death from toxicity | boolean |  |
| `hospital_days` | Hospital days | integer | 0 or more |
| `icu_days` | Intensive care days | integer | 0 or more |
| `unplanned_visits` | Unplanned visits | integer | 0 or more |
| `alerts` | Alerts | integer | 0 or more |
| `false_alerts` | False alerts | integer | 0 or more |
| `cost_care` | Cost of care | number | 0 or more |
| `cost_intervention` | Cost of the intervention | number | 0 or more |
| `qaly` | Quality-adjusted life years | number | 0 or more |

The outcome table is derived from the event, alert and observation tables. It holds the targets of the risk models and the measures for comparing scenarios.

### risk_score

| Field | Title | Type | Values |
|---|---|---|---|
| `patient_id` | Patient ID | string |  |
| `model_version` | Model version | string |  |
| `severe_toxicity_90d_risk` | Risk of severe toxicity in 90 days | number | 0–1 |
| `severe_toxicity_90d_regimen_rate` | Regimen rate of severe toxicity | number | 0–1 |
| `severe_toxicity_90d_category` | Risk category, severe toxicity | string | `low`, `intermediate`, `high` |
| `ild_applicable` | Lung toxicity model applies | boolean |  |
| `ild_risk` | Risk of lung toxicity | number or null | 0–1 |
| `ild_grade2plus_risk` | Risk of lung toxicity, grade 2 or higher | number or null | 0–1 |
| `ild_regimen_rate` | Regimen rate of lung toxicity | number or null | 0–1 |
| `ild_category` | Risk category, lung toxicity | string or null | `low`, `intermediate`, `high` |

Risks are probabilities. The `ild_` fields are null if the lung toxicity model does not apply to the regimen. The risk_score table is written by the risk model, all other tables by the engine.

## Format

The schema files are JSON Schema (draft 2020-12), so any language can read them. All fields are flat, so a table can be stored as CSV with the field names as header. In CSV, null is an empty cell and booleans are `true` and `false`.

Each schema file carries a `version`, currently 0.3.0 for the six tables of the engine and 0.1.1 for risk_score. Adding an optional field raises the minor version. Renaming or removing a field, or changing its meaning, raises the major version. Changes that leave the data as they are, such as a new `title`, raise the patch version.

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
