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
| Risk model candidate | Candidate 1, candidate 3 for G-CSF | Candidate 2, later others |
| Input | Baseline data | Weekly observations |
| Time of action | Before the first cycle | In the week of the alert |
| Typical action | Adapted dose or regimen, prophylaxis, closer monitoring | Contact, examination, pause of therapy, early treatment |
| Evidence that acting helps | Geriatric assessment with adapted management lowered severe toxicity from 71% to 51% ([Mohile et al., 2021](references.md#mohile-2021)) and from 61% to 51% in GAIN ([Dale et al., 2023](references.md#dale-2023)). G-CSF from the first cycle lowers neutropenic events strongly ([Lyman et al., 2011](references.md#lyman-2011)) | Weekly symptom reports with alerts improved function, symptom control and quality of life ([Basch et al., 2022](references.md#basch-2022)); the European guideline recommends them ([Di Maio et al., 2022](references.md#di-maio-2022)) |

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

Anchors:

- In PRO-TECT, 1066 of 1191 patients (89.5%) completed the three-month follow-up of the trial ([Basch et al., 2022](references.md#basch-2022)). This is retention in the study, not the completion of weekly reports.
- The European guideline states that little is known about how well patients keep reporting, older patients in particular. More than a third of the patients in one study preferred an automated telephone call to the web, more often older and less educated patients ([Di Maio et al., 2022](references.md#di-maio-2022)). Offering one mode only lowers participation in exactly the groups at higher risk.
- A risk assessment has to be done to have an effect: in surveys about one in five oncologists used a geriatric assessment routinely ([Dale et al., 2023](references.md#dale-2023)).
- Loss to follow-up was 0.4% and 1.9% within a year in the two arms of PRONOUNCE ([Lopes et al., 2021](references.md#lopes-2021)).

All values of this section are set as assumptions.

### 3.2 Detector and risk model

The simulation uses a stand-in for the risk model, with adjustable performance. Stand-in and risk model use the same interface, so that one can take the place of the other without changing the rest.

**Prediction at therapy start**

- The stand-in produces a risk score from the true risk of the patient plus noise. The amount of noise sets the discrimination (AUC).
- A threshold turns the score into "high risk" or "not high risk". It can be given as a risk value or as the share of patients to be flagged.
- Parameters: discrimination, threshold.

**Detection during therapy**

- The stand-in gives an alert in a week with a probability that depends on the stage of the toxicity: low shortly after onset, higher as it worsens.
- In weeks without a developing toxicity it gives a false alert with a small probability.
- Parameters: sensitivity per stage, false alert rate per patient-week.
- The lead time, meaning how much earlier than in usual care a toxicity is found, is not a parameter. It results from the sensitivity, the adherence and the natural course of the toxicity.

A first published rule for a detector exists for lung toxicity under trastuzumab deruxtecan: a fall of the oxygen saturation at rest by 2 to 4 points over 1 to 3 days should lead to an examination ([Swain et al., 2022](references.md#swain-2022)). It rests on expert opinion. Home measurements cannot see grade 1, which shows only in imaging.

**Perfect detector.** A stand-in that knows the truth gives the upper limit of what any risk model could achieve with the given actions. This is a useful reference in the analysis.

### 3.3 Natural course of a toxicity

To model early treatment, a toxicity must have a course that can be interrupted. Each event therefore runs through stages:

```
onset ─► mild ─► moderate ─► severe ─► life-threatening ─► fatal
        (grade 1) (grade 2)  (grade 3)     (grade 4)       (grade 5)
```

- Each episode has a ceiling, the grade it would reach if nobody acted, and a time it spends in each stage.
- Recognition stops the worsening. The grade at recognition is the grade of the event.
- In usual care, recognition comes from regular visits and from patients who seek help when symptoms are strong enough. With an intervention it can come earlier.
- Before a severe event there is a phase with milder signs. Detection in this phase can keep the event from becoming severe.

The stage times and ceilings are set so that the scenario "usual care" gives the published event rates and grade distributions, which are the calibration targets.

For lung toxicity the published delay supports this structure directly: onset was set earlier by the adjudication committee for 53% of events, with a median difference of 43 days ([Powell et al., 2022](references.md#powell-2022)); a second analysis found 48% and 49 days ([Swain et al., 2022](references.md#swain-2022)). The first severe toxicity of chemotherapy in older patients came after a median of 22 days ([Extermann et al., 2012](references.md#extermann-2012)), so the early phase of most events lies in the first cycle. For other event types the length of the early phase is an assumption. Cardiovascular events are a special case: only a part of them has a phase with warning signs, such as unstable angina, a transient ischaemic attack or rising blood pressure. The others come without notice, and no detection can prevent them. The engine assumes a warning phase for half of the events.

### 3.4 Actions

What the care team does after a flag or an alert. Each action has a probability that it is carried out and an effect.

**After a high-risk flag at therapy start**

| Action | Effect in the model | Already in the engine |
|---|---|---|
| Reduced starting dose or less intensive regimen | Lower hazard of all dose-dependent events | Dose level and its effect on the hazard |
| G-CSF prophylaxis | Lower hazard of neutropenia and febrile neutropenia | Yes, with the published effect |
| Thromboprophylaxis for patients with a Khorana score of 2 or more | Lower hazard of venous thromboembolism, about one percentage point more major bleeding ([Key et al., 2020](references.md#key-2020)) | Yes, with the published effect and bleeding risk |
| GnRH antagonist instead of an agonist for men with cardiovascular disease ([Tilki et al., 2024](references.md#tilki-2024)) | Lower hazard of cardiovascular events, by an uncertain amount | No |
| Supportive measures, for example nutrition, review of medication, physiotherapy | Lower general hazard, fewer falls | No |
| Closer monitoring | Earlier recognition of all events | No |

Anchors:

- In GAP70+, 48.7% of patients in the intervention group started with reduced intensity against 35.0% with usual care. Severe toxicity fell by a relative risk of 0.74, falls from 21% to 12%. Survival did not differ ([Mohile et al., 2021](references.md#mohile-2021)).
- In GAIN, toxicity of grade 3 or higher fell from 60.6% to 50.5%; hospital stays, dose changes and survival did not differ ([Dale et al., 2023](references.md#dale-2023)).
- The guideline names the actions: one drug instead of two, a dose reduced by 20% with escalation as tolerated, toxicity checks every one or two weeks ([Dale et al., 2023](references.md#dale-2023)). The engine's reduced dose level of 0.8 is this reduction.
- With G-CSF from the first cycle, 6.4% of the patients had a neutropenic event in that cycle against 22.8% without ([Lyman et al., 2011](references.md#lyman-2011)). Guidelines recommend it from a risk of febrile neutropenia of 20%.
- The assessment has to come before the treatment decision. A trial in which most patients were assessed after the start found no effect ([Dale et al., 2023](references.md#dale-2023)).

**After an alert during therapy**

| Action | Effect in the model |
|---|---|
| Contact by phone, advice for self-management | Mild events are contained without a visit |
| Examination and diagnostics | Confirms or rules out the toxicity; has a cost also for false alerts |
| Pause of therapy or dose reduction at an earlier stage | Stops the worsening; lower final grade |
| Early specific treatment, for example corticosteroids for lung toxicity or immune-related events, antibiotics for fever in neutropenia, fluids and electrolytes for diarrhoea | Lower final grade, shorter duration, less often a hospital stay |
| Resumption of therapy after a mild, well-managed event | Fewer permanent stops of therapy |

Anchors:

- In PRO-TECT, 33.9% of the weekly surveys triggered an alert, and 59.1% of the alerts led to an immediate action by a nurse, mostly a phone call ([Basch et al., 2022](references.md#basch-2022)).
- The European guideline describes the path of an alert: automated advice for mild symptoms, a nurse who assesses by phone, coaching in self-management, and escalation to a physician or an urgent visit when needed. Reports without a named person to act had no effect ([Di Maio et al., 2022](references.md#di-maio-2022)).
- The ASCO guideline ties the management of immune-related events to the grade: continue at grade 1, pause at grade 2, high-dose corticosteroids at grade 3, permanent stop at grade 4 ([Schneider et al., 2021](references.md#schneider-2021)).
- For lung toxicity under trastuzumab deruxtecan the rule is sharper: at grade 1 the drug is paused and can be resumed, from grade 2 it is stopped for good ([Swain et al., 2022](references.md#swain-2022)). The engine follows this rule.

An event caught at a lower grade therefore has a milder consequence for the therapy by rule.

### 3.5 Consequences

The comparison of interventions needs these consequences. Section 6 shows how the engine implements them.

| Consequence | Depends on | In the engine |
|---|---|---|
| Unplanned visit | Event type, grade at recognition | Yes |
| Hospital stay and its length | Event type, grade at recognition, frailty | Yes |
| Intensive care | Grade 4 and 5 | Yes |
| Duration of the event | Grade at recognition, treatment | Yes |
| Pause, dose reduction, stop of therapy | Grade at recognition | Yes |
| Death from toxicity | Grade | Yes |
| Dose received relative to the planned dose | Dose reductions, pauses, stops | Can be derived |
| Tumour control and survival | Time on therapy and dose received | Parameter exists, switched off, see 3.7 |
| Quality of life | Health state, events and their duration | Yes, with published utilities |

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

- Each week gets a quality-of-life weight between 0 and 1. It depends on the health state and on frailty and is lowered during events.
- Summed over the follow-up this gives quality-adjusted life years.
- Costs and quality-adjusted life years together give the cost per quality-adjusted life year gained against usual care.

Anchors:

- Utilities for metastatic breast cancer from the general public: 0.715 for stable disease on treatment, 0.272 less with progressive disease, 0.150 less with febrile neutropenia, 0.103 less with severe diarrhoea and vomiting, 0.115 less with severe fatigue ([Lloyd et al., 2006](references.md#lloyd-2006)). The engine uses them for all three tumours and counts a patient as progressive after the end of the therapy line. Staying on therapy longer therefore has a value of its own.
- A symptom monitoring system cost 200 euros per patient and month, software and staff time included, and a consultation was reimbursed with 28 euros on average in the French health insurance ([Lizée et al., 2019](references.md#lizee-2019)). The same analysis called 30 000 euros per quality-adjusted life year very cost-effective and 90 000 euros cost-effective.

The references contain no unit costs for hospital stays, intensive care, diagnostics and the treatment of toxicity. These values are placeholders and need a separate literature search and a decision on the cost perspective.

### 3.7 Unwanted effects of the intervention

An honest model includes the ways in which an intervention can do harm.

- **False alerts.** They cause contacts, diagnostics and sometimes an unnecessary pause of therapy.
- **Alert fatigue.** The more alerts per nurse, the lower the share that leads to action. The guideline asks for protected time for the nurses who handle alerts ([Di Maio et al., 2022](references.md#di-maio-2022)). The engine models a simple form: every earlier false alert of a patient lowers the probability that the team acts on the next one.
- **Harm from preventive drugs.** Thromboprophylaxis raises major bleeding by one to two percentage points ([Key et al., 2020](references.md#key-2020)). The engine generates this excess, and a bleeding can be fatal.
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

### 4.2 Scenarios

| Scenario | Content | Purpose |
|---|---|---|
| Usual care | No intervention | Reference |
| Risk-adapted start | Prediction at therapy start by a stand-in with adjustable accuracy; adapted dose, prophylaxis and supportive measures for flagged patients | What a predictor of a given accuracy achieves |
| Model-guided start | The same actions, but the risk models decide: candidate 1 flags, candidate 3 decides on G-CSF | What the risk models achieve |
| Symptom monitoring | Weekly reports with alerts for all event types | The intervention of PRO-TECT |
| Lung monitoring | Oxygen saturation and symptoms at home for patients on trastuzumab deruxtecan, with a detection model | Candidate 2 |
| Cardiovascular monitoring | Blood pressure and chest symptoms at home for men under androgen deprivation, with a detection model | Candidate 5 |
| Combined | Risk-adapted start and the three kinds of monitoring | Joint effect |
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

### 4.4 Time-to-event endpoints

Every endpoint counts from the start of therapy. Each patient is followed until death or the end of the simulated period; a patient without the event is censored at that end.

| Endpoint | Event | Estimate | Measures |
|---|---|---|---|
| Overall survival | Death from any cause | Kaplan-Meier | Restricted mean survival within 5 years, alive at 1 year, median survival |
| Survival without severe toxicity | First adverse event of grade 3 to 5, or death | Kaplan-Meier | Restricted mean within 1 year, alive without severe event at 1 year |
| First severe adverse event | First adverse event of grade 3 to 5; death competes | Cumulative incidence (Aalen-Johansen) | Share at 90 days and at 1 year |
| Time on therapy | End of the therapy line for any reason | Kaplan-Meier | Median |
| End of therapy for toxicity | End of therapy for toxicity; the other reasons compete | Cumulative incidence | Share at 1 year; all reasons of the selected scenario in one chart |
| Lung toxicity | Lung toxicity of grade 2 or higher, by its day of onset; death competes. Patients on trastuzumab deruxtecan | Cumulative incidence | Share at 1 year |
| Major cardiovascular event | Myocardial infarction, stroke or cardiovascular death; death from other causes competes. Men under androgen deprivation | Cumulative incidence | Share at 1 year |

Events that death can prevent get a cumulative incidence, not 1 − Kaplan-Meier: Kaplan-Meier would count the patients who died as if they could still have the event and overestimate it.

The scenarios hold the same patients with the same random draws. They are therefore compared pair by pair, not with tests for independent groups such as the log-rank test. Because the status of every patient is known up to the end of the simulated period, a restricted mean or a share at a time is the mean of a per-patient value; the difference between two scenarios is the mean of the per-patient differences, with a 95% confidence interval from their spread. In a simulation the interval says how precisely the cohort shows the difference, not whether an effect is real.

The endpoints on toxicity and therapy are intermediate endpoints, not validated surrogates for survival. In the model their link to survival is explicit: deaths from toxicity end survival directly, and the dose received changes the time to progression through a parameter that is switched off by default (section 3.7). An intervention therefore changes survival by days, while it changes survival without severe toxicity and the end of therapy for toxicity clearly.

## 5. Parameters

| Group | Parameter | Anchor in our references |
|---|---|---|
| Participation | Uptake, by age and frailty | none; older and less educated patients prefer the telephone ([Di Maio et al., 2022](references.md#di-maio-2022)) |
| | Weekly completion of reports | none; PRO-TECT gives only study retention (89.5% at three months) |
| | Dropout from the intervention per week | none |
| | Attendance after an alert | none |
| | Loss to follow-up per week | PRONOUNCE: 0.4% and 1.9% within a year ([Lopes et al., 2021](references.md#lopes-2021)) |
| Prediction | Discrimination of the risk score | c-statistic 0.64 for any severe toxicity ([Extermann et al., 2012](references.md#extermann-2012)), 0.81 for neutropenia in the first cycle ([Lyman et al., 2011](references.md#lyman-2011)) |
| | Threshold or share flagged | none |
| Detection | Sensitivity per stage | none; a first rule for oxygen saturation in [Swain et al. (2022)](references.md#swain-2022) |
| | False alerts per patient-week | PRO-TECT: alerts in 33.9% of surveys under fixed thresholds |
| Natural course | Time per stage, ceiling grade | Lung toxicity: recognition delay in [Powell et al. (2022)](references.md#powell-2022), grades in [Modi et al. (2022)](references.md#modi-2022). Early events: median day 22 in [Extermann et al. (2012)](references.md#extermann-2012). Cardiovascular events: share and length of the warning phase are assumptions |
| Actions at start | Share of flagged patients with reduced dose | GAP70+: 48.7% against 35.0% |
| | Effect of supportive measures on the hazard | GAP70+: relative risk 0.74 for the whole bundle; GAIN: 50.5% against 60.6% |
| | Effect of G-CSF | [Lyman et al. (2011)](references.md#lyman-2011): 6.4% against 22.8% in the first cycle |
| Actions after alert | Share of alerts with action | PRO-TECT: 59.1% |
| | Effect of early treatment on the final grade | none |
| | Therapy consequence by grade | [Schneider et al. (2021)](references.md#schneider-2021) for immune-related events; [Swain et al. (2022)](references.md#swain-2022) for lung toxicity |
| Consequences | Hospital stay by type and grade, length of stay | about five days for febrile neutropenia in the health state of [Lloyd et al. (2006)](references.md#lloyd-2006) |
| | Effect of dose received on progression | GAP70+: no difference in survival |
| Value | Quality-of-life weights | [Lloyd et al. (2006)](references.md#lloyd-2006) |
| | Unit costs | [Lizée et al. (2019)](references.md#lizee-2019) for monitoring and consultations; none for the others |

The risk-adapted start can be checked against GAP70+ as a whole: with parameters in a plausible range, the scenario should lower severe toxicity in older patients with impairments by about a quarter.

## 6. Implementation

The engine implements the model with the parameters in `engine/config/interventions.json`. The app shows the scenarios side by side and the course of single patients under two scenarios.

| Component | Status in the engine |
|---|---|
| Participation: uptake, adherence, dropout, attendance, loss to follow-up | Implemented. Uptake and adherence depend on frailty and age. |
| Prediction at therapy start | Two predictors: a stand-in (true patient-related risk plus noise) and the risk models (candidate 1 for the flag, candidate 3 for G-CSF). A fixed share of the cohort is flagged. |
| Detection during therapy | Lung monitoring: the detection model of the risk models reads the generated oxygen saturation and symptoms. Symptom and cardiovascular monitoring: stand-ins with a sensitivity per stage, the share of events that show in symptoms, and false alerts per report. |
| Perfect detector | Implemented as scenario. |
| Natural course in stages | Implemented. Usual care recognises an event at a fixed day and grade; monitoring can recognise it at an earlier stage. |
| Actions at therapy start | Reduced starting dose, G-CSF, thromboprophylaxis, supportive measures, closer monitoring. |
| Actions after an alert | Recognition on the next day, early treatment that stops the worsening with a given probability, milder change of therapy at lower grade. |
| Consequences | Unplanned visits, hospital days, intensive care days, duration of events, death from toxicity. |
| Costs and quality-adjusted life years | Implemented. Utilities and the costs of symptom reports and visits come from the literature, the other unit costs are placeholders. |
| False alerts | Counted, with their costs. They do not change the therapy. |
| Alert fatigue | Implemented per patient: earlier false alerts lower the probability of action. The workload of the team is not modelled. |
| Link from dose received to tumour control | Parameter exists, switched off. |
| Same patients, same chance | Implemented with fixed random numbers per patient, purpose and week. |
| Scenarios | The eight scenarios of section 4.2. |

The check against GAP70+ holds: flagged patients who take part in the risk-adapted start have severe toxicity within 90 days in 55% against 74% in usual care, a relative risk of 0.74. In the model-guided start, where the risk models choose the patients, it is 69% against 86%, a relative risk of 0.80.

Open parts:

- Values from the literature for participation, the effect of early treatment, hospital stays and the remaining unit costs; quality-of-life weights for pancreatic and prostate cancer.
- The choice of a GnRH antagonist as an action at therapy start.
- Detection models for symptom monitoring and cardiovascular monitoring in place of their stand-ins.
- A link from time on therapy to survival, without which an intervention changes survival only through deaths from toxicity.

## 7. Ideas for later

- Thresholds that adapt to the workload of the care team, and alert fatigue that follows the number of alerts per nurse.
- Automated advice for mild symptoms, which takes alerts off the nurses.
- More than one way to report, with different participation by age.
- Different detectors per event type with their own performance.
- Learning effects: the performance of the risk model improves with the data collected.
- Interventions for the care team rather than the patient, for example decision support at the tumour board.
- Costs from different perspectives: health insurance, hospital, society.
- Longer follow-up with later therapy lines, so that effects on survival can show.
- Ranges for the assumed parameters of participation, detection and early treatment, so that the uncertainty analysis of the engine covers the whole chain of effects.
