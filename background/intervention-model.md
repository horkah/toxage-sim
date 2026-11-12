# Intervention model: concept

This document describes how interventions and their effects are modelled in the microsimulation. Section 6 says which parts the [engine](../engine/) implements and where it is simpler than the concept.

The main intervention of the project is the early detection or prediction of therapy toxicity. Detection alone changes nothing. What changes the course of a patient is what the care team does with the information, and whether the patient takes part. The model therefore describes the whole chain from the offer of the intervention to its effect on health and costs.

Statements with a source refer to [references.md](references.md). Everything else is a design proposal of this project.

## 1. Chain of effects

```
offer ─► participation ─► adherence ─► signal ─► alert ─► contact ─► action ─► effect
          (uptake)        (reports,    (true     (detector  (patient   (care     (health,
                           devices,    course)   or risk    reached,   team      resources,
                           dropout)              model)     shows up)  acts)     costs)
```

Every arrow is a step where the intervention can fail. Each step gets its own parameters. The effect of the intervention in a cohort is the product of all steps, not the performance of the risk model alone.

## 2. Two kinds of intervention

| | Prediction at therapy start | Detection during therapy |
|---|---|---|
| Question | Who will probably have severe toxicity? | Who is developing a toxicity right now? |
| Risk model candidate | Candidate 1 | Candidate 2, later others |
| Input | Baseline data | Weekly observations |
| Time of action | Before the first cycle | In the week of the alert |
| Typical action | Adapted dose or regimen, prophylaxis, closer monitoring | Contact, examination, pause of therapy, early treatment |
| Evidence that acting helps | Geriatric assessment with adapted management lowered severe toxicity from 71% to 51% (Mohile et al., 2021) | Weekly symptom reports with alerts improved function, symptom control and quality of life (Basch et al., 2022) |

## 3. Model components

### 3.1 Participation and adherence

| Component | Meaning | Parameters |
|---|---|---|
| Eligibility | Which patients are offered the intervention | Rules on tumour, regimen, age |
| Uptake | Share of eligible patients who agree | Probability, lower with higher age and frailty |
| Adherence | Share of weeks in which a participating patient delivers reports and measurements | Completion rate per week, lower with frailty and in weeks with severe symptoms |
| Dropout from the intervention | Patient stops reporting for good but stays in care | Weekly dropout hazard, higher in the first weeks |
| Attendance after an alert | Patient can be reached and comes to the visit that the alert calls for | Probability per alert |
| Loss to follow-up | Patient no longer shows up at all, also not for regular visits | Weekly hazard; applies to usual care as well |

Two points matter for realism:

- **Selective participation.** Patients who take part and stay adherent are on average fitter than those who do not. If the model ignores this, it overstates the benefit, because the patients with the highest risk are the ones the intervention reaches least. Uptake and adherence therefore depend on the latent frailty.
- **Loss to follow-up exists without the intervention.** A patient who stays away after a diagnosis has a later recognition of every further toxicity and no adapted therapy. This belongs to usual care and to every other scenario.

Anchor: in PRO-TECT, 1066 of 1191 patients (89.5%) completed the three-month follow-up of the trial (Basch et al., 2022). This is retention in the study, not the completion of weekly reports. All values of this section have to be set as assumptions or taken from further literature.

### 3.2 Detector and risk model

The real risk model will be added later. Until then the simulation needs a stand-in with adjustable performance. Both use the same interface, so that the stand-in can be replaced without changing the rest.

**Prediction at therapy start**

- The stand-in produces a risk score from the true risk of the patient plus noise. The amount of noise sets the discrimination (AUC).
- A threshold turns the score into "high risk" or "not high risk". It can be given as a risk value or as the share of patients to be flagged.
- Parameters: discrimination, threshold.

**Detection during therapy**

- The stand-in gives an alert in a week with a probability that depends on the stage of the toxicity: low shortly after onset, higher as it worsens.
- In weeks without a developing toxicity it gives a false alert with a small probability.
- Parameters: sensitivity per stage, false alert rate per patient-week.
- The lead time, meaning how much earlier than in usual care a toxicity is found, is not a parameter. It results from the sensitivity, the adherence and the natural course of the toxicity.

