# toxage-sim

Cancer therapies save and prolong lives, but they often harm the patient as well. In clinical trials of chemotherapy, immunotherapy and other systemic treatments for advanced cancer, more than half of the patients have at least one severe side effect. Some of them are noticed late.

The goal of this project is to predict toxicity from cancer therapy, or to detect it early, better than current clinical care does.

## Patient groups

We start with three groups of patients with advanced disease who receive systemic therapy with a relevant risk of toxicity:

- pancreatic cancer
- prostate cancer
- breast cancer

## Approach

The project works with synthetic data. A data engine generates patients, therapies and toxicity courses based on published knowledge. A risk model is built and tested on these data. An app makes data and risk scores visible, for a single patient, for a population, and for a patient compared with a reference population.

## Repository

| Folder | Content |
|---|---|
| [background/](background/) | Scientific background: literature list and a report on therapy toxicity |
| [schema/](schema/) | Central data schema, shared by engine, risk model and app |
| [engine/](engine/) | Generator for synthetic patient data |
| [risk-model/](risk-model/) | Toxicity risk models with a common interface |
| [app/](app/) | App to inspect data and risk scores |
| [project/](project/) | Project management and internal documentation |

## Getting started

The project uses [uv](https://docs.astral.sh/uv/) for the Python environment and [just](https://just.systems/) for its tasks.

```bash
just setup
```

```bash
just test
```

```bash
just serve
```

`just` alone lists all tasks: tests, generating and calibrating with the engine, scoring and evaluating with the risk models, running the app, and Docker. `just docker-up` starts the app in a container instead.

## Status

The scientific background is in place:

- [background/references.md](background/references.md) lists 28 sources: 20 papers from high-impact journals on toxicity in the three patient groups and 8 further clinical guidelines from the US and Europe.
- [background/toxicity-report.md](background/toxicity-report.md) summarises their findings: how often severe toxicity occurs with which therapy, when it starts, who is at risk, and what guidelines ask for in risk assessment and monitoring.
- The report derives ten candidates for risk models, from a general model for severe toxicity in the first three months of a therapy line to specific models for lung toxicity, neutropenia, diarrhoea, cardiovascular events and others.

The central data schema and the data engine exist:

- [schema/](schema/) defines seven tables: scenarios, baseline data, weekly observations, adverse events, alerts and an outcome summary per patient and scenario, and the risk scores.
- [engine/](engine/) is a microsimulation. It follows each synthetic patient week by week until death or for ten years: adverse events, dose changes, end of therapy and death, together with blood values, oxygen saturation, blood pressure and reported symptoms. The three tumour types have equal numbers of patients, with subgroups and ten regimens inside. Event rates follow the published trials.
- Three kinds of events are modelled in detail: any severe toxicity, lung toxicity under trastuzumab deruxtecan with its late recognition, and major cardiovascular events under androgen deprivation for prostate cancer with their warning phase.
- The engine simulates the same patients under seven intervention scenarios: usual care, a risk-adapted start of therapy, symptom monitoring, lung monitoring, cardiovascular monitoring, all four combined, and perfect detection as upper limit. Each patient has fixed random numbers, so a patient differs between scenarios only where an intervention acts. Participation, dropout, alerts, early treatment, hospital stays, costs and quality-adjusted life years are part of the model.

A first version of the risk models exists:

- [risk-model/](risk-model/) gives all risk models one interface and has baseline models for candidates 1, 2 and 5: a logistic model for any severe toxicity within 90 days, a proportional hazards model for lung toxicity under trastuzumab deruxtecan and single-agent chemotherapy, and a proportional hazards model for major cardiovascular events in the first year under androgen deprivation, built on the HERO trial. Coefficients come from the literature or are marked as assumptions. Each patient gets a risk, the published rate of the regimen for comparison, a risk category, and the factors behind the risk.
- On the synthetic data, the model for severe toxicity ranks patients only slightly better than the published rate of the regimen alone, and the models for lung toxicity and for cardiovascular events clearly better. All data are synthetic, so this says nothing about real patients. [risk-model/EXTENSIONS.md](risk-model/EXTENSIONS.md) lists the next steps, among them the detection model for lung toxicity.

[background/intervention-model.md](background/intervention-model.md) describes the intervention model: the chain from the offer of an intervention to its effect on health and costs, and what the engine implements of it. The effect sizes, costs and quality-of-life weights are assumptions or placeholders, so the scenario results show how the model behaves, not what an intervention achieves in patients.

A first app exists:

- [app/](app/) is a web app that shows the cohort and a single patient in relation to it: risk distribution, calibration, time to event by risk group, and observed and predicted rates by patient characteristic. Filters cover every field of the baseline and outcome records and every risk model.
- The app shows the course over time, for the cohort and for a single patient under two scenarios, and compares all scenarios side by side.
- Data sets are generated, inspected and deleted in the app. All model parameters can be changed there and reset to the defaults of the repository. The schema and the documents of the project can be read in the app.
- A tutorial and a demo lead through all functions of the app. In the tutorial the user does each step herself; the demo runs on its own at an adjustable speed and leaves the app as it was.
- `docker compose up -d --build` starts the app in a container, with the data in a volume. See [app/README.md](app/README.md).

## Note

This is a research project. It uses synthetic data only and is not a medical device. Nothing in this repository is medical advice.
