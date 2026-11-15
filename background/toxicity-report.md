# Toxicity of systemic therapy in advanced pancreatic, prostate and breast cancer

This report collects what the papers and guidelines in [references.md](references.md) say about toxicity of systemic cancer therapy: how often it happens, what it looks like, when it starts, who is at risk, and how guidelines ask clinicians to assess and monitor it. From this it derives candidates for risk models that identify patients at risk of severe side effects early.

All numbers come from the cited sources. The table "Full texts" in `references.md` shows for each source whether the full text or only the abstract was read. Sections 2 to 7 report what the sources say. Section 8 is our own derivation. Five of its candidates exist as risk models in [risk-model/](../risk-model/).

## Contents

1. Key points
2. How toxicity is measured
3. Pancreatic cancer
4. Prostate cancer
5. Breast cancer
6. Toxicity across tumour types
7. What guidelines ask for: risk assessment and monitoring
8. Candidates for risk models
9. Topics not covered by the current references

## 1. Key points

- Severe toxicity is the normal case. In the phase 3 trials covered here, between about half and almost nine in ten patients had at least one adverse event of grade 3 or higher.
- Each therapy class has its own pattern, its own timing and its own risk factors. One general model will therefore not be enough. A small set of models per toxicity type fits the evidence better.
- Guidelines already use risk stratification in some areas: performance status and bilirubin for the choice of pancreatic chemotherapy, the HFA-ICOS tool and SCORE2 for cardiovascular risk, geriatric assessment for patients aged 65 or older, the Khorana score for venous thromboembolism, the MASCC index for febrile neutropenia. In other areas they state openly that no validated tool exists, for example for cardiovascular risk under androgen deprivation.
- Published prediction models exist for two events. A model for severe or febrile neutropenia in the first cycle reached an area under the curve of 0.81 in validation ([Lyman et al., 2011](references.md#lyman-2011)). The CRASH score for any severe toxicity in older patients reached 0.64, and its authors found that patient differences count two to three times more than regimen differences ([Extermann et al., 2012](references.md#extermann-2012)). Predicting a specific toxicity works better than predicting any toxicity.
- Toxicity is often noticed late. For lung toxicity from trastuzumab deruxtecan, an expert committee dated the onset earlier than the treating investigators in about half of the events, with a median gap of 43 days ([Powell et al., 2022](references.md#powell-2022)).
- Better assessment and monitoring change outcomes. Geriatric assessment lowered severe toxicity in older patients from 71% to 51% ([Mohile et al., 2021](references.md#mohile-2021)) and from 61% to 51% in a second trial ([Dale et al., 2023](references.md#dale-2023)). Weekly electronic symptom reports improved physical function, symptom control and quality of life ([Basch et al., 2022](references.md#basch-2022)), and the European guideline recommends them during systemic treatment ([Di Maio et al., 2022](references.md#di-maio-2022)).
- Monitoring helps only if someone acts. Symptom reports without a named person to respond showed no benefit in the trials the guideline reviews ([Di Maio et al., 2022](references.md#di-maio-2022)).
- The evidence on the type of androgen deprivation and cardiovascular events is open. HERO found fewer events with an antagonist, PRONOUNCE found no difference in men with cardiovascular disease and was stopped early ([Lopes et al., 2021](references.md#lopes-2021)).

## 2. How toxicity is measured

The trials grade adverse events with the Common Terminology Criteria for Adverse Events (CTCAE) of the US National Cancer Institute, on a scale from 1 (mild) to 5 (death). "Severe" in this report means grade 3 or higher. The trials used different CTCAE versions, for example 4.03 in HERO, 4 in GAP70+ and 5.0 in VISION and DESTINY-Breast04.

Three things make numbers hard to compare between trials:

- Some trials count all adverse events during treatment, others only those judged to be related to the drug.
- Reporting thresholds differ, for example "events in at least 5% of patients".
- Longer treatment means more time to collect events. DESTINY-Breast04 therefore also reports rates per patient-year ([Modi et al., 2022](references.md#modi-2022)).

Definitions of "severe" differ as well. The CRASH study counted haematological toxicity only from grade 4 and non-haematological toxicity from grade 3, because this is the level at which trials ask for a dose change ([Extermann et al., 2012](references.md#extermann-2012)). The neutropenia model of [Lyman et al. (2011)](references.md#lyman-2011) counts a neutrophil count below 0.5 × 10^9/l, which is grade 4, or febrile neutropenia. The same authors state that trials underreport neutropenia and its complications and that the rates of one regimen vary widely between trials.

Patient-reported outcomes are a second source next to clinician grading. PRO-TECT used weekly patient surveys and the EORTC QLQ-C30 questionnaire ([Basch et al., 2022](references.md#basch-2022)). A secondary analysis of GAP70+ used the patient-reported version of the CTCAE: 88.9% of the patients with geriatric assessment and 94.8% of the patients with usual care reported a symptomatic toxicity of grade 2 or higher ([Dale et al., 2023](references.md#dale-2023)). Clinicians detect symptoms less often than patients report them and rate them as less severe, most of all for symptoms that are not life-threatening ([Di Maio et al., 2022](references.md#di-maio-2022)).

Some toxicities have their own definitions. The ESC guideline defines cancer therapy-related cardiac dysfunction by symptoms, left ventricular ejection fraction (LVEF), global longitudinal strain (GLS) and cardiac biomarkers ([Lyon et al., 2022](references.md#lyon-2022)):

| Asymptomatic cardiac dysfunction | Definition |
|---|---|
| Severe | New LVEF reduction to below 40% |
| Moderate | New LVEF reduction by 10 percentage points or more to an LVEF of 40–49%, or a smaller reduction to 40–49% together with a new relative GLS decline of more than 15% or a new rise in cardiac biomarkers |
| Mild | LVEF of 50% or more with a new relative GLS decline of more than 15% and/or a new rise in cardiac biomarkers |

## 3. Pancreatic cancer

### Treatment frame

Both guidelines tie the choice of first-line chemotherapy for metastatic disease to the patient's condition. This is risk stratification by expected tolerance.

| Patient | ESMO ([Conroy et al., 2023](references.md#conroy-2023)) | ASCO ([Sohal et al., 2020](references.md#sohal-2020)) |
|---|---|---|
| ECOG 0–1, bilirubin below 1.5 times the upper limit of normal | FOLFIRINOX or gemcitabine plus nab-paclitaxel | FOLFIRINOX if comorbidity profile is favourable, a support system exists and port and pump services are available; gemcitabine plus nab-paclitaxel if comorbidity profile is relatively favourable |
| ECOG 2 with Karnofsky score of 70 or more and bilirubin up to 1.5 times the upper limit | Gemcitabine plus nab-paclitaxel can be considered | Gemcitabine alone; a second drug may be added with proactive dose and schedule adjustments |
| ECOG 2 with Karnofsky score below 70 and/or bilirubin above 1.5 times the upper limit | Gemcitabine alone | Gemcitabine alone |
| ECOG 3–4 | Symptom-directed care, because the risks of chemotherapy likely outweigh the benefit | Cancer-directed therapy only case by case (ECOG 3 or poorly controlled comorbidity) |

The ESMO guideline adds that there is no randomised comparison of FOLFIRINOX with gemcitabine plus nab-paclitaxel, and that real-world data suggest greater activity but also higher toxicity for FOLFIRINOX. Most patients are unsuitable for third-line treatment because of poor nutritional status or performance status.

The same logic holds for the second line ([Sohal et al., 2020](references.md#sohal-2020)). Patients with ECOG 0 or 1 and a favourable comorbidity profile get the regimen they did not have before: gemcitabine plus nab-paclitaxel after FOLFIRINOX, fluorouracil plus nanoliposomal irinotecan after a gemcitabine-based regimen. Patients with ECOG 2 or relevant comorbidity get gemcitabine or fluorouracil alone, and a second drug only with proactive adjustments of dose and schedule.

### Toxicity of first-line regimens

NAPOLI 3 compared NALIRIFOX with gemcitabine plus nab-paclitaxel in 770 patients ([Wainberg et al., 2023](references.md#wainberg-2023)). Safety data refer to 370 and 379 treated patients.

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

A meta-analysis of seven phase 3 trials with 2581 patients compared all three regimens ([Nichetti et al., 2024](references.md#nichetti-2024)):

- Severe low platelet counts: 1.6% with NALIRIFOX, 11.8% with FOLFIRINOX, 10.8% with gemcitabine plus nab-paclitaxel.
- Severe diarrhoea: 20.3% with NALIRIFOX, 16.8% with FOLFIRINOX, 15.7% with gemcitabine plus nab-paclitaxel.
- FOLFIRINOX had the highest risk of febrile neutropenia and vomiting.
- Gemcitabine plus nab-paclitaxel had the highest rates of anaemia and peripheral neuropathy.
- Survival with NALIRIFOX and FOLFIRINOX was similar, so the choice between them is largely a question of the toxicity profile and patient selection.

### Other points from the ESMO guideline

- Venous thromboembolism has a reported prevalence of about 25% in pancreatic cancer, and the risk rises further with chemotherapy. Three trials showed that primary prevention with low-molecular-weight heparin, apixaban or rivaroxaban is safe and effective in outpatients with advanced disease on chemotherapy. Section 6 gives the numbers.
- Maintenance with olaparib in patients with germline BRCA mutations doubled the rate of grade 3 adverse events (49% versus 25%). The ASCO guideline counts 234 against 150 serious adverse events per 1000 patients and no gain in overall survival ([Sohal et al., 2020](references.md#sohal-2020)).
- Factors linked to worse survival in advanced disease are ECOG 2, age over 65, albumin below 35 g/l, synchronous metastases, liver metastases, number of metastatic sites and high CA 19-9.

## 4. Prostate cancer

### Treatment frame

Both guidelines combine androgen deprivation with further drugs in metastatic disease and tie the choice to fitness.

- The ASCO guideline offers docetaxel, abiraterone, enzalutamide or apalutamide, each with androgen deprivation, in metastatic hormone-sensitive disease ([Virgo et al., 2021](references.md#virgo-2021)). It limits docetaxel to men with metastases at first diagnosis or high-volume disease. It notes that docetaxel is somewhat more toxic than the hormonal drugs but is given for a short time. In the trials of enzalutamide and apalutamide, adverse events of grade 3 or higher were about as frequent as in the control arms (24.3% with enzalutamide versus 25.6% with placebo in ARCHES).
- The European guideline goes further ([Tilki et al., 2024](references.md#tilki-2024)). Androgen deprivation alone should not be offered to men who are fit for a combination, have a life expectancy of at least a year and accept the higher risk of side effects. Docetaxel should only be given together with abiraterone or darolutamide.
- After docetaxel and one hormonal drug, the European guideline names cabazitaxel, lutetium-177–PSMA-617 and, with alterations in DNA repair genes, PARP inhibitors.

The ASCO guideline asks clinicians to review all chronic conditions before planning treatment. In men with prostate cancer older than 65 the most common ones are hypertension, hyperlipidaemia, ischaemic heart disease, anaemia and diabetes ([Virgo et al., 2021](references.md#virgo-2021)). These are the risk factors of the cardiovascular events below.

### Androgen deprivation

HERO compared the oral antagonist relugolix with leuprolide injections over 48 weeks in 930 patients ([Shore et al., 2020](references.md#shore-2020)).

- Major adverse cardiovascular events occurred in 2.9% with relugolix and 6.2% with leuprolide (hazard ratio 0.46).
- More than 90% of the men had at least one cardiovascular risk factor.
- In men with a history of such events, the rates were 3.6% with relugolix (3 of 84) and 17.8% with leuprolide (8 of 45).

The ESC guideline states that GnRH agonists are associated with increased cardiovascular risk and mortality, particularly in men over 60, and that the main effects to consider are hypertension, diabetes, ischaemic heart disease and cardiac dysfunction ([Lyon et al., 2022](references.md#lyon-2022)).

PRONOUNCE is the only trial that compared an antagonist with an agonist with cardiovascular events as primary endpoint ([Lopes et al., 2021](references.md#lopes-2021)). It enrolled men with prostate cancer and atherosclerotic cardiovascular disease, compared degarelix with leuprolide over 12 months and had an independent committee confirm the events.

| | HERO ([Shore et al., 2020](references.md#shore-2020)) | PRONOUNCE ([Lopes et al., 2021](references.md#lopes-2021)) |
|---|---|---|
| Patients | 930 men with advanced prostate cancer | 545 men with prostate cancer and atherosclerotic cardiovascular disease; 900 were planned |
| Antagonist against agonist | Relugolix against leuprolide | Degarelix against leuprolide |
| Events | Myocardial infarction, stroke, death from any cause; from adverse event reports | The same events, confirmed by a blinded committee |
| Events within about 48 weeks, antagonist / agonist | 2.9% / 6.2% | 5.5% / 4.1% |
| Hazard ratio | 0.46 | 1.28 (95% confidence interval 0.59 to 2.79) |
| With the event definition of HERO | – | 5.1% / 7.4%, hazard ratio 0.67 (0.34 to 1.32) |

- PRONOUNCE was stopped early because enrolment was slow and events were rarer than expected: 5.1% and 10.2% had been planned. Its authors call the question unresolved.
- Of the 26 men with an event, 16 had cardiovascular death, myocardial infarction or stroke; the other 10 died of other causes. The rate of HERO therefore overstates cardiovascular events.
- All men in PRONOUNCE were under the care of a cardiologist, 84% took lipid-lowering drugs, 73% drugs acting on the renin-angiotensin system and 69% beta-blockers. The authors suggest that this attention to risk factors explains the low event rate.
- At baseline 46% had had a myocardial infarction, 86% had hypertension, 32% diabetes, and 15% smoked. The authors cite a cohort of 2492 men with prostate cancer in which two thirds had a high cardiovascular risk, 22% cardiovascular disease, 16% diabetes, 45% hypertension and 31% obesity.

Taken together: among the men with an earlier event in HERO and the men of PRONOUNCE, 19 of 314 had an event under an agonist and 18 of 359 under an antagonist. The European guideline still concludes that antagonists might be considered for men with cardiovascular disease or risk factors ([Tilki et al., 2024](references.md#tilki-2024)).

### Treatment intensification in hormone-sensitive disease

Two trials added a second hormonal drug to androgen deprivation plus docetaxel.

| | PEACE-1 ([Fizazi et al., 2022](references.md#fizazi-2022)) | ARASENS ([Smith et al., 2022](references.md#smith-2022)) |
|---|---|---|
| Added drug | Abiraterone plus prednisone | Darolutamide |
| Severe adverse events with / without the added drug | 63% / 52% (grade 3 or worse) | 66.1% / 63.5% (grade 3 or 4) |
| Hypertension | 22% / 13% (severe) | 6.4% / 3.2% (grade 3–4) |
| Liver toxicity | Raised aminotransferases 6% / 1% (severe) | – |
| Neutropenia | Not increased by abiraterone | Grade 3–4: 33.7% / 34.2% |
| Febrile neutropenia | Not increased by abiraterone | Grade 3–4: 7.8% / 7.4% |

The European guideline sums up that abiraterone added modest toxicity, mostly hypertension, and that adverse events were similar in both arms of ARASENS ([Tilki et al., 2024](references.md#tilki-2024)).

In ARASENS, serious adverse events occurred in 44.8% and 42.3%, and deaths from adverse events in 4.1% and 4.0%. The most common events were highest in both arms while docetaxel was given and fell afterwards. In PEACE-1, severe neutropenia occurred in 10% of the abiraterone patients who also received docetaxel and in none of those who did not. G-CSF after each docetaxel cycle was first recommended and later mandatory in PEACE-1. Most of the severe toxicity of these triplets therefore comes from docetaxel and is concentrated in the first months.

### PARP inhibition

In PROfound, olaparib was compared with a hormonal drug in castration-resistant disease with alterations in DNA repair genes ([de Bono et al., 2020](references.md#de-bono-2020)). Safety data refer to 256 and 130 patients.

| PROfound | Olaparib | Control |
|---|---|---|
| Any adverse event of grade 3 or higher | 51% | 38% |
| Anaemia (all grades / grade 3 or higher) | 46% / 21% | 15% / 5% |
| Nausea (all grades) | 41% | 19% |
| Pulmonary embolism | 4% | 1% |
| Interruption because of an adverse event | 45% | 18% |
| Dose reduction because of an adverse event | 22% | 4% |
| Stopped treatment because of an adverse event | 18% | 8% |

Combinations of a PARP inhibitor with a hormonal drug add to this ([Tilki et al., 2024](references.md#tilki-2024)). Anaemia occurred in 48% with olaparib plus abiraterone, in 15% of grade 3, and 18% needed a blood transfusion. With talazoparib plus enzalutamide anaemia of grade 3 or 4 occurred in 46%, and 39% needed a transfusion. The guideline states that PARP inhibitors add substantial toxicity to a hormonal drug alone.

### Radioligand therapy

VISION tested lutetium-177–PSMA-617 added to standard care after hormonal therapy and taxanes ([Sartor et al., 2021](references.md#sartor-2021)). Safety data refer to 529 and 205 patients.

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

### Treatment frame

The ESMO guideline orders treatment by subtype ([Gennari et al., 2021](references.md#gennari-2021)):

| Subtype | First line | Later lines named in this report |
|---|---|---|
| Hormone receptor-positive, HER2-negative | CDK4/6 inhibitor with endocrine therapy | Chemotherapy; alpelisib with a PIK3CA mutation |
| HER2-positive | Docetaxel, trastuzumab and pertuzumab | Trastuzumab deruxtecan as preferred second line |
| Triple-negative | Chemotherapy, with pembrolizumab if PD-L1 is expressed | Sacituzumab govitecan as preferred option after taxanes |

Points on toxicity and risk:

- Treatment should not depend on age alone. Comorbidity counts, and in older patients a geriatric assessment may add important information. Haematological adverse events of CDK4/6 inhibitors may be more frequent in older patients.
- The three CDK4/6 inhibitors differ slightly in toxicity. A patient with a severe toxicity typical of one may switch to another.
- Before capecitabine, patients should be tested for variants that leave them without the enzyme dihydropyrimidine dehydrogenase.
- Alpelisib causes hyperglycaemia, rash and gastrointestinal toxicity early. About 70% of the patients needed a dose reduction or interruption and 25% stopped. Diabetes and the baseline HbA1c decide who is a candidate.
- Patients with two copies of UGT1A1*28 have a higher risk of severe neutropenia and diarrhoea with sacituzumab govitecan.
- Dose reduction and delay are effective ways to manage toxicity in advanced disease. Side effects should be assessed at each visit, and specialised nurses should screen for them proactively. Electronic patient-reported outcomes may help.

### Antibody–drug conjugates

Trastuzumab deruxtecan was compared with chemotherapy of the physician's choice in HER2-low disease in DESTINY-Breast04 ([Modi et al., 2022](references.md#modi-2022)). Safety data refer to 371 and 172 patients.

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

A pooled analysis of nine earlier studies with 1150 heavily pretreated patients, 44% of them with breast cancer, looked at this lung toxicity in detail ([Powell et al., 2022](references.md#powell-2022)):

- Incidence 15.4%, fatal in 2.2%.
- 77.4% of affected patients had grade 1 or 2 events.
- 87.0% had the first event within 12 months, median 5.4 months.
- For 53.2% of events the adjudication committee set an earlier onset than the investigators. The median difference was 43 days.
- Baseline factors linked to higher risk: age under 65, enrolment in Japan, dose above 6.4 mg/kg, oxygen saturation below 95%, moderate or severe renal impairment, lung comorbidities, and more than four years since first diagnosis.

The rate of this lung toxicity depends on the setting ([Swain et al., 2022](references.md#swain-2022)):

| Study | Patients | Any grade | Grade 1 or 2 | Grade 5 |
|---|---|---|---|---|
| DESTINY-Breast01 | 184, HER2-positive breast cancer after trastuzumab emtansine | 15.8% | 12.5% | 2.7% |
| DESTINY-Breast03 | 257, HER2-positive breast cancer, largely second line | 10.5% | 9.7% | 0 |
| DESTINY-Lung01 | 91, lung cancer, higher dose of 6.4 mg/kg | 26.4% | 19.8% | 2.2% |
| Eight pooled studies | 879, several tumours and doses | 15.8% | 12.3% | 2.4% |

- In 245 patients with breast cancer on the standard dose, 97% of the events started within 12 months. Patients who were still on treatment after 12 months had a risk of 1.8% of a new event, which speaks against a cumulative toxicity.
- In the eight pooled studies the committee set an earlier onset than the investigators for 71 of 148 events, with a median difference of 49 days.
- The dose counts: 17.0% with 6.4 mg/kg against 14.0% with 5.4 mg/kg in one analysis.
- With nivolumab added, 23.5% of 34 patients had lung toxicity.
- General risk factors of drug-related lung disease are named as well: treatment in Japan, age of 60 or older, existing lung disease, earlier radiation of the lung, renal impairment and smoking. The authors add that the factors found for trastuzumab deruxtecan come from heavily pretreated patients with different tumours and doses and do not justify withholding the drug.

The same paper gives guidance on monitoring and management, see section 7.

Sacituzumab govitecan was compared with single-agent chemotherapy in metastatic triple-negative disease in ASCENT ([Bardia et al., 2021](references.md#bardia-2021)). Treatment-related events of grade 3 or higher were neutropenia (51% versus 33%), leukopenia (10% versus 5%), diarrhoea (10% versus under 1%), anaemia (8% versus 5%) and febrile neutropenia (6% versus 2%). Only 5% stopped treatment because of adverse events, and no death was attributed to the drug. The paper notes that homozygosity for the UGT1A1*28 gene variant is associated with an increased risk of haematological toxicity.

A review of antibody–drug conjugates explains why these drugs are not as gentle as hoped ([Tarantino et al., 2023](references.md#tarantino-2023)). Most still cause toxicity that resembles their cytotoxic payload, plus effects on healthy tissue carrying the target, plus other poorly understood and sometimes life-threatening effects. The review names patient factors that change the risk:

- Impaired organ function at baseline. Impaired renal function and lower oxygen saturation are linked to lung toxicity from trastuzumab deruxtecan.
- Gene variants in drug metabolism. Patients with deleterious UGT1A1 variants had more adverse events with sacituzumab govitecan.
- Body weight and albumin, which change how the drugs are distributed and cleared.
- Ethnicity. Patients of Japanese ethnicity have a 20% higher mean serum concentration of trastuzumab deruxtecan.

For early detection the review points to wearable biosensors, pulse oximetry, home spirometry and cough monitors as possible tools for lung toxicity. It adds that costs and missing guidelines stand in the way.

### Immunotherapy plus chemotherapy

KEYNOTE-355 added pembrolizumab to chemotherapy in advanced triple-negative disease ([Cortes et al., 2022](references.md#cortes-2022)).

- Treatment-related events of grade 3 to 5 occurred in 68.1% with pembrolizumab and 66.9% with placebo. Most of the severe toxicity therefore comes from the chemotherapy.
- Immune-mediated events occurred in 26.5% versus 6.4%, of grade 3 or 4 in 5.3% versus 0%.
- The most common were hypothyroidism (15.8% versus 3.2%) and hyperthyroidism (4.3% versus 1.1%).

### CDK4/6 inhibition

In MONALEESA-2, ribociclib plus letrozole was compared with letrozole alone as first-line treatment of hormone receptor-positive disease, with a median follow-up of 6.6 years ([Hortobagyi et al., 2022](references.md#hortobagyi-2022)). Grade 3 or 4 events of special interest were:

| MONALEESA-2 | Ribociclib + letrozole | Placebo + letrozole |
|---|---|---|
| Neutropenia | 63.8% | 1.2% |
| Liver and bile duct toxicity | 14.4% | 4.8% |
| Prolonged QT interval | 4.5% | 2.1% |

Grade 3 lung inflammation occurred in 0.6% with ribociclib. The ESC guideline confirms that CDK4/6 inhibitors can prolong the QT interval, ribociclib in particular ([Lyon et al., 2022](references.md#lyon-2022)).

## 6. Toxicity across tumour types

### Immune-related adverse events

Checkpoint inhibitors cause a different kind of toxicity than chemotherapy. Any organ can be affected, with gut, skin, liver, hormone glands and lung in front ([Schneider et al., 2021](references.md#schneider-2021)). Incidence depends on the drug class: lower with anti-PD-1 or anti-PD-L1 than with anti-CTLA-4, and highest with combinations. Onset ranges from days to 26 weeks, with a median of about 40 days.

The ESMO guideline gives figures by organ ([Haanen et al., 2022](references.md#haanen-2022)):

| Organ | Incidence | Onset and risk factors |
|---|---|---|
| Skin | More than 50% (all grades), rarely severe | Rash usually within the first 6 weeks |
| Thyroid (hypothyroidism) | 6–9% with anti-PD-(L)1, 4% with anti-CTLA-4, 16% with combination | Mostly within 3 months, possible at any time |
| Pituitary | 9–10% with combination, 2–6% with anti-CTLA-4 | – |
| Diabetes | 1–2% | Median after 4.5 cycles, earlier with combination; HLA-DR4 may increase vulnerability |
| Adrenal insufficiency | 1–2% with single drug, 5–8% with combination | Median 4 months, range from days to over 12 months |
| Liver | 5–10% with single drug (1–2% grade 3), 25–30% with combination (15% grade 3) | – |
| Gut (diarrhoea / colitis) | About 10% / 1% with anti-PD-1, 35% / 10% with anti-CTLA-4, 32% / 15% with combination | Median 2–4 months with anti-PD-1, 1 month with anti-CTLA-4; about 40% of patients with inflammatory bowel disease have a flare |
| Lung | About 4% with anti-PD-1, 2% with anti-PD-L1, 10% with combination; high grade about 1% | Tobacco exposure, chronic lung disease and earlier radiotherapy may raise the risk |
| Kidney | About 1–4% | – |
| Heart (myocarditis) | Severe in under 1% | – |
| Blood | – | About 25 weeks with single drug, 12 weeks with combination; no clear predisposing factors reported |

For the heart, the ESC guideline adds that in the largest case series of 122 patients, myocarditis started after a median of 30 days and up to 50% of the patients died. High cardiovascular risk under checkpoint inhibitors is linked to dual checkpoint inhibition, combination with other cardiotoxic therapy, earlier non-cardiac immune-related events, and earlier cardiac dysfunction or cardiovascular disease ([Lyon et al., 2022](references.md#lyon-2022)).

The ASCO guideline gives management rules by grade ([Schneider et al., 2021](references.md#schneider-2021)):

- Grade 1: continue the checkpoint inhibitor with close monitoring. Exceptions are some neurological, haematological and cardiac toxicities.
- Grade 2: pause for most toxicities and consider restarting once symptoms are back to grade 1 or lower. Corticosteroids may be given.
- Grade 3: pause and start high-dose corticosteroids, tapered over at least four to six weeks. Some cases need other immunosuppressive drugs.
- Grade 4: stop permanently, except for endocrine toxicities that are controlled by hormone replacement.

The panel notes that high-quality evidence is scarce and that the recommendations rest on expert consensus.

### Peripheral neuropathy

Neuropathy matters in all three patient groups because oxaliplatin and taxanes are widely used. The ASCO guideline update states ([Loprinzi et al., 2020](references.md#loprinzi-2020)):

- Before treatment, clinicians should weigh risks and benefits in patients with existing neuropathy and with conditions that predispose to it, such as diabetes or a family or personal history of hereditary neuropathy.
- No drug is recommended to prevent chemotherapy-induced neuropathy.
- When neuropathy becomes intolerable or impairs function, clinicians should consider delaying, reducing, replacing or stopping chemotherapy.
- Duloxetine is the only drug with adequate evidence for established painful neuropathy, and its benefit is limited.

Since prevention does not work, early detection and dose adjustment are the only tools.

### Cardiovascular toxicity

The trial data show cardiovascular events under androgen deprivation, hypertension with abiraterone or darolutamide, and QT prolongation with ribociclib. The ESC guideline covers the whole field ([Lyon et al., 2022](references.md#lyon-2022)). Points that matter for our three groups:

- Fluoropyrimidines can cause myocardial ischaemia through coronary spasm and vessel injury. Chest pain and ECG changes typically occur at rest within days of drug administration. The risk rises markedly with existing coronary artery disease.
- HER2-targeted therapy can cause cardiac dysfunction. Management depends on the severity grades in section 2.
- Androgen deprivation is uncommonly associated with QT prolongation, ribociclib more often. Correctable risk factors for QT prolongation include other QT-prolonging drugs such as antiemetics, antibiotics and antidepressants, and low potassium, magnesium or calcium. Non-correctable factors include age over 65, female sex, a prolonged QT interval at baseline, impaired renal function, liver disease and existing heart disease.

### Venous thromboembolism

The ASCO guideline asks for a risk assessment at the start of systemic therapy and periodically after ([Key et al., 2020](references.md#key-2020)). Single factors such as the tumour site or a biomarker do not identify patients at high risk reliably. For outpatients with solid tumours it recommends the Khorana score:

| Characteristic | Points |
|---|---|
| Stomach or pancreatic cancer | 2 |
| Lung, gynaecological, bladder, testicular or renal cancer, or lymphoma | 1 |
| Platelet count of 350 × 10^9/l or more before chemotherapy | 1 |
| Haemoglobin below 10 g/dl, or use of red cell growth factors | 1 |
| Leukocyte count above 11 × 10^9/l before chemotherapy | 1 |
| Body mass index of 35 kg/m² or more | 1 |

A score of 3 or more is high risk, 1 or 2 intermediate, 0 low. Every patient with pancreatic cancer has at least 2 points.

- Routine prophylaxis for all outpatients is not recommended. Patients with a score of 2 or more who start a new systemic therapy may be offered apixaban, rivaroxaban or low-molecular-weight heparin, if they have no relevant bleeding risk and no drug interactions.
- Two trials tested this in patients with a score of 2 or more over 180 days. Apixaban lowered venous thromboembolism from 10.2% to 4.2% (hazard ratio 0.41) and raised major bleeding from 1.8% to 3.5%. Rivaroxaban lowered it from 8.8% to 6.0% (hazard ratio 0.66, not significant) and, while patients took the drug, from 6.4% to 2.6%; more than half of its patients had pancreatic or gastro-oesophageal cancer. Major bleeding rose by about one percentage point in both trials.
- In advanced pancreatic cancer two trials of low-molecular-weight heparin at higher doses lowered venous thromboembolism from 23% to 3.4% within 100 days and symptomatic events from 10.2% to 1.3% within three months, without more major bleeding.
- The score has limits. Two studies in pancreatic cancer and three in lung cancer found no association between the score and events. Other tools exist, among them one that uses only tumour type and D-dimer.
- For treatment, rivaroxaban and edoxaban carry a higher bleeding risk than low-molecular-weight heparin in gastrointestinal cancers.
- Patients know little about the warning signs, and the guideline asks the oncology team to teach them.

In PROfound, pulmonary embolism was more frequent with olaparib ([de Bono et al., 2020](references.md#de-bono-2020)).

### Febrile neutropenia

The joint guideline of ASCO and the Infectious Diseases Society of America requires the first dose of empirical antibiotics within one hour of triage ([Taplitz et al., 2018](references.md#taplitz-2018)). To decide who can be treated as an outpatient, it recommends clinical judgement together with clinical criteria or a validated tool such as the risk index of the Multinational Association of Supportive Care in Cancer (MASCC). This index grades the risk of complications once fever has occurred. It does not predict who will develop febrile neutropenia.

A model for this prediction exists ([Lyman et al., 2011](references.md#lyman-2011)). A prospective study followed 3760 patients who started a new chemotherapy in 115 US community practices, with breast, lung, colorectal or ovarian cancer or lymphoma.

- 30% had severe neutropenia (neutrophils below 0.5 × 10^9/l) or febrile neutropenia within four cycles, two thirds of them in the first cycle, when most patients get the full dose without prophylaxis.
- The model predicts such an event in the first cycle, which about 20% had. Its factors, with odds ratios: earlier chemotherapy 1.93, immunosuppressive medication 1.55, AST above 35 U/l 1.42, alkaline phosphatase above 120 U/l 1.47, bilirubin above 1 mg/dl 2.15, renal function 0.993 per ml/min, white cells 0.93 per 10^9/l, planned dose intensity of 85% or more 2.02, G-CSF from the first cycle 0.12, and the drug classes, from 1.8 for platinum to 18.6 for topoisomerase I inhibitors such as irinotecan. Age of 65 or older had 1.30 and was not significant: the authors state that comorbidity counts more than age.
- The area under the curve was 0.83 in the derivation sample and 0.81 in the validation sample. At a predicted risk of 10% the model found 90% of the patients with an event in the derivation sample and 85% in the validation sample; 34% to 36% of the patients above this risk had an event against 4% to 6% below.
- Over all cycles, about 20% of the patients at high risk and 5% of those at low risk had febrile neutropenia.
- Guidelines recommend G-CSF from the first cycle when the risk of febrile neutropenia reaches 20%. The model is meant to guide this choice for the single patient.

### Older patients

GAP70+ enrolled 718 patients aged 70 or older with incurable cancer and at least one impaired domain in a geriatric assessment, starting a new treatment with a high risk of toxicity ([Mohile et al., 2021](references.md#mohile-2021)). Mean age was 77 years, and patients had on average 4.5 impaired domains.

- With usual care, 71% had a toxic effect of grade 3 to 5 within three months.
- When oncologists received a summary of the assessment with management recommendations, the rate was 51% (relative risk 0.74).
- Severe non-haematological toxicity fell from 51.8% to 31.8%.
- Falls within three months fell from 21% to 12%.
- More patients in the intervention group started with reduced treatment intensity (48.7% versus 35.0%). Survival did not differ between the groups.

The ASCO guideline turned this into a strong recommendation ([Dale et al., 2023](references.md#dale-2023)): all patients aged 65 or older should have a geriatric assessment, and those with impairments should have their care plan adapted to it. The assessment should cover physical and cognitive function, emotional health, comorbid conditions, polypharmacy, nutrition and social support. The guideline offers the Practical Geriatric Assessment as one tool for this. It reviews nine trials:

- GAIN enrolled 605 patients aged 65 or older who started chemotherapy. A team acted on the assessment by fixed thresholds. Toxicity of grade 3 or higher fell from 60.6% to 50.5%. Emergency visits, hospital stays, dose changes and survival did not differ.
- More patients completed the planned chemotherapy in one trial of older patients with colorectal cancer (45% versus 28%), and unplanned hospital stays fell in another (rate ratio 0.60).
- Not all trials were positive. In one trial most patients had the assessment only after treatment had started, and neither quality of life nor toxicity improved. The assessment has to come before the treatment decision.
- The guideline ties actions to impairments. With impaired function or a high risk score: one drug instead of two, a dose reduced by 20% with escalation as tolerated, and toxicity checks every one or two weeks. With diabetes: avoid drugs that damage nerves if an equal option exists. With kidney or liver disease: adjust the dose.
- Few oncologists use a geriatric assessment in practice. In the surveys the guideline cites, about one in five did so routinely.

Two published scores predict severe toxicity in older patients. The guideline names both as tools: the CARG score with 11 items and three risk groups ([Hurria et al., 2011](references.md#hurria-2011); [Hurria et al., 2016](references.md#hurria-2016)) and the CRASH score ([Extermann et al., 2012](references.md#extermann-2012)). Only the CRASH study has been read in full:

- 518 patients aged 70 or older who started chemotherapy with 121 different regimens were followed for up to six months. 64% had severe toxicity: 32% haematological toxicity of grade 4 and 56% non-haematological toxicity of grade 3 or 4. The median time to the first event was 22 days, with quartiles at 9 and 51 days. 23% stopped treatment because of toxicity, and 1.7% died of complications.
- The score has two parts, because the two kinds of toxicity had different predictors. Haematological: diastolic blood pressure, instrumental activities of daily living, LDH and the toxicity of the regimen. Non-haematological: ECOG, the Mini-Mental Status, the Mini Nutritional Assessment and the toxicity of the regimen.
- The toxicity of the regimen comes from published trial rates and is part of the score. Docetaxel every three weeks and irinotecan get the highest of three levels, gemcitabine and weekly taxanes the lowest.
- From the lowest to the highest of four risk groups, haematological toxicity rose from 7% to 100% and non-haematological toxicity from 33% to 93%. For any severe toxicity the range was 50% to 79%: even the lowest group had a high risk.
- The c-statistic was 0.76 for haematological, 0.66 for non-haematological and 0.65 for any severe toxicity in the derivation sample, and 0.65, 0.62 and 0.64 in the validation sample.
- Age did not predict toxicity among these patients (odds ratio about 1.0 per year). Neither did the number of drugs taken, comorbidity or earlier chemotherapy. Haemoglobin (0.90 per g/dl) and albumin (0.74 per g/dl) pointed to less non-haematological toxicity with higher values, without statistical significance.
- The authors estimate that about one in three of these events would not need a dose change.

### Symptom monitoring by patients

PRO-TECT randomised 52 US community oncology practices with 1191 patients treated for metastatic cancer ([Basch et al., 2022](references.md#basch-2022)). Patients in the intervention group filled in a weekly symptom survey by web or phone for up to one year. Severe or worsening symptoms triggered an alert to the care team.

- After three months, physical function, symptom control and health-related quality of life were each about 2.5 points better on a 100-point scale than with usual care. The odds of a clinically meaningful benefit were higher by factors of 1.35, 1.50 and 1.41.
- Of 20 565 completed surveys, 33.9% triggered an alert, most often for pain, reduced performance status and diarrhoea.
- 59.1% of the alerts led to immediate action by a nurse, mostly a phone call.
- The primary endpoint, overall survival, was not yet reported in this paper.

The ESMO guideline recommends digital symptom monitoring with patient-reported outcome measures during systemic treatment, with the highest level of evidence ([Di Maio et al., 2022](references.md#di-maio-2022)). It names seven randomised trials, among them PRO-TECT, an earlier single-centre trial with 766 patients that found better quality of life, fewer emergency visits and longer survival, and a trial of 609 patients on oral therapy that found a higher dose intensity and fewer hospital stays. Its points for practice:

- A system should offer questions by web, handheld device or automated telephone, send reminders, and alert the team automatically when a symptom is severe or worsening. In one US study more than 35% of the patients preferred the telephone, more often older and less educated patients.
- A core set of symptoms for all patients is suggested: pain, nausea, vomiting, constipation, diarrhoea, breathlessness, insomnia, depression and physical function. For weekly reports, 10 to 20 questions have worked.
- Nurses should be the first to respond to an alert, with training and protected time. They assess by phone, coach self-management and pass the alert to a physician when needed. Mild symptoms can be answered by automated advice.
- Monitoring without clinical integration and without a named person to act is unlikely to help. A trial that fed reports back to the team without saying who should act found no effect.
- Less is known about how well patients keep reporting over time, older patients in particular, and about patients on oral therapy or radiotherapy alone.
- After the end of treatment, the guideline suggests symptom monitoring for patients with advanced lung cancer. In a French trial of 133 patients more patients had an unscheduled visit (58% versus 25%), more were in good condition when the tumour returned (76% versus 33%), and median survival was 7 months longer.

### Quality of life and costs

Two sources give numbers for the value of avoided toxicity and for the cost of monitoring.

Health state utilities for metastatic breast cancer were obtained from 100 members of the UK public ([Lloyd et al., 2006](references.md#lloyd-2006)). They rated descriptions of health states that each cover three weeks:

| Health state | Utility |
|---|---|
| Stable disease on treatment, no toxicity | 0.715 |
| Response to treatment | +0.075 |
| Progressive disease | −0.272 |
| Febrile neutropenia, with about five days in hospital | −0.150 |
| Stomatitis | −0.151 |
| Hand-foot syndrome | −0.116 |
| Fatigue | −0.115 |
| Hair loss | −0.114 |
| Diarrhoea and vomiting | −0.103 |

The toxicities are of grade 3 or 4, except hair loss. Progression costs more than twice as much utility as any severe toxicity. Older raters gave higher values. The values come from the public, not from patients, and the changes do not simply add up.

The French trial of symptom monitoring after lung cancer treatment was followed by a cost analysis from the view of the health insurance ([Lizée et al., 2019](references.md#lizee-2019)):

- The monitoring system was set at 200 euros per patient and month, for the software and the staff time to review the reports.
- The yearly cost of follow-up visits, imaging and transport was 941 euros with monitoring and 1304 euros without, because fewer scheduled scans were done. With the system it was 3266 euros.
- Monitoring cost 12 127 euros per life year gained and 20 912 euros per quality-adjusted life year. The analysis called 30 000 euros per quality-adjusted life year very cost-effective and 90 000 euros cost-effective. Monitoring stayed below the first threshold as long as the system cost less than 275 euros per month.
- This result rests on the survival gain of the trial, with 121 patients, and on monitoring for relapse after treatment, not for toxicity during treatment.

## 7. What guidelines ask for: risk assessment and monitoring

This section lists the risk tools and monitoring schedules that guidelines recommend today. They are the standard that a new risk model has to beat or to complement.

### Risk assessment before treatment

| Area | Tool or criteria | Source |
|---|---|---|
| Choice of pancreatic chemotherapy | ECOG performance status, Karnofsky score, bilirubin, comorbidity profile | [Conroy et al. (2023)](references.md#conroy-2023); [Sohal et al. (2020)](references.md#sohal-2020) |
| Patients aged 65 or older | Geriatric assessment of seven domains; G-8 as a short screening; CARG or CRASH score for the risk of chemotherapy toxicity | [Dale et al. (2023)](references.md#dale-2023) |
| Febrile neutropenia | Risk of 20% or more as threshold for G-CSF from the first cycle; a published model for the single patient | [Lyman et al. (2011)](references.md#lyman-2011) |
| Cardiovascular toxicity of HER2-targeted therapy and some other drug classes | HFA-ICOS risk assessment | [Lyon et al. (2022)](references.md#lyon-2022) |
| Cardiovascular risk under androgen deprivation, endocrine therapy for breast cancer and fluoropyrimidines | SCORE2 or SCORE2-OP, the general European scores for 10-year cardiovascular risk | [Lyon et al. (2022)](references.md#lyon-2022) |
| Checkpoint inhibitors | ECG, natriuretic peptides and troponin in all patients; echocardiography in high-risk patients | [Lyon et al. (2022)](references.md#lyon-2022) |
| QT prolongation | List of correctable and non-correctable risk factors | [Lyon et al. (2022)](references.md#lyon-2022) |
| Neuropathy | Existing neuropathy, diabetes, hereditary neuropathy | [Loprinzi et al. (2020)](references.md#loprinzi-2020) |
| Venous thromboembolism | Khorana score at the start of systemic therapy and periodically; prophylaxis may be offered from a score of 2 | [Key et al. (2020)](references.md#key-2020) |
| Trastuzumab deruxtecan | CT of the chest and interview before treatment; no current or earlier interstitial lung disease | [Swain et al. (2022)](references.md#swain-2022) |
| Androgen deprivation | Antagonists might be considered with cardiovascular disease or risk factors | [Tilki et al. (2024)](references.md#tilki-2024) |
| Capecitabine | Test for dihydropyrimidine dehydrogenase deficiency | [Gennari et al. (2021)](references.md#gennari-2021) |

The HFA-ICOS assessment sorts patients into low, moderate, high and very high risk. It uses earlier cardiovascular disease, cardiac imaging and biomarkers, age, cardiovascular risk factors such as hypertension, diabetes, kidney disease, smoking and obesity, and earlier cardiotoxic cancer treatment. Each factor counts as moderate (1 or 2 points), high or very high for a given drug class:

- Low risk: no risk factor or one moderate factor with 1 point.
- Moderate risk: moderate factors adding up to 2–4 points.
- High risk: moderate factors adding up to 5 points or more, or any high-risk factor.
- Very high risk: any very-high-risk factor.

The guideline is open about the limits. It states that only a limited number of retrospective risk scores have been published in patients with cancer, that most of them were developed for specific groups and cannot be transferred, and that the HFA-ICOS tools still need validation. For androgen deprivation it states that no dedicated cardiovascular toxicity risk calculator exists.

### Monitoring during treatment

| Therapy | Recommended monitoring | Source |
|---|---|---|
| Checkpoint inhibitors | Transaminases, alkaline phosphatase and bilirubin before every cycle; attention to creatinine relative to the patient's own baseline | [Haanen et al. (2022)](references.md#haanen-2022) |
| Checkpoint inhibitors | ECG and troponin before doses 2, 3 and 4, then every three doses (should be considered) | [Lyon et al. (2022)](references.md#lyon-2022) |
| HER2-targeted therapy | Echocardiography at baseline in all patients; in metastatic disease every 3 months in the first year, then every 6 months if there are no problems | [Lyon et al. (2022)](references.md#lyon-2022) |
| Androgen deprivation | Cardiovascular risk assessment every year; repeated ECGs in patients at risk of QT prolongation | [Lyon et al. (2022)](references.md#lyon-2022) |
| All chemotherapy with neuropathy risk | Assessment of neuropathy and of the need to adjust the dose | [Loprinzi et al. (2020)](references.md#loprinzi-2020) |
| Pancreatic chemotherapy | Evaluation every 8–12 weeks by clinical status, CA 19-9 and imaging | [Conroy et al. (2023)](references.md#conroy-2023) |
| Trastuzumab deruxtecan | Questions on breathlessness and cough at each visit, visits every 4–6 weeks, CT every 9–12 weeks; patients watch for new cough and lower exercise tolerance | [Swain et al. (2022)](references.md#swain-2022) |
| All systemic therapy | Weekly digital symptom reports with alerts to a nurse | [Di Maio et al. (2022)](references.md#di-maio-2022) |
| Older patients with impairments | Toxicity checks every one or two weeks | [Dale et al. (2023)](references.md#dale-2023) |
| Metastatic breast cancer | Side effects assessed at each visit, by clinical assessment, blood tests and patient-reported outcomes | [Gennari et al. (2021)](references.md#gennari-2021) |

The guidance on lung toxicity under trastuzumab deruxtecan is the most detailed ([Swain et al., 2022](references.md#swain-2022)):

- An expert panel proposed a rule for home measurements: a fall of the oxygen saturation at rest by 2 to 4 points over 1 to 3 days, or after exertion by 2 to 5 points over 1 to 7 days, should lead to an examination. The authors add that no data on pulse oximetry in this setting exist, and that it cannot replace CT, because grade 1 has no symptoms and shows only in imaging.
- In trials CT was done every 6 weeks. In practice it is done every 9 to 12 weeks.
- Grade 1: pause the drug until the lung has fully recovered and consider corticosteroids. Treatment resumes at the same dose if recovery takes up to 28 days, and one dose level lower if it takes longer. Changes in imaging can take 10 to 12 weeks to resolve.
- Grade 2 or higher: stop the drug for good and give corticosteroids for at least 14 days, then taper over at least four weeks. Grade 3 or 4 needs a hospital stay and high-dose corticosteroids.
- With other drugs a longer time between onset and stopping the drug was associated with worse outcomes. Whether early detection improves outcomes with trastuzumab deruxtecan has not been shown.

## 8. Candidates for risk models

This section is our derivation from sections 2 to 7. Each candidate names the event to predict, the patients and therapies it applies to, the predictors that the references support, the signals that could show the event early, and the current standard. Candidates 1 to 5 exist as baseline models in [risk-model/](../risk-model/); its README gives their formulas and their results on synthetic data.

Two kinds of model appear in every candidate:

- A **baseline model** estimates the risk before a therapy line starts. It supports the choice of regimen, dose and preventive measures.
- A **detection model** follows the patient during therapy and flags the start of a toxicity earlier than routine care.

### Overview

| # | Event | Pancreas | Prostate | Breast | Evidence for predictors | Existing tool | Risk model |
|---|---|---|---|---|---|---|---|
| 1 | Any severe toxicity in the first 3 months of a therapy line | all chemotherapy | docetaxel triplets, radioligand, PARP inhibitor | chemotherapy, antibody–drug conjugates | strong for older patients | geriatric assessment, CARG and CRASH score, performance status | yes |
| 2 | Lung toxicity (interstitial lung disease, pneumonitis) | – | – | trastuzumab deruxtecan, checkpoint inhibitors | good | none | yes |
| 3 | Severe neutropenia and febrile neutropenia | FOLFIRINOX, NALIRIFOX, gemcitabine + nab-paclitaxel | docetaxel | sacituzumab govitecan, ribociclib, chemotherapy | good | published model for the first cycle; MASCC index after fever | yes |
| 4 | Severe diarrhoea with dehydration and electrolyte loss | NALIRIFOX, FOLFIRINOX | – | sacituzumab govitecan, checkpoint inhibitors | weak | none | yes |
| 5 | Cardiovascular events | fluoropyrimidines | androgen deprivation, abiraterone, darolutamide | HER2-targeted therapy, ribociclib, checkpoint inhibitors | good | HFA-ICOS, SCORE2 | yes, for androgen deprivation |
| 6 | Immune-related adverse events | – | – | pembrolizumab | weak | none | no |
| 7 | Peripheral neuropathy | oxaliplatin, nab-paclitaxel | docetaxel | taxanes | weak | none | no |
| 8 | Venous thromboembolism | all, high baseline rate | olaparib | – | moderate | Khorana score | no |
| 9 | Anaemia and low platelets needing action | gemcitabine + nab-paclitaxel, FOLFIRINOX | olaparib, PARP inhibitor combinations, radioligand | antibody–drug conjugates | weak | none | no |
| 10 | Symptom deterioration needing action | all | all | all | good for the benefit of monitoring | alert thresholds | no |

### Candidate 1: any severe toxicity in the first three months

- **Event.** At least one adverse event of grade 3 to 5 within three months of starting a new therapy line. Secondary events: dose reduction, stopping treatment, falls.
- **Why.** It is the primary endpoint of GAP70+ and GAIN and the most comparable number across trials. Reference rates range from 51% to 87% in trials and reach 61% to 71% in older patients under usual care.
- **Baseline predictors.** Regimen and number of drugs, planned dose intensity, the seven geriatric assessment domains, ECOG and Karnofsky score, bilirubin in pancreatic cancer. The CRASH score adds instrumental activities of daily living, cognition, nutrition, LDH and diastolic blood pressure, and points to haemoglobin and albumin ([Extermann et al., 2012](references.md#extermann-2012)). Age adds little once these are known.
- **Time window.** Half of the first events fall into the first three weeks.
- **Current standard.** Geriatric assessment for patients aged 65 or older, with the CARG or CRASH score as tools ([Dale et al., 2023](references.md#dale-2023)); performance status and bilirubin rules in pancreatic cancer.
- **What a model adds.** A risk estimate instead of a list of impairments, also for patients under 65, and specific to the regimen.
- **What to expect.** The published score reaches a c-statistic of about 0.65 for this event, and even its lowest risk group has a risk of 50%. Separate models for haematological and non-haematological toxicity do better. A model for any severe toxicity is useful to choose patients for adapted management, not to rule toxicity out.
- **Risk model.** The regimen rate, shifted by age, ECOG, the number of impaired geriatric domains, haemoglobin, albumin and a reduced starting dose.

### Candidate 2: lung toxicity

- **Event.** Interstitial lung disease or pneumonitis of any grade, and of grade 2 or higher.
- **Applies to.** Trastuzumab deruxtecan in breast cancer (10–16%, fatal in up to 2.7%); checkpoint inhibitors (about 4% with anti-PD-1); ribociclib at a low rate.
- **Baseline predictors.** Oxygen saturation below 95%, moderate or severe renal impairment, lung comorbidities, dose, age under 65, Japanese origin, time since diagnosis ([Powell et al., 2022](references.md#powell-2022)). The rate is lower in earlier therapy lines ([Swain et al., 2022](references.md#swain-2022)). For checkpoint inhibitors: tobacco exposure, chronic lung disease, earlier chest radiotherapy ([Haanen et al., 2022](references.md#haanen-2022)).
- **Detection signals.** Oxygen saturation at rest and after exertion, heart and breathing rate, cough, home spirometry, reported breathlessness and exercise tolerance ([Tarantino et al., 2023](references.md#tarantino-2023); [Swain et al., 2022](references.md#swain-2022)). A first rule exists: a fall of the saturation at rest by 2 to 4 points over 1 to 3 days.
- **Time window.** Median onset after 129 days to 5.5 months, 87% to 97% within the first year, little risk after.
- **What a model adds.** The measured delay of 43 to 49 days between true and recognised onset is the clearest gap in current care among all candidates. An event caught at grade 1 allows treatment to resume; from grade 2 the drug is stopped for good.
- **Limit.** Grade 1 has no symptoms and shows only in imaging. Home measurements can find grade 2 early, not grade 1.
- **Risk model.** The published hazard ratios, set to the published rate, for trastuzumab deruxtecan; the risk up to any day and the remaining risk during follow-up.

### Candidate 3: severe neutropenia and febrile neutropenia

- **Event.** Neutropenia of grade 3 or 4, and febrile neutropenia, per cycle.
- **Reference rates.** Grade 3–4 neutropenia: 25% with gemcitabine plus nab-paclitaxel, 14% with NALIRIFOX, 34% with docetaxel triplets, 51% with sacituzumab govitecan, 64% with ribociclib. Febrile neutropenia: 7–8% with docetaxel triplets, 6% with sacituzumab govitecan, highest among pancreatic regimens with FOLFIRINOX.
- **Baseline predictors.** Regimen and planned dose intensity, G-CSF prophylaxis, earlier chemotherapy, AST, alkaline phosphatase and bilirubin, renal function, white cell count, immunosuppressive medication ([Lyman et al., 2011](references.md#lyman-2011)); UGT1A1 genotype for sacituzumab govitecan and irinotecan. Age counts little next to these.
- **Time window.** Two thirds of first events fall into the first cycle.
- **Detection signals.** Blood counts over the cycles, temperature, reported symptoms of infection.
- **Current standard.** G-CSF from the first cycle when the risk of febrile neutropenia of a regimen reaches 20%. The MASCC index grades risk only after fever has occurred ([Taplitz et al., 2018](references.md#taplitz-2018)).
- **What a model adds.** The risk of the single patient before the first cycle, so that G-CSF, dose and follow-up can be adapted. The published model shows that this is possible, with an area under the curve of 0.81 in validation. It was built in other tumours and regimens than ours.
- **Risk model.** The published patient factors with their odds ratios, set to the published rate of the regimen, for neutropenia of grade 3 or higher or febrile neutropenia within 90 days.

### Candidate 4: severe diarrhoea with dehydration and electrolyte loss

- **Event.** Diarrhoea of grade 3 or higher, and hypokalaemia of grade 3 or higher.
- **Reference rates.** Diarrhoea: 20% with NALIRIFOX, 17% with FOLFIRINOX, 16% with gemcitabine plus nab-paclitaxel in the pooled analysis, 10% with sacituzumab govitecan. Hypokalaemia: 15% with NALIRIFOX. Colitis under checkpoint inhibitors: about 1% with anti-PD-1.
- **Baseline predictors.** Regimen, UGT1A1 genotype, existing inflammatory bowel disease for checkpoint inhibitors, age and frailty, nutritional state. The references give no effect sizes.
- **Detection signals.** Number of stools per day relative to the patient's own baseline, which is how the CTCAE grade is defined; weight; potassium; reported nausea and intake. Diarrhoea is in the core set of symptoms for weekly reports ([Di Maio et al., 2022](references.md#di-maio-2022)).
- **Link to other candidates.** Low potassium is a correctable risk factor for QT prolongation (candidate 5).
- **Value.** Severe diarrhoea and vomiting lower the utility of a health state by 0.103 ([Lloyd et al., 2006](references.md#lloyd-2006)).
- **Risk model.** The published rate of the two pancreatic regimens and of sacituzumab govitecan, shifted by age, ECOG, albumin and the UGT1A1 genotype with assumed odds ratios. It has the weakest basis of the five models.

### Candidate 5: cardiovascular events

- **Events.** Major cardiovascular events under androgen deprivation; hypertension of grade 3 or higher with abiraterone or darolutamide; cardiac dysfunction under HER2-targeted therapy; QT prolongation with ribociclib or androgen deprivation; myocardial ischaemia with fluoropyrimidines; myocarditis with checkpoint inhibitors.
- **Baseline predictors.** Earlier cardiovascular events, type of androgen deprivation, age, hypertension, diabetes, kidney function, lipids, smoking, obesity, LVEF, troponin and natriuretic peptides, baseline QT interval, QT-prolonging co-medication, electrolytes. Whether the patient is under the care of a cardiologist and takes drugs for secondary prevention may count as much ([Lopes et al., 2021](references.md#lopes-2021)).
- **Detection signals.** Blood pressure at home, ECG, troponin, natriuretic peptides, LVEF and strain, reported chest pain and breathlessness.
- **Current standard.** HFA-ICOS and SCORE2 ([Lyon et al., 2022](references.md#lyon-2022)). An antagonist might be considered for men with cardiovascular disease ([Tilki et al., 2024](references.md#tilki-2024)).
- **What a model adds.** The guideline itself states that HFA-ICOS needs validation and that no risk calculator exists for androgen deprivation. Prostate cancer under androgen deprivation is the clearest open field.
- **Limit.** The two trials disagree on how much the type of androgen deprivation counts. HERO alone suggests a large effect in men with an earlier event (3.6% versus 17.8%, from 84 and 45 men); with PRONOUNCE it is small (18 of 359 versus 19 of 314).
- **Risk model.** Major cardiovascular events within one year under androgen deprivation: the rates of HERO, brought to cardiovascular events with PRONOUNCE, the effect of an earlier event pooled from both trials, and assumed effects of the classical risk factors. It also gives the risk of the same man on the other type of androgen deprivation.

### Candidate 6: immune-related adverse events

- **Event.** Any immune-related event of grade 2 or higher, and by organ.
- **Reference rates.** 26.5% of any grade and 5.3% of grade 3–4 with pembrolizumab plus chemotherapy in breast cancer, mostly thyroid.
- **Baseline predictors.** Drug class and combination, existing inflammatory bowel disease, lung disease and smoking for pneumonitis, earlier cardiovascular disease for myocarditis.
- **Detection signals.** Liver values before every cycle, creatinine relative to baseline, thyroid values, troponin and ECG in the first cycles, stool frequency, skin symptoms.
- **Time window.** Median about 40 days, organ-specific windows in section 6.
- **Limit.** The guidelines report few established predictors. A detection model based on laboratory trends and symptoms is better supported than a baseline model.

### Candidate 7: peripheral neuropathy

- **Event.** Neuropathy of grade 2 or higher, and neuropathy that forces a dose change.
- **Reference rates.** Grade 3–4: 6% with gemcitabine plus nab-paclitaxel, 3% with NALIRIFOX, 1–2% with docetaxel in PEACE-1.
- **Baseline predictors.** Existing neuropathy, diabetes, hereditary neuropathy, drug and cumulative dose.
- **Detection signals.** Patient-reported numbness, tingling and pain, function of hands and gait.
- **What a model adds.** No prevention exists, so the only gain is an earlier dose decision.

### Candidate 8: venous thromboembolism

- **Event.** Deep vein thrombosis or pulmonary embolism during therapy.
- **Reference rates.** Prevalence of about 25% in pancreatic cancer; pulmonary embolism in 4% with olaparib versus 1% in PROfound.
- **Reference rates.** Prevalence of about 25% in pancreatic cancer; 10% to 23% within about three months of chemotherapy for advanced pancreatic cancer without prophylaxis; 9% to 10% within six months with a Khorana score of 2 or more; pulmonary embolism in 4% with olaparib versus 1% in PROfound.
- **Baseline predictors.** The items of the Khorana score: tumour site, platelets, haemoglobin, leukocytes, body mass index. Further: earlier thrombosis, drug, D-dimer.
- **Current standard.** Khorana score at therapy start and periodically; prophylaxis may be offered from a score of 2 ([Key et al., 2020](references.md#key-2020)).
- **What a model adds.** Every patient with pancreatic cancer has a score of 2 or more, and the score did not separate patients within pancreatic cancer. A model for this group would have to find the patients whose risk outweighs one percentage point more major bleeding.
- **Action.** Prophylaxis lowers the risk by more than half, which makes this the candidate with the best proven action.

### Candidate 9: anaemia and low platelets needing action

- **Event.** Anaemia or thrombocytopenia of grade 3 or higher, transfusion, dose change.
- **Reference rates.** Anaemia of grade 3 or higher: 21% with olaparib, 46% with talazoparib plus enzalutamide, 17% with gemcitabine plus nab-paclitaxel, 12.9% with lutetium-177–PSMA-617. Blood transfusions in 18% to 39% with combinations of a PARP inhibitor and a hormonal drug. Thrombocytopenia of grade 3 or higher: 7.9% with lutetium-177–PSMA-617, 11.8% with FOLFIRINOX, 10.8% with gemcitabine plus nab-paclitaxel.
- **Baseline predictors.** Drug, earlier therapy lines, baseline blood counts. The references give no further patient factors.
- **Detection signals.** Blood count trend over cycles, reported fatigue and breathlessness.

### Candidate 10: symptom deterioration needing action

- **Event.** A symptom report that leads to an action by the care team, an unplanned visit or a hospital stay.
- **Why.** In PRO-TECT one in three weekly surveys triggered an alert under fixed thresholds, and six in ten alerts led to action. A model that ranks reports by the risk of a severe event could reduce the alert load and focus on the patients who need help.
- **Inputs.** Weekly patient-reported symptoms and performance status as time series, regimen and cycle day, baseline risk from candidates 1 to 9.
- **Frame.** The guideline sets the frame such a model has to fit into: 10 to 20 questions per week, nurses as first responders with protected time, automated advice for mild symptoms ([Di Maio et al., 2022](references.md#di-maio-2022)). The workload of the nurses is the scarce resource.

### Variables for the synthetic data engine

The candidates need these groups of variables:

| Group | Variables |
|---|---|
| Patient | Age, sex, weight, ethnicity, ECOG and Karnofsky score |
| Geriatric domains | Physical function, cognition, emotional health, comorbidity, polypharmacy, nutrition, social support, falls |
| Organ function | Renal function, bilirubin, AST and alkaline phosphatase, LDH, oxygen saturation, LVEF, baseline QT interval, blood counts with white cells, albumin, diastolic blood pressure |
| Comorbidity | Cardiovascular disease and earlier events, hypertension, diabetes, lung disease, inflammatory bowel disease, neuropathy, earlier thrombosis, smoking, obesity |
| Genetics | UGT1A1 genotype, germline BRCA status |
| Tumour and therapy | Tumour type, metastatic sites, therapy line, regimen, dose, cycle, G-CSF, co-medication including immunosuppressive drugs, drugs for cardiovascular prevention and thromboprophylaxis |
| Course | Blood counts, electrolytes, liver values, creatinine, thyroid values, troponin, natriuretic peptides, ECG, blood pressure, oxygen saturation, weight, temperature |
| Patient reports | Weekly symptoms and performance status |
| Outcomes | Adverse events by type, grade and onset day; dose reduction, interruption, stop; hospital stay; death; quality of life by health state |

### The five risk models

Candidates 1 to 5 are implemented. They were chosen for these reasons:

- Candidate 1 applies to all three patient groups, has the largest set of reference rates, two randomised trials showing that acting on the risk reduces toxicity, and a published score to compare with.
- Candidate 2 has well described risk factors, a clear time window, simple signals that can be measured at home, a measured delay in current care and a first rule for home measurements.
- Candidate 3 has a published and validated model with effect sizes for every factor, and an action with a known effect, G-CSF.
- Candidate 4 completes the picture for the pancreatic regimens, where diarrhoea decides between NALIRIFOX and gemcitabine plus nab-paclitaxel, and for sacituzumab govitecan. Its predictors have no published effect sizes.
- Candidate 5 in prostate cancer under androgen deprivation fills a gap that the guideline names itself: no risk tool exists. Two trials give the event rates by type of androgen deprivation and by earlier cardiovascular events.

All five are baseline models. The next step is detection during therapy, first for candidate 2. Among the candidates without a model, venous thromboembolism (candidate 8) has the best basis: a score in guidelines, rates with and without prophylaxis, and all its items in the baseline record.

## 9. Topics not covered by the current references

- Machine learning models for toxicity and their performance, and published models beyond the two read here. The CARG score is known from its abstracts only.
- Evidence for wearables and home measurements. The guidance on trastuzumab deruxtecan states that no data on pulse oximetry at home exist.
- Pharmacogenetics of fluoropyrimidines and effect sizes for UGT1A1.
- Toxicity rates in routine care compared with trials.
- Effect sizes for the risk factors of severe diarrhoea.
- The scores that the ESC guideline recommends for cardiovascular risk, SCORE2 and SCORE2-OP, and a meta-analysis of antagonists against agonists.
- Toxicity of cabazitaxel in prostate cancer and of second-line chemotherapy in pancreatic cancer.
- Unit costs of hospital stays and of the treatment of toxicity, and quality-of-life weights for pancreatic and prostate cancer.
- The guideline on fever and neutropenia ([Taplitz et al., 2018](references.md#taplitz-2018)) and the trial eRAPID ([Absolom et al., 2021](references.md#absolom-2021)), of which only the abstracts were read.
