# Toxicity of systemic therapy in advanced pancreatic, prostate and breast cancer

This report collects what the papers in [references.md](references.md) say about toxicity: how often it happens, what it looks like, who is at risk, and what is known about detecting it early. It is the knowledge base for the synthetic data engine and the risk model.

All numbers come from the cited papers. The table at the end of `references.md` shows for each paper whether the full text or only the abstract was read. Where only the abstract was available, the report stays at the level of the abstract.

## 1. Key points

- Severe toxicity is the normal case, not the exception. In the phase 3 trials covered here, between about half and almost nine in ten patients had at least one adverse event of grade 3 or higher.
- Each therapy class has its own pattern: bone marrow suppression and diarrhoea for chemotherapy and some antibody–drug conjugates, lung inflammation for trastuzumab deruxtecan, cardiovascular events for androgen deprivation, dry mouth and blood count changes for radioligand therapy.
- Timing differs by toxicity. Docetaxel-related events cluster in the months of docetaxel treatment. Lung toxicity from trastuzumab deruxtecan appears after a median of four to five months.
- Toxicity is often noticed late. In a pooled analysis of trastuzumab deruxtecan, an expert committee dated the start of lung toxicity earlier than the treating investigators in about half of the events, with a median gap of 43 days (Powell et al., 2022).
- Two randomised trials show that better assessment and monitoring change outcomes: geriatric assessment lowered severe toxicity in older patients from 71% to 51% (Mohile et al., 2021), and weekly electronic symptom reports improved physical function, symptom control and quality of life (Basch et al., 2022).

## 2. How toxicity is measured

The trials grade adverse events with the Common Terminology Criteria for Adverse Events (CTCAE) of the US National Cancer Institute, on a scale from 1 (mild) to 5 (death). "Severe" in this report means grade 3 or higher. The trials used different CTCAE versions, for example version 4 in GAP70+ (Mohile et al., 2021) and version 5.0 in VISION (Sartor et al., 2021) and DESTINY-Breast04 (Modi et al., 2022).

Three things make numbers hard to compare between trials:

- Some trials count all adverse events during treatment, others only those judged to be related to the drug.
- Reporting thresholds differ, for example "events in at least 5% of patients".
- Longer treatment means more time to collect events. DESTINY-Breast04 therefore also reports rates per patient-year (Modi et al., 2022).

Patient-reported outcomes are a second source next to clinician grading. PRO-TECT used weekly patient surveys and the EORTC QLQ-C30 questionnaire (Basch et al., 2022).

## 3. Pancreatic cancer

### First-line chemotherapy for metastatic disease

The three main combination regimens are FOLFIRINOX (fluorouracil, leucovorin, irinotecan, oxaliplatin), NALIRIFOX (the same with liposomal irinotecan) and gemcitabine plus nab-paclitaxel.

NAPOLI 3 compared NALIRIFOX with gemcitabine plus nab-paclitaxel in 770 patients (Wainberg et al., 2023). Safety data refer to 370 and 379 treated patients.

| NAPOLI 3 | NALIRIFOX | Gemcitabine + nab-paclitaxel |
|---|---|---|
| Any adverse event of grade 3 or higher | 87% | 86% |
| Treatment-related event of grade 3 or higher | 71% | 68% |
| Serious adverse event | 54% | 52% |
| Dose reduction | 60% | 54% |
| Stopped treatment because of an adverse event | 32% | 30% |
| Treatment-related death | 2% | 2% |
| Grade 3–4 diarrhoea | 20% | 5% |
| Grade 3–4 nausea | 12% | 3% |
| Grade 3–4 hypokalaemia | 15% | 4% |
| Grade 3–4 neutropenia | 14% | 25% |
| Grade 3–4 decreased neutrophil count (reported separately) | 10% | 14% |
| Grade 3–4 anaemia | 11% | 17% |
| Grade 3–4 peripheral neuropathy | 3% | 6% |

The overall burden is the same in both arms, but the pattern differs: NALIRIFOX causes more gastrointestinal toxicity and hypokalaemia, gemcitabine plus nab-paclitaxel more blood count changes and neuropathy. Median treatment duration was 24.3 versus 17.6 weeks.

A meta-analysis of seven phase 3 trials with 2581 patients compared all three regimens (Nichetti et al., 2024):

