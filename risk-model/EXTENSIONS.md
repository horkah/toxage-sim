# Possible extensions

Open ideas for the risk models of candidates 1 and 2. Each item says what it needs: a change in the [schema](../schema/), the [engine](../engine/), the literature in [background/](../background/), or only the risk model. Items leave this list when they are done.

## Candidate 1: any severe toxicity in 90 days

| # | Extension | Needs |
|---|---|---|
| 1.1 | Replace the assumed odds ratios for age, ECOG and geriatric domains by published estimates. Published toxicity scores for older patients, such as the CARG score (Hurria et al., 2011) and the CRASH score (Extermann et al., 2012), are candidates; they are not yet in `references.md` and have to be checked first. | literature |
| 1.2 | Use the seven geriatric domains one by one instead of their count, as the ASCO guideline lists them (Dale et al., 2023): physical function, cognition, emotional health, comorbidity, polypharmacy, nutrition, social support. Add falls. | schema, engine |
| 1.3 | Pancreatic cancer: Karnofsky score and bilirubin, which guide the choice of regimen (Conroy et al., 2023; Sohal et al., 2020). | schema, engine |
| 1.4 | Number of earlier therapy lines, number of drugs, planned dose intensity and dose reduction at start. | schema, engine |
| 1.5 | Patients aged 65 or older without a geriatric assessment are counted as unimpaired. Better: impute the domains from age and ECOG, or show the score as uncertain. | risk model |
| 1.6 | Scenario "with geriatric assessment-guided management": apply the relative risk of 0.74 from GAP70+ (Mohile et al., 2021) to show what the trial achieved. Only for patients like the trial population. | risk model |
| 1.7 | Secondary events: dose reduction, stop of treatment, hospital stay, falls. Split into haematological and non-haematological toxicity, as GAP70+ reports both. | schema, engine |
| 1.8 | Time to first event: cumulative risk by day instead of one 90-day probability, so the app can show the course. | risk model, engine onset model from literature |
| 1.9 | Effects that differ by regimen, for example a stronger age effect with combination chemotherapy. | literature |
| 1.10 | Calibrate to rates in routine care instead of trial rates, once the literature covers them (report, section 9). | literature |

## Candidate 2: lung toxicity

| # | Extension | Needs |
|---|---|---|
| 2.1 | **Detection model.** The report names candidate 2 as the first detection model. It needs measurements during therapy: oxygen saturation, heart and breathing rate, cough, home spirometry and reported breathlessness (Tarantino et al., 2023). The model would update the risk with each new value and flag a likely onset. Its main measure: how much earlier than the 43-day gap between true and recognised onset in Powell et al. (2022) it detects an event. | schema (course table), engine (time series before and after onset), risk model |
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
| B.1 | **Tests on data that differ from the model.** At the moment engine and risk model share structure and parameters, so evaluation checks the code only. The engine needs scenarios that deviate on purpose: other effect sizes, interactions, correlated baseline factors, a different population mix, noise in the measurements. Then the literature model, the fitted model and the regimen-only model can be compared fairly. | engine |
| B.2 | Uncertainty per patient: propagate the confidence intervals of the hazard ratios (Powell et al., 2022) and the sampling error of the trial rates into a risk interval. | risk model |
| B.3 | Position of a patient in a reference population: percentile of the risk among patients with the same regimen or tumour type. The app needs this for the comparison view. | risk model or app |
| B.4 | Store the explanation (factors and ratios) as a table in the schema, so that the app can read it without calling Python. | schema |
| B.5 | Validate the risk categories, for example by decision curve analysis (net benefit at the thresholds), and decide whether categories should be relative to the regimen rate. | risk model |
| B.6 | Confidence intervals for AUC and calibration by bootstrap; evaluation by subgroups of age, sex and tumour type. | risk model |
| B.7 | Competing events: death and stop of therapy for other reasons end the observation. The lung toxicity analysis of Powell et al. (2022) treats discontinuation as a competing event. | engine, risk model |
| B.8 | Machine learning models once the engine produces richer data, compared with the simple models here. The literature on published prediction models is still missing (report, section 9). | literature, engine |