**Perfect detector.** A stand-in that knows the truth gives the upper limit of what any risk model could achieve with the given actions. This is a useful reference in the analysis.

### 3.3 Natural course of a toxicity

To model early treatment, a toxicity must have a course that can be interrupted. Today the engine draws the final grade of an event at once. The concept replaces this with stages:

```
onset ─► mild ─► moderate ─► severe ─► life-threatening ─► fatal
        (grade 1) (grade 2)  (grade 3)     (grade 4)       (grade 5)
```

- Each episode has a ceiling, the grade it would reach if nobody acted, and a time it spends in each stage.
- Recognition stops the worsening. The grade at recognition is the grade of the event.
- In usual care, recognition comes from regular visits and from patients who seek help when symptoms are strong enough. With an intervention it can come earlier.
- Before a severe event there is a phase with milder signs. Detection in this phase can keep the event from becoming severe.

The stage times and ceilings are set so that the scenario "usual care" gives the same event rates and grade distributions as the engine gives today. The published values stay the calibration targets.

For lung toxicity the published delay supports this structure directly: onset was set earlier by the adjudication committee for 53% of events, with a median difference of 43 days (Powell et al., 2022). For other event types the length of the early phase is an assumption.

### 3.4 Actions

What the care team does after a flag or an alert. Each action has a probability that it is carried out and an effect.

**After a high-risk flag at therapy start**

| Action | Effect in the model | Already in the engine |
|---|---|---|
| Reduced starting dose or less intensive regimen | Lower hazard of all dose-dependent events | Dose level and its effect on the hazard |
| G-CSF prophylaxis | Lower hazard of neutropenia and febrile neutropenia | Yes |
| Supportive measures, for example nutrition, review of medication, physiotherapy | Lower general hazard, fewer falls | No |
| Closer monitoring | Earlier recognition of all events | No |

Anchor: in GAP70+, 48.7% of patients in the intervention group started with reduced intensity against 35.0% with usual care. Severe toxicity fell by a relative risk of 0.74. Survival did not differ (Mohile et al., 2021).

**After an alert during therapy**

| Action | Effect in the model |
|---|---|
| Contact by phone, advice for self-management | Mild events are contained without a visit |
| Examination and diagnostics | Confirms or rules out the toxicity; has a cost also for false alerts |
| Pause of therapy or dose reduction at an earlier stage | Stops the worsening; lower final grade |
| Early specific treatment, for example corticosteroids for lung toxicity or immune-related events, antibiotics for fever in neutropenia, fluids and electrolytes for diarrhoea | Lower final grade, shorter duration, less often a hospital stay |
| Resumption of therapy after a mild, well-managed event | Fewer permanent stops of therapy |

Anchors: in PRO-TECT, 33.9% of the weekly surveys triggered an alert, and 59.1% of the alerts led to an immediate action by a nurse, mostly a phone call (Basch et al., 2022). The ASCO guideline ties the management of immune-related events to the grade: continue at grade 1, pause at grade 2, high-dose corticosteroids at grade 3, permanent stop at grade 4 (Schneider et al., 2021). An event caught at a lower grade therefore has a milder consequence for the therapy by rule.

### 3.5 Consequences

The engine today counts events, dose changes, stops of therapy and deaths. The comparison of interventions needs further consequences.

| Consequence | Depends on | New in the engine |
|---|---|---|
| Unplanned visit | Event type, grade at recognition | Yes |
| Hospital stay and its length | Event type, grade at recognition, frailty | Yes |
| Intensive care | Grade 4 and 5 | Yes |
| Duration of the event | Grade at recognition, treatment | Yes |
| Pause, dose reduction, stop of therapy | Grade at recognition | Exists, becomes grade-dependent |
| Death from toxicity | Grade | Exists |
| Dose received relative to the planned dose | Dose reductions, pauses, stops | Can be derived |
| Tumour control and survival | Time on therapy and dose received | Optional link, see 3.7 |
| Quality of life | Health state, events and their duration | Yes |