- Severe low platelet counts: 1.6% with NALIRIFOX, 11.8% with FOLFIRINOX, 10.8% with gemcitabine plus nab-paclitaxel.
- Severe diarrhoea: 20.3% with NALIRIFOX, 16.8% with FOLFIRINOX, 15.7% with gemcitabine plus nab-paclitaxel.
- FOLFIRINOX had the highest risk of febrile neutropenia and vomiting.
- Gemcitabine plus nab-paclitaxel had the highest rates of anaemia and peripheral neuropathy.
- Survival with NALIRIFOX and FOLFIRINOX was similar, so the choice between them is largely a question of the toxicity profile and patient selection.

### Guideline

The ESMO guideline on pancreatic cancer (Conroy et al., 2023) is the clinical frame for treatment choice. Its full text has not been read yet, see section 7.

## 4. Prostate cancer

### Androgen deprivation

Androgen deprivation is the base of all systemic treatment in advanced prostate cancer. HERO compared the oral antagonist relugolix with leuprolide injections over 48 weeks in 930 patients (Shore et al., 2020). Major adverse cardiovascular events occurred in 2.9% with relugolix and 6.2% with leuprolide (hazard ratio 0.46). Cardiovascular risk is therefore part of the toxicity picture from the first treatment step, and it depends on the drug.

### Treatment intensification in hormone-sensitive disease

Two trials added a second hormonal drug to androgen deprivation plus docetaxel.

| | PEACE-1 (Fizazi et al., 2022) | ARASENS (Smith et al., 2022) |
|---|---|---|
| Added drug | Abiraterone plus prednisone | Darolutamide |
| Severe adverse events with / without the added drug | 63% / 52% (grade 3 or worse) | 66.1% / 63.5% (grade 3 or 4) |
| Main difference | Hypertension 22% / 13% | Grade 3–4 hypertension 6.4% / 3.2% |
| Neutropenia | Not increased by abiraterone | Grade 3–4: 33.7% / 34.2% |
| Febrile neutropenia | Not increased by abiraterone | Grade 3–4: 7.8% / 7.4% |

In ARASENS, serious adverse events occurred in 44.8% and 42.3%, and deaths from adverse events in 4.1% and 4.0%. The most common events were highest in both arms while docetaxel was given and fell afterwards. Most of the severe toxicity of these triplets therefore comes from docetaxel and is concentrated in the first months.

### PARP inhibition

In PROfound, olaparib was given to men with castration-resistant disease and alterations in DNA repair genes. Anaemia and nausea were the main toxic effects (de Bono et al., 2020).

### Radioligand therapy

VISION tested lutetium-177–PSMA-617 added to standard care after hormonal therapy and taxanes (Sartor et al., 2021). Safety data refer to 529 and 205 patients.

| VISION | Lutetium-177–PSMA-617 + standard care | Standard care |
|---|---|---|
| Any adverse event of grade 3 or higher | 52.7% | 38.0% |
| Fatigue (all grades / grade 3 or higher) | 43.1% / 5.9% | 22.9% / 1.5% |
| Dry mouth (all grades / grade 3 or higher) | 38.8% / 0 | 0.5% / 0 |
| Nausea (all grades / grade 3 or higher) | 35.3% / 1.3% | 16.6% / 0.5% |
| Anaemia (all grades / grade 3 or higher) | 31.8% / 12.9% | 13.2% / 4.9% |
| Thrombocytopenia (all grades / grade 3 or higher) | 17.2% / 7.9% | 4.4% / 1.0% |
| Lymphopenia (all grades / grade 3 or higher) | 14.2% / 7.8% | 3.9% / 0.5% |

Adverse events led to stopping the radioligand in 11.9%, to interruption in 16.1% and to dose reduction in 5.7%. Five deaths were judged to be drug-related: three from pancytopenia or bone marrow failure and two from bleeding inside the skull. Quality of life was not worse than with standard care alone.

## 5. Breast cancer

### Antibody–drug conjugates

Trastuzumab deruxtecan was compared with chemotherapy of the physician's choice in HER2-low disease in DESTINY-Breast04 (Modi et al., 2022). Safety data refer to 371 and 172 patients.

| DESTINY-Breast04 | Trastuzumab deruxtecan | Chemotherapy |
|---|---|---|
| Any adverse event of grade 3 or higher | 52.6% | 67.4% |
| Serious adverse event | 27.8% | 25.0% |
| Stopped treatment because of an adverse event | 16.2% | 8.1% |
| Dose reduction because of an adverse event | 22.6% | 38.4% |
| Nausea, drug-related, any grade | 73.0% | 23.8% |
| Neutropenia of grade 3 or higher | 13.7% | 40.7% |
| Interstitial lung disease or pneumonitis | 12.1% | 0.6% |

