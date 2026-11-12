# Possible extensions

Open ideas for the risk models of candidates 1 and 2. Each item says what it needs: a change in the [schema](../schema/), the [engine](../engine/), the literature in [background/](../background/), or only the risk model. Items leave this list when they are done.

## Candidate 1: any severe toxicity in 90 days

| # | Extension | Needs |
|---|---|---|
| 1.1 | Replace the assumed odds ratios for age, ECOG and geriatric domains by published estimates. Published toxicity scores for older patients, such as the CARG score (Hurria et al., 2011) and the CRASH score (Extermann et al., 2012), are candidates; they are not yet in `references.md` and have to be checked first. | literature |
| 1.2 | Use the seven geriatric domains one by one instead of their count, as the ASCO guideline lists them (Dale et al., 2023): physical function, cognition, emotional health, comorbidity, polypharmacy, nutrition, social support. Add falls. | schema, engine |
| 1.3 | Pancreatic cancer: bilirubin, which guides the choice of regimen (Conroy et al., 2023; Sohal et al., 2020) and is in the baseline record. The Karnofsky score is not in the schema. | risk model; schema and engine for the Karnofsky score |
| 1.4 | Number of earlier therapy lines, starting dose level, G-CSF prophylaxis, albumin and baseline blood values, which are in the baseline record. Number of drugs is not. | risk model |
| 1.5 | Patients aged 65 or older without a geriatric assessment are counted as unimpaired. Better: impute the domains from age and ECOG, or show the score as uncertain. | risk model |
| 1.6 | Show next to the risk what the scenario "risk-adapted start" of the engine achieves for a patient like this one. The engine reproduces the relative risk of GAP70+ (Mohile et al., 2021) for flagged patients who take part. | risk model, app |
| 1.7 | Secondary events: dose reduction, stop of treatment and hospital stay, and the split into haematological and non-haematological toxicity as in GAP70+, all of which can be derived from the event and outcome tables. Falls are not in the schema. | risk model; schema and engine for falls |
| 1.8 | Time to first event: cumulative risk by day instead of one 90-day probability, so the app can show the course. The outcome table holds the day of the first severe event. | risk model |
| 1.9 | Effects that differ by regimen, for example a stronger age effect with combination chemotherapy. | literature |
| 1.10 | Calibrate to rates in routine care instead of trial rates, once the literature covers them (report, section 9). | literature |

## Candidate 2: lung toxicity

| # | Extension | Needs |
|---|---|---|
| 2.1 | **Detection model.** The report names candidate 2 as the first detection model. The observation table holds weekly oxygen saturation, cough and reported breathlessness, and the outcome table the true onset and the recognition day. The model would update the risk with each new value and flag a likely onset. Its main measure: how much earlier than the 43-day gap between true and recognised onset in Powell et al. (2022) it detects an event. Heart and breathing rate and home spirometry (Tarantino et al., 2023) are not in the schema. | risk model |
| 2.2 | Dose (5.4 mg/kg, 6.4 mg/kg, above 6.4 mg/kg; hazard ratios 1.30 and 2.92) and enrolment in Japan (hazard ratio 2.08), both in Powell et al. (2022). | schema, engine |
| 2.3 | Pneumonitis under checkpoint inhibitors (pembrolizumab with chemotherapy), about 4% with anti-PD-1. Risk factors named by Haanen et al. (2022): tobacco exposure, chronic lung disease, earlier chest radiotherapy. The references give no effect sizes. | literature, schema, engine |
| 2.4 | Ribociclib, with grade 3 lung inflammation in 0.6% (Hortobagyi et al., 2022). | literature, engine (regimen) |
| 2.5 | Risk over time: probability of onset by month 3, 6, 12 and 24 from the onset distribution (median 129 days, 87% within 12 months), and the remaining risk of a patient who is still free of lung toxicity at a given day. The app can show this during follow-up. | risk model |
| 2.6 | Risk by grade from patient factors, instead of a fixed share of 71.1% for grade 2 or higher. Fatal events (0.8–2.2%) separately. | literature |
| 2.7 | Correlated risk factors in the reference population (for example age and renal function) instead of independence when setting `r0`. | literature or engine |
| 2.8 | Apply the risk factors only to trastuzumab deruxtecan and use a plain rate for single-agent chemotherapy, unless evidence supports transfer. | risk model |

## Both models

| # | Extension | Needs |
|---|---|---|
| B.1 | **Role in the intervention scenarios.** The engine flags patients at therapy start with a stand-in: the true patient-related risk plus noise (`engine/interventions.py`). Candidate 1 could take its place, so that a scenario shows what this model achieves. The same holds for the detection model of 2.1 and the detection stand-in. | risk model, engine |
| B.9 | Risk under an intervention: the models describe usual care. A scenario with an adapted start or monitoring lowers the observed rates. | risk model, engine |
| B.2 | Uncertainty per patient: propagate the confidence intervals of the hazard ratios (Powell et al., 2022) and the sampling error of the trial rates into a risk interval. | risk model |
| B.3 | Position of a patient in a reference population: percentile of the risk among patients with the same regimen or tumour type. The app needs this for the comparison view. | risk model or app |
| B.4 | Store the explanation (factors and ratios) as a table in the schema, so that the app can read it without calling Python. | schema |
| B.5 | Validate the risk categories, for example by decision curve analysis (net benefit at the thresholds), and decide whether categories should be relative to the regimen rate. | risk model |
| B.6 | Confidence intervals for AUC and calibration by bootstrap; evaluation by subgroups of age, sex and tumour type. | risk model |
| B.7 | Competing events: death and stop of therapy for other reasons end the observation, and the outcome table records both. The lung toxicity analysis of Powell et al. (2022) treats discontinuation as a competing event. | risk model |
| B.8 | Machine learning models once the engine produces richer data, compared with the simple models here. The literature on published prediction models is still missing (report, section 9). | literature, engine |