### 3.6 Costs and health value

**Costs of care**

| Item | Unit |
|---|---|
| Unplanned outpatient visit | per visit |
| Emergency visit | per visit |
| Hospital stay | per day, by ward |
| Diagnostics for a suspected toxicity, for example CT of the chest | per examination |
| Treatment of the toxicity | per episode, by grade |
| Cancer therapy | per week on therapy |

**Costs of the intervention**

| Item | Unit |
|---|---|
| Set-up, training, devices | per participating patient |
| Running the monitoring | per patient-week |
| Handling an alert | per alert, true or false |
| Baseline assessment for the risk model, for example geriatric assessment | per patient |

**Health value**

- Each week gets a quality-of-life weight between 0 and 1. It depends on tumour and frailty and is lowered during events, more for higher grades.
- Summed over the follow-up this gives quality-adjusted life years.
- Costs and quality-adjusted life years together give the cost per quality-adjusted life year gained against usual care.

Our references contain no unit costs and no quality-of-life weights. These values need a separate literature search and a decision on the cost perspective.

### 3.7 Unwanted effects of the intervention

An honest model includes the ways in which an intervention can do harm.

- **False alerts.** They cause contacts, diagnostics and sometimes an unnecessary pause of therapy.
- **Alert fatigue.** The more alerts per nurse, the lower the share that leads to action.
- **Undertreatment of the tumour.** Dose reductions and pauses for flagged patients can lower the effect of the cancer therapy. The model has an optional link from dose received to the hazard of progression. The default is no effect, in line with GAP70+, where survival did not differ. The link can be switched on to test how sensitive the result is.
- **Burden for the patient.** Weekly reporting takes effort. This shows in dropout from the intervention.

## 4. Parallel universes

A scenario is one complete set of intervention parameters. Each scenario is simulated for the same cohort. The results can then be compared patient by patient.

### 4.1 Same patients, same chance

For a fair comparison, the scenarios must differ only through the intervention.

- All scenarios use the same patients with the same baseline data and the same latent frailty.
- Each patient has fixed random numbers for each purpose: for the start of events per week and type, for the natural course of each episode, for measurement noise, for participation. A scenario changes probabilities, not the random numbers.
- A lower hazard then removes some of the events of the reference scenario and adds none by chance. A patient without any contact with the intervention has exactly the same course in all scenarios.

This makes statements on the level of single patients possible, for example: "In this patient, the lung toxicity was recognised 34 days earlier and stayed at grade 1 instead of grade 3."

### 4.2 First set of scenarios

| Scenario | Content | Purpose |
|---|---|---|
| Usual care | No intervention | Reference; equals the engine of today |
| Risk-adapted start | Prediction at therapy start, adapted dose, prophylaxis and supportive measures for flagged patients | Candidate 1 |
| Symptom monitoring | Weekly reports with alerts for all event types | The intervention of PRO-TECT |
| Lung monitoring | Oxygen saturation and symptoms at home for patients on trastuzumab deruxtecan, with a detection model | Candidate 2 |
| Combined | All three | Joint effect |
| Perfect detection | As combined, with full participation and a detector that knows the truth | Upper limit |

Further scenarios come from varying single parameters, for example uptake, sensitivity or false alert rate. This shows which step of the chain limits the benefit.

### 4.3 What to compare

| Area | Measures |
|---|---|
| Reach | Share offered, taking part, still reporting after 3 and 6 months |
| Detector | Alerts per patient, share of true alerts, share of toxicities found early, lead time |
| Toxicity | Events by type and grade, severe toxicity within 90 days, deaths from toxicity |
| Therapy | Dose reductions, pauses, stops for toxicity, dose received, time on therapy |
| Resources | Unplanned visits, hospital days, intensive care days |
| Outcome | Survival, quality-adjusted life years |
| Economics | Costs of care, costs of the intervention, cost per quality-adjusted life year gained |
| Efficiency | Patients to monitor to avoid one severe event, alerts to handle per avoided event |
| Fairness | All measures by tumour, subgroup, age and frailty |