Of the lung events with trastuzumab deruxtecan, 3.5% were grade 1, 6.5% grade 2, 1.3% grade 3 and 0.8% fatal. The median time to onset was 129 days (range 26 to 710).

A pooled analysis of nine earlier studies with 1150 heavily pretreated patients, 44% of them with breast cancer, looked at this lung toxicity in detail (Powell et al., 2022):

- Incidence 15.4%, fatal in 2.2%.
- 77.4% of affected patients had grade 1 or 2 events.
- 87.0% had the first event within 12 months, median 5.4 months.
- For 53.2% of events the adjudication committee set an earlier onset than the investigators. The median difference was 43 days.
- Baseline factors linked to higher risk: age under 65, enrolment in Japan, dose above 6.4 mg/kg, oxygen saturation below 95%, moderate or severe renal impairment, lung comorbidities, and more than four years since first diagnosis.

Sacituzumab govitecan was compared with single-agent chemotherapy in metastatic triple-negative disease in ASCENT (Bardia et al., 2021). Treatment-related events of grade 3 or higher were neutropenia (51% versus 33%), leukopenia (10% versus 5%), diarrhoea (10% versus under 1%), anaemia (8% versus 5%) and febrile neutropenia (6% versus 2%). No death was attributed to sacituzumab govitecan.

Antibody–drug conjugates were designed to be less toxic than chemotherapy. A review points out that most of them still cause toxicity that resembles their cytotoxic payload, plus effects on healthy tissue carrying the target, plus other poorly understood and sometimes life-threatening effects (Tarantino et al., 2023). The review names four ways to improve safety: better dose and schedule, changes to the drug components, biomarkers that predict toxicity, and new diagnostic tools.

### Immunotherapy plus chemotherapy

KEYNOTE-355 added pembrolizumab to chemotherapy in advanced triple-negative disease (Cortes et al., 2022). Treatment-related events of grade 3 to 5 occurred in 68.1% with pembrolizumab and 66.9% with placebo, with treatment-related death in 0.4% and 0%. The rates are almost the same in both arms, so most of the severe toxicity comes from the chemotherapy. Immune-related events add a different kind of risk, see section 6.

### CDK4/6 inhibition

In MONALEESA-2, ribociclib plus letrozole prolonged survival as first-line treatment of hormone receptor-positive disease (Hortobagyi et al., 2022). The abstract reports no new safety signals after a median follow-up of 6.6 years. Detailed toxicity data from this paper are not yet included.

## 6. Toxicity across tumour types

### Immune-related adverse events

The ASCO guideline gives management rules by grade (Schneider et al., 2021):

- Grade 1: continue the checkpoint inhibitor with close monitoring. Exceptions are some neurological, haematological and cardiac toxicities.
- Grade 2: pause for most toxicities and consider restarting once symptoms are back to grade 1 or lower. Corticosteroids may be given.
- Grade 3: pause and start high-dose corticosteroids, tapered over at least four to six weeks. Some cases need other immunosuppressive drugs.
- Grade 4: stop permanently, except for endocrine toxicities that are controlled by hormone replacement.

The panel notes that high-quality evidence is scarce and that the recommendations rest on expert consensus. The ESMO guideline on the same topic (Haanen et al., 2022) has not been read in full yet, see section 7.

### Peripheral neuropathy

Neuropathy matters in all three patient groups because oxaliplatin and taxanes are widely used. The ASCO guideline update states (Loprinzi et al., 2020):

- No drug is recommended to prevent chemotherapy-induced neuropathy.
- Acetyl-L-carnitine for prevention should be discouraged.
- When neuropathy becomes intolerable or impairs function, clinicians should consider delaying, reducing, replacing or stopping chemotherapy.
- Duloxetine is the only drug with adequate evidence for established painful neuropathy, and its benefit is limited.

Since prevention does not work, early detection and dose adjustment are the only tools.

### Cardiovascular toxicity

The ESC guideline on cardio-oncology (Lyon et al., 2022) covers cardiovascular risk before, during and after cancer therapy. Its full text has not been read yet, see section 7. The trial data above already show two cardiovascular signals: major cardiovascular events under androgen deprivation (Shore et al., 2020) and hypertension when abiraterone or darolutamide is added (Fizazi et al., 2022; Smith et al., 2022).

