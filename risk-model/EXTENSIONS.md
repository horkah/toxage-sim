# Possible extensions

Open ideas for the risk models of candidates 1 to 5. Each item says what it needs: a change in the [schema](../schema/), the [engine](../engine/), the literature in [background/](../background/), or only the risk model. Items leave this list when they are done.

## Candidate 1: any severe toxicity in 90 days

| # | Extension | Needs |
|---|---|---|
| 1.1 | Replace the assumed odds ratios for age, ECOG and geriatric domains by published estimates. The CARG score ([Hurria et al., 2011](../background/references.md#hurria-2011); [Hurria et al., 2016](../background/references.md#hurria-2016)) is a candidate; only its abstracts have been read. | literature |
| 1.2 | Two sub-models for haematological and non-haematological toxicity, as in the CRASH score, whose split score discriminated better than the combined one ([Extermann et al., 2012](../background/references.md#extermann-2012)). The event table holds the types. | risk model |
| 1.3 | The predictors of the CRASH score that the baseline record lacks: instrumental activities of daily living, cognition (Mini-Mental Status), nutrition (Mini Nutritional Assessment), LDH and diastolic blood pressure. This also means the geriatric domains one by one instead of their count, as the ASCO guideline lists them ([Dale et al., 2023](../background/references.md#dale-2023)), and falls. | schema, engine |
| 1.4 | Pancreatic cancer: bilirubin, which guides the choice of regimen ([Conroy et al., 2023](../background/references.md#conroy-2023); [Sohal et al., 2020](../background/references.md#sohal-2020)) and is in the baseline record. The Karnofsky score is not in the schema. | risk model; schema and engine for the Karnofsky score |
| 1.5 | Number of earlier therapy lines, G-CSF prophylaxis and the other baseline blood values, which are in the baseline record. Number of drugs is not. | risk model |
| 1.6 | Patients aged 65 or older without a geriatric assessment are counted as unimpaired. Better: impute the domains from age and ECOG, or show the score as uncertain. | risk model |
| 1.7 | Show next to the risk what the scenario "risk-adapted start" of the engine achieves for a patient like this one. The engine reproduces the relative risk of GAP70+ ([Mohile et al., 2021](../background/references.md#mohile-2021)) for flagged patients who take part. | risk model, app |
| 1.8 | Secondary events: dose reduction, stop of treatment and hospital stay, all of which can be derived from the event and outcome tables. Falls are not in the schema. | risk model; schema and engine for falls |
| 1.9 | Time to first event: cumulative risk by day instead of one 90-day probability, as candidate 2 has it. The median time to the first severe toxicity was 22 days in [Extermann et al. (2012)](../background/references.md#extermann-2012). | risk model |
| 1.10 | Effects that differ by regimen, for example a stronger age effect with combination chemotherapy. | literature |
| 1.11 | Calibrate to rates in routine care instead of trial rates, once the literature covers them (report, section 9). | literature |

## Candidate 2: lung toxicity

| # | Extension | Needs |
|---|---|---|
| 2.1 | **Detection model.** The report names candidate 2 as the first detection model. The observation table holds weekly oxygen saturation, cough and reported breathlessness, and the outcome table the true onset and the recognition day. A first rule comes from an expert panel: a fall of the oxygen saturation at rest by 2 to 4 points over 1 to 3 days should lead to an examination ([Swain et al., 2022](../background/references.md#swain-2022)). The main measure: how much earlier than the 43-day gap between true and recognised onset in [Powell et al. (2022)](../background/references.md#powell-2022) the model detects an event. Heart and breathing rate and home spirometry ([Tarantino et al., 2023](../background/references.md#tarantino-2023)) are not in the schema. | risk model |
| 2.2 | Dose (5.4 mg/kg, 6.4 mg/kg, above 6.4 mg/kg; hazard ratios 1.30 and 2.92) and enrolment in Japan (hazard ratio 2.08), both in [Powell et al. (2022)](../background/references.md#powell-2022). | schema, engine |
| 2.3 | Therapy line: 10.5% lung toxicity in a largely second-line trial against about 15% in heavily pretreated patients ([Swain et al., 2022](../background/references.md#swain-2022)). The references give no hazard ratio. | literature |
| 2.4 | Pneumonitis under checkpoint inhibitors (pembrolizumab with chemotherapy), about 4% with anti-PD-1. Risk factors named by [Haanen et al. (2022)](../background/references.md#haanen-2022): tobacco exposure, chronic lung disease, earlier chest radiotherapy. The references give no effect sizes. | literature, schema, engine |
| 2.5 | Ribociclib, with grade 3 lung inflammation in 0.6% ([Hortobagyi et al., 2022](../background/references.md#hortobagyi-2022)). | literature, engine (regimen) |
| 2.6 | Risk by grade from patient factors, instead of a fixed share of 71.1% for grade 2 or higher. Fatal events (0.8–2.4%) separately. | literature |
| 2.7 | Correlated risk factors in the reference population (for example age and renal function) instead of independence when setting `r0`. | literature or engine |
| 2.8 | Show the risk over time and the remaining risk in the app during follow-up. | app |

## Candidate 3: severe or febrile neutropenia

| # | Extension | Needs |
|---|---|---|
| 3.1 | Febrile neutropenia as an event of its own, next to the combined event. Guidelines tie G-CSF to a risk of febrile neutropenia of 20% ([Lyman et al., 2011](../background/references.md#lyman-2011)). | schema, engine, risk model |
| 3.2 | The risk per cycle and the risk in later cycles for a patient without an event so far. Two thirds of first events fall into the first cycle ([Lyman et al., 2011](../background/references.md#lyman-2011)). | risk model; engine for cycles |
| 3.3 | Rates for the regimens without one: lutetium-177–PSMA-617, olaparib, pembrolizumab with chemotherapy. | literature |
| 3.4 | Published shares of the trial patients with G-CSF and an age of 65 or older, in place of the assumed ones. | literature |
| 3.5 | Earlier chemotherapy that varies within a regimen, so that its effect can be estimated on engine data. | engine |
| 3.6 | A detection model on the blood counts over the cycles and on temperature, which is not in the schema. | risk model; schema and engine for temperature |
| 3.7 | Show what G-CSF would change for a patient, as candidate 5 does for the type of androgen deprivation. | risk model, app |

## Candidate 4: severe diarrhoea

| # | Extension | Needs |
|---|---|---|
| 4.1 | Published effect sizes for age, performance status, albumin and UGT1A1 with irinotecan. | literature |
| 4.2 | Further regimens: FOLFIRINOX (16.8% severe diarrhoea in [Nichetti et al., 2024](../background/references.md#nichetti-2024)), sacituzumab govitecan (10%, [Bardia et al., 2021](../background/references.md#bardia-2021)), colitis under checkpoint inhibitors with inflammatory bowel disease as risk factor ([Haanen et al., 2022](../background/references.md#haanen-2022)). | engine (regimens), schema |
| 4.3 | Hypokalaemia of grade 3 or higher, 15% with NALIRIFOX ([Wainberg et al., 2023](../background/references.md#wainberg-2023)), and potassium as a weekly value. Low potassium is a correctable risk factor for QT prolongation. | schema, engine |
| 4.4 | A detection model on the weekly reports of diarrhoea, on weight and on potassium. The engine raises reported diarrhoea in the week before an event. | risk model; schema and engine for weight and potassium |

## Candidate 5: cardiovascular events

| # | Extension | Needs |
|---|---|---|
| 5.1 | **Detection model.** The observation table holds weekly systolic blood pressure and reported chest pain, and the outcome table the start of the warning phase and the day of the event. The model would flag a likely warning phase. Half of the events in the engine have none, which limits what detection can reach. | risk model |
| 5.2 | Replace the assumed hazard ratios for age, diabetes, hypertension, smoking and renal function by published estimates, for example from SCORE2 and SCORE2-OP, which the ESC guideline recommends for these patients ([Lyon et al., 2022](../background/references.md#lyon-2022)). The SCORE2 publications are not in `references.md`. | literature |
| 5.3 | A meta-analysis of antagonists against agonists in place of the pooling of two trials. The European guideline names one ([Tilki et al., 2024](../background/references.md#tilki-2024)); it is not in `references.md`. | literature |
| 5.4 | Systolic blood pressure as a number, which is in the baseline record, and lipids, LVEF, troponin and natriuretic peptides, which are not. The men of PRONOUNCE had a mean NT-proBNP of 670 pg/ml and a mean troponin T of 18 pg/ml ([Lopes et al., 2021](../background/references.md#lopes-2021)). | risk model; schema and engine for the others |
| 5.5 | The effect of cardiology care and of drugs for secondary prevention, which nearly all men in PRONOUNCE received and to which its authors ascribe the low event rate ([Lopes et al., 2021](../background/references.md#lopes-2021)). | literature, schema, engine |
| 5.6 | Separate risks for myocardial infarction, stroke and cardiovascular death, and risk beyond the first year. | literature, schema, engine |
| 5.7 | The other parts of candidate 5 in the report: cardiac dysfunction under HER2-targeted therapy, QT prolongation with ribociclib, ischaemia with fluoropyrimidines, myocarditis with checkpoint inhibitors, severe hypertension with abiraterone. | literature, schema, engine |
| 5.8 | Show in the app, for a man at high risk on an agonist, his risk on an antagonist. The model computes it. | app |

## All models

| # | Extension | Needs |
|---|---|---|
| B.1 | **Role in the intervention scenarios.** The engine flags patients at therapy start with a stand-in: the true patient-related risk plus noise (`engine/interventions.py`). Candidate 1 could take its place, and candidate 3 could decide on G-CSF, so that a scenario shows what these models achieve. The same holds for the detection model of 2.1 and the detection stand-in. | risk model, engine |
| B.2 | Risk under an intervention: the models describe usual care. A scenario with an adapted start or monitoring lowers the observed rates. | risk model, engine |
| B.3 | Uncertainty per patient: propagate the confidence intervals of the ratios ([Powell et al., 2022](../background/references.md#powell-2022); [Lyman et al., 2011](../background/references.md#lyman-2011)) and the sampling error of the trial rates into a risk interval. | risk model |
| B.4 | Position of a patient in a reference population: percentile of the risk among patients with the same regimen or tumour type. The app needs this for the comparison view. | risk model or app |
| B.5 | Store the explanation (factors and ratios) as a table in the schema, so that the app can read it without calling Python. | schema |
| B.6 | Validate the risk categories, for example by decision curve analysis (net benefit at the thresholds), and decide whether categories should be relative to the regimen rate. Report sensitivity, specificity and predictive values at the thresholds, as [Lyman et al. (2011)](../background/references.md#lyman-2011) do. | risk model |
| B.7 | Confidence intervals for AUC and calibration by bootstrap; evaluation by subgroups of age, sex and tumour type. | risk model |
| B.8 | Competing events: death and stop of therapy for other reasons end the observation, and the outcome table records both. The lung toxicity analysis of [Powell et al. (2022)](../background/references.md#powell-2022) treats discontinuation as a competing event. | risk model |
| B.9 | Machine learning models once the engine produces richer data, compared with the simple models here. | literature, engine |
| B.10 | A model for venous thromboembolism with the Khorana score, which uses tumour site, platelets, haemoglobin, white cells and body mass index ([Key et al., 2020](../background/references.md#key-2020)). All but the event are in the baseline record. | schema, engine, risk model |
