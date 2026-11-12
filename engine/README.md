# engine

Generator for synthetic patient data. It produces patients at the start of a systemic therapy line and their toxicity outcomes, in the format of the central [schema](../schema/).

The engine covers the first two risk model candidates of the [toxicity report](../background/toxicity-report.md):

- Candidate 1: any adverse event of grade 3 to 5 within 90 days of therapy start.
- Candidate 2: interstitial lung disease or pneumonitis.

## Run

```bash
python3 engine/generate.py --n 5000 --seed 1 --out engine/output
```

This writes `baseline.csv`, `outcome.csv` and `metadata.json` to the output folder and prints the event rates per regimen. The same seed gives the same data. The output folder is not under version control.

```bash
python3 -m unittest discover engine/tests
```

The engine needs Python 3 and no further packages.

## Files

| File | Content |
|---|---|
| `generate.py` | Command line entry: generates, checks against the schema, writes the files |
| `population.py` | Baseline characteristics of a patient |
| `toxicity.py` | The two toxicity models |
| `config/regimens.json` | Regimens with reference rates and their sources |
| `config/parameters.json` | All other parameters, each marked as literature value or assumption |
| `tests/test_engine.py` | Tests |

## Regimens

Each patient gets one of ten regimens with equal probability. The tumour type follows from the regimen.

| Regimen | Tumour | Severe toxicity rate | Lung toxicity rate | Source |
|---|---|---|---|---|
| `nalirifox` | pancreas | 87% | – | Wainberg et al. (2023) |
| `gemcitabine_nab_paclitaxel` | pancreas | 86% | – | Wainberg et al. (2023) |
| `adt_docetaxel` | prostate | 63.5% | – | Smith et al. (2022) |
| `adt_docetaxel_abiraterone` | prostate | 63% | – | Fizazi et al. (2022) |
| `adt_docetaxel_darolutamide` | prostate | 66.1% | – | Smith et al. (2022) |
| `lu_psma_617` | prostate | 52.7% | – | Sartor et al. (2021) |
| `olaparib` | prostate | 51% | – | de Bono et al. (2020) |
| `trastuzumab_deruxtecan` | breast | 52.6% | 12.1% | Modi et al. (2022) |
| `chemotherapy_single_agent` | breast | 67.4% | 0.6% | Modi et al. (2022) |
| `pembrolizumab_chemotherapy` | breast | 68.1% | – | Cortes et al. (2022) |

Where the sources give no lung toxicity rate for a regimen, the engine generates no lung toxicity.

## Model for severe toxicity (candidate 1)

A logistic model. The regimen rate is the risk of a reference patient: 65 years old, ECOG 0 or 1, no impaired geriatric domain. Three factors shift the risk:

| Factor | Odds ratio | Basis |
|---|---|---|
| Age, per 10 years | 1.2 | assumption |
| ECOG 2 or higher | 2.0 | assumption |
| Each impaired geriatric domain | 1.1 | assumption |

The odds ratios for age and geriatric domains are set so that a patient like the average GAP70+ participant (77 years, 4.5 impaired domains, regimen rate 60%) has a risk of about 74%. The usual-care arm of that trial had 71% (Mohile et al., 2021).

The day of the first event follows an exponential distribution with a mean of 30 days, cut at day 90. This is an assumption.

## Model for lung toxicity (candidate 2)

A proportional hazards model. The risk of a patient is `1 − (1 − r)^HR`, where `r` is the risk of a patient without risk factors and `HR` is the product of the hazard ratios that apply:

| Risk factor | Hazard ratio |
|---|---|
| Age below 65 | 1.56 |
| Lung comorbidity | 1.75 |
| Renal function, mild decrease | 1.24 |
| Renal function, moderate or severe decrease | 2.73 |
| More than 4 years since diagnosis | 1.82 |
| Oxygen saturation below 95% | 2.14 |

The hazard ratios come from the multivariable model of Powell et al. (2022). The engine sets `r` per regimen so that the mean risk of the generated patients equals the rate in the regimen table. The value is stored in `metadata.json`.

- Onset day: log-normal with a median of 129 days (Modi et al., 2022). The spread is set so that 87% of events start within 12 months (Powell et al., 2022). Events after day 730 are not generated.
- Grade: 29% grade 1, 53% grade 2, 11% grade 3, 7% grade 5, as in Modi et al. (2022).

## Baseline characteristics

| Field | How it is drawn | Basis |
|---|---|---|
| Age | Normal distribution, mean 65 (pancreas), 69 (prostate), 57 (breast), limited to 30–90 | assumption |
| Sex | Male for prostate, female for breast, 55% male for pancreas | assumption |
| ECOG | 40% ECOG 0, 45% ECOG 1, 15% ECOG 2 | assumption |
| Impaired geriatric domains | From age 65: each of 7 domains impaired with a probability of 15%, rising by 1 point per year of age. Not assessed below 65. | assumption |
| Renal function | 42% normal, 41% mild decrease, 17% moderate or severe decrease | Powell et al. (2022) |
| Oxygen saturation | Normal distribution, mean 97.5, about 5% below 95% | Powell et al. (2022) for the share below 95% |
| Lung comorbidity | 7% | Powell et al. (2022) |
| Years since diagnosis | Log-normal, median 0.4 (pancreas), 3.0 (prostate), 3.3 (breast) | breast: about 39% above 4 years as in Powell et al. (2022); others assumption |

All baseline fields are drawn independently of each other, apart from the link between age and geriatric domains.

## Simplifications

- The severe toxicity rates in the trials refer to the whole treatment period. The engine uses them as 90-day risks.
- The trial populations differ in age and fitness from the reference patient of the model. The generated rates per regimen are therefore somewhat above the trial rates for regimens given to older patients.
- The effects of age, ECOG and geriatric domains on severe toxicity are assumptions, not estimates from data.
- Two risk factors for lung toxicity in Powell et al. (2022) are not modelled: dose above the standard dose and enrolment in Japan. All patients are treated as receiving the standard dose.
- The risk factors for lung toxicity were found for trastuzumab deruxtecan. The engine applies them to single-agent chemotherapy as well.
- There are no measurements during therapy yet, so the data support baseline models but not detection models.