### Older patients

GAP70+ enrolled 718 patients aged 70 or older with incurable cancer and at least one impaired domain in a geriatric assessment, starting a new treatment with a high risk of toxicity (Mohile et al., 2021). Mean age was 77 years, and patients had on average 4.5 impaired domains.

- With usual care, 71% had a toxic effect of grade 3 to 5 within three months. This is the baseline risk in this group.
- When oncologists received a summary of the assessment with management recommendations, the rate was 51% (relative risk 0.74).
- Severe non-haematological toxicity fell from 51.8% to 31.8%.
- Falls within three months fell from 21% to 12%.
- More patients in the intervention group started with reduced treatment intensity (48.7% versus 35.0%). Survival did not differ between the groups.

Function, comorbidity, nutrition, cognition and medication therefore carry information about toxicity risk that standard oncology assessment misses.

### Symptom monitoring by patients

PRO-TECT randomised 52 US community oncology practices with 1191 patients treated for metastatic cancer (Basch et al., 2022). Patients in the intervention group filled in a weekly symptom survey by web or phone for up to one year. Severe or worsening symptoms triggered an alert to the care team.

After three months, physical function, symptom control and health-related quality of life were each about 2.5 points better on a 100-point scale than with usual care. More patients had a clinically meaningful benefit, with odds ratios of 1.35, 1.50 and 1.41. The primary endpoint, overall survival, was not yet reported in this paper.

## 7. Guidelines not yet read in full

Three guidelines have no abstract, and their full texts could not be retrieved. Their content is not yet part of this report.

| Guideline | Scope |
|---|---|
| Conroy et al. (2023) | ESMO guideline on diagnosis, treatment and follow-up of pancreatic cancer |
| Haanen et al. (2022) | ESMO guideline on toxicities from immunotherapy |
| Lyon et al. (2022) | ESC guideline on cardio-oncology |

## 8. What this means for the project

This section is our reading of the references, not a statement from the papers.

**Outcomes to model**

- Any toxicity of grade 3 or higher within a time window. This is the primary endpoint of GAP70+ and the most comparable number across trials.
- Toxicity by type: neutropenia and febrile neutropenia, anaemia, thrombocytopenia, diarrhoea, nausea, neuropathy, hypertension, cardiovascular events, lung inflammation, immune-related events.
- Consequences: dose reduction, interruption, stopping treatment, serious adverse event, death.

**Reference rates for the synthetic data engine**

The tables in sections 3 to 5 give regimen-specific rates. Trial patients are selected, mostly with good performance status. The 71% rate in the usual-care group of GAP70+ shows how much higher the risk is in older, frailer patients.

**Risk factors named in the references**

- Regimen and dose.
- Age and impairments in geriatric assessment domains (Mohile et al., 2021).
- For lung toxicity of trastuzumab deruxtecan: oxygen saturation, renal function, lung comorbidities, dose, age, time since diagnosis (Powell et al., 2022).
- Choice of androgen deprivation drug for cardiovascular events (Shore et al., 2020).

**Timing**

- Docetaxel toxicity peaks during the docetaxel cycles (Smith et al., 2022).
- Lung toxicity of trastuzumab deruxtecan starts after a median of 129 days in DESTINY-Breast04 and 5.4 months in the pooled analysis, mostly within the first year.
- GAP70+ counts toxicity over the first three months.

**Where early detection can gain time**

- The 43-day gap between adjudicated and investigator-reported onset of lung toxicity (Powell et al., 2022) is a measured delay in current care.
- Weekly symptom reports with alerts improve outcomes (Basch et al., 2022). Symptom time series are therefore a realistic input for a detection model.
- For neuropathy there is no prevention, so earlier detection is the only way to act (Loprinzi et al., 2020).

## 9. Topics not covered by the current references

- Prediction models and machine learning for toxicity.
- Wearables and other continuous measurements.
- Pharmacogenetics, for example of fluoropyrimidines and irinotecan.
- Toxicity rates in routine care compared with trials.
- Incidence figures for immune-related adverse events by drug class.
- Detailed toxicity of CDK4/6 inhibitors and of endocrine therapy in breast cancer.
- Second-line chemotherapy in pancreatic cancer and cabazitaxel in prostate cancer.