## 5. Parameters

| Group | Parameter | Anchor in our references |
|---|---|---|
| Participation | Uptake, by age and frailty | none |
| | Weekly completion of reports | none; PRO-TECT gives only study retention (89.5% at three months) |
| | Dropout from the intervention per week | none |
| | Attendance after an alert | none |
| | Loss to follow-up per week | none |
| Prediction | Discrimination of the risk score | none; later from the real risk model |
| | Threshold or share flagged | none |
| Detection | Sensitivity per stage | none; later from the real risk model |
| | False alerts per patient-week | PRO-TECT: alerts in 33.9% of surveys under fixed thresholds |
| Natural course | Time per stage, ceiling grade | Lung toxicity: recognition delay in Powell et al. (2022), grades in Modi et al. (2022) |
| Actions at start | Share of flagged patients with reduced dose | GAP70+: 48.7% against 35.0% |
| | Effect of supportive measures on the hazard | GAP70+: relative risk 0.74 for the whole bundle |
| Actions after alert | Share of alerts with action | PRO-TECT: 59.1% |
| | Effect of early treatment on the final grade | none |
| | Therapy consequence by grade | Schneider et al. (2021) for immune-related events |
| Consequences | Hospital stay by type and grade, length of stay | none |
| | Effect of dose received on progression | GAP70+: no difference in survival |
| Value | Unit costs, quality-of-life weights | none |

The risk-adapted start can be checked against GAP70+ as a whole: with parameters in a plausible range, the scenario should lower severe toxicity in older patients with impairments by about a quarter.

## 6. Implementation

The engine implements the model with the parameters in `engine/config/interventions.json`. The app shows the scenarios side by side and the course of single patients under two scenarios.

| Component | Status in the engine |
|---|---|
| Participation: uptake, adherence, dropout, attendance, loss to follow-up | Implemented. Uptake and adherence depend on frailty and age. |
| Prediction at therapy start | Stand-in: true patient-related risk plus noise. A fixed share of the cohort is flagged. |
| Detection during therapy | Stand-in: sensitivity per stage, share of events that show in symptoms, false alerts per report. It does not read the generated measurements. |
| Perfect detector | Implemented as scenario. |
| Natural course in stages | Implemented. Usual care recognises an event at a fixed day and grade; monitoring can recognise it at an earlier stage. |
| Actions at therapy start | Reduced starting dose, G-CSF, supportive measures, closer monitoring. |
| Actions after an alert | Recognition on the next day, early treatment that stops the worsening with a given probability, milder change of therapy at lower grade. |
| Consequences | Unplanned visits, hospital days, intensive care days, duration of events, death from toxicity. |
| Costs and quality-adjusted life years | Implemented with placeholder values. |
| False alerts | Counted, with their costs. They do not change the therapy. |
| Alert fatigue | Not implemented. |
| Link from dose received to tumour control | Parameter exists, switched off. |
| Same patients, same chance | Implemented with fixed random numbers per patient, purpose and week. |
| Scenarios | The six scenarios of section 4.2. |

The check against GAP70+ holds: flagged patients who take part in the risk-adapted start have severe toxicity within 90 days in 55% against 72% in usual care, a relative risk of 0.76.

Open parts:

- Values from the literature for participation, the effect of early treatment, hospital stays, unit costs and quality-of-life weights.
- Real risk models in place of the stand-ins.
- A link from time on therapy to survival, without which an intervention changes survival only through deaths from toxicity.

## 7. Ideas for later

- Thresholds that adapt to the workload of the care team.
- Different detectors per event type with their own performance.
- Learning effects: the performance of the risk model improves with the data collected.
- Interventions for the care team rather than the patient, for example decision support at the tumour board.
- Costs from different perspectives: health insurance, hospital, society.
- Longer follow-up with later therapy lines, so that effects on survival can show.
- Uncertainty of the parameters: repeated simulation with parameters drawn from ranges.
