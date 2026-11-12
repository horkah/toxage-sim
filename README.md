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
| [risk-model/](risk-model/) | Toxicity risk model |
| [app/](app/) | App to inspect data and risk scores |
| [project/](project/) | Project management and internal documentation |

## Status

The scientific background is in place:

- [background/references.md](background/references.md) lists 28 sources: 20 papers from high-impact journals on toxicity in the three patient groups and 8 further clinical guidelines from the US and Europe.
- [background/toxicity-report.md](background/toxicity-report.md) summarises their findings: how often severe toxicity occurs with which therapy, when it starts, who is at risk, and what guidelines ask for in risk assessment and monitoring.
- The report derives ten candidates for risk models, from a general model for severe toxicity in the first three months of a therapy line to specific models for lung toxicity, neutropenia, diarrhoea, cardiovascular events and others.

The central data schema and the data engine exist:

- [schema/](schema/) defines five tables: baseline data, weekly observations, adverse events and an outcome summary per patient, and the risk scores.
- [engine/](engine/) is a microsimulation. It follows each synthetic patient week by week for one year: adverse events, dose changes, end of therapy and death, together with blood values, oxygen saturation and reported symptoms. The three tumour types have equal numbers of patients, with subgroups and ten regimens inside. Event rates follow the published trials.

A first version of the risk models exists:

- [risk-model/](risk-model/) has baseline models for candidates 1 and 2: a logistic model for any severe toxicity within 90 days and a proportional hazards model for lung toxicity under trastuzumab deruxtecan and single-agent chemotherapy. Coefficients come from the literature or are marked as assumptions. Each patient gets a risk, the published rate of the regimen for comparison, a risk category, and the factors behind the risk.
- On the synthetic data, the model for severe toxicity ranks patients only slightly better than the published rate of the regimen alone, and the model for lung toxicity clearly better. All data are synthetic, so this says nothing about real patients. [risk-model/EXTENSIONS.md](risk-model/EXTENSIONS.md) lists the next steps, among them the detection model for lung toxicity.

A concept for interventions exists: [background/intervention-model.md](background/intervention-model.md) describes how early detection and prediction, participation, the actions of the care team and their effects on health and costs can be simulated, and how the same cohort can be run through several scenarios for comparison. It is not implemented yet.

The app has no code yet.

## Note

This is a research project. It uses synthetic data only and is not a medical device. Nothing in this repository is medical advice.
