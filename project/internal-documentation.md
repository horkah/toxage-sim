# Internal documentation

Technical and organisational details that go beyond the public [README](../README.md). All documentation in this repository describes the current status only. The history is in the git log.

## Working rules

- Tasks on the command line are recipes of the `justfile` in the repository root; `just` lists them. A new recurring command becomes a recipe there.
- The Python environment is managed by uv. `pyproject.toml` names the packages, `uv.lock` pins them, and the Docker image installs from the same lock file. Engine, risk models and schema need only the standard library; the packages are for the app.
- Work happens on `main`. Every change is committed and pushed unless a prompt says otherwise.
- Every prompt is logged in [prompting.log](prompting.log) with date-time, selected model, attachments and the prompt text. Nothing else goes into the log.
- [initial-prompt.txt](initial-prompt.txt) is the start prompt of the project.

## Folders

| Folder | Purpose | Status |
|---|---|---|
| `background/` | Literature, report, concepts | 37 references, report with ten risk model candidates, intervention model, 20 PDFs |
| `schema/` | Central data schema | scenario, baseline, observation, event, alert and outcome table (version 0.4.0), risk_score table (version 0.2.0), Python loader, validator, CSV reader and writer |
| `engine/` | Synthetic data generator | weekly microsimulation until death or ten years, five subgroups, ten regimens, three event categories modelled in detail (severe toxicity, lung toxicity, cardiovascular events), seven intervention scenarios, calibration, tests |
| `risk-model/` | Toxicity risk model | common interface, baseline models for candidates 1, 2 and 5, fitting, evaluation, tests, list of extensions |
| `app/` | Inspection app | Django app with disclaimer, explorer (risk, characteristics, course over time, interventions), data sets, parameters, schema and documents, tutorial and demo; Docker image; tests |
| `project/` | Project management, internal documentation | prompt log, start prompt, this file |

## Literature

### Selection

The first 20 references cover the three patient groups and the main therapy classes: combination chemotherapy, taxanes, androgen deprivation and androgen receptor inhibitors, PARP inhibitors, radioligand therapy, antibody–drug conjugates, checkpoint inhibitors, and CDK4/6 inhibitors. They are ten phase 3 trials, two cluster-randomised trials, one pooled safety analysis, one meta-analysis, one review and five guidelines, from The New England Journal of Medicine, The Lancet, JAMA, JAMA Network Open, Journal of Clinical Oncology, Annals of Oncology, European Heart Journal, Nature Reviews Clinical Oncology and ESMO Open.

Eight further guidelines were added for the derivation of risk models:

- Treatment guidelines that define the therapy settings: ASCO on metastatic pancreatic cancer, ASCO and EAU on advanced prostate cancer, ESMO on metastatic breast cancer.
- Guidelines on risk assessment and monitoring: ASCO on older patients, ASCO on venous thromboembolism, ASCO and IDSA on febrile neutropenia, ESMO on patient-reported outcome measures.

The febrile neutropenia guideline is from 2018 and so older than the six-year window of the first selection.

Section 9 of the report lists the topics that the references do not cover.

### How references are checked

- Every reference is looked up in PubMed through the NCBI E-utilities. Title, authors, journal, year, volume, issue, pages and DOI come from the PubMed record.
- Author names are compared with Crossref, which keeps accents that PubMed drops.
- A reference only enters `references.md` after this check.

### Sources for the report

The report uses the PDFs in `background/papers/`, converted to text with `pdftotext`. For references without a PDF it uses the accepted manuscript from the PubMed Central article datasets where one exists, and the PubMed abstract otherwise. The table "Full texts" in `background/references.md` shows the source for each reference. Numbers in the report are taken from these texts only.

Sections 2 to 7 of the report state what the sources say. Section 8, the risk model candidates, is our own derivation and is marked as such.

Limits of the current reading:

- The two longest guidelines (Lyon 2022 with 133 pages, Schneider 2021 with 64 pages) were read in selected sections.
- The online supplements of the papers are not in the repository. This affects Haanen 2022 most, where baseline screening and details on several organs are in the supplement.
- In the text extracted from Conroy 2023, the signs "≥" and "≤" are lost. The thresholds for Karnofsky score and bilirubin in section 3 of the report follow from the wording of the neighbouring recommendations.

### PDFs

All 20 PDFs of the first selection are in `background/papers/`. File names follow the pattern `<first author>-<year>-<publisher file name>.pdf`. The file of Haanen 2022 is spelled `Haanan-…` .

The PDFs of the eight added guidelines are missing: Dale 2023, Di Maio 2022, Gennari 2021, Key 2020, Sohal 2020, Taplitz 2018, Tilki 2024, Virgo 2021.

Automated download is limited because the publisher websites and the Europe PMC website block scripted access. The only automated source for PDFs is the PubMed Central article dataset on AWS (`pmc-oa-opendata`), which holds PDFs only for articles with an open licence.

### Licences of the stored PDFs

- Powell 2022 and Nichetti 2024 are open access under CC BY and may be redistributed.
- All other PDFs are publisher versions under publisher copyright, obtained through the university account or free to read on the journal website.

The copyrighted PDFs must not be in the repository when it becomes public. Before publication, `background/papers/` has to be reduced to openly licensed files, and the PDFs have to be removed from the git history as well.

## Schema and engine

- The schema in `schema/` is the single source for field names, types and allowed values. Code in other folders reads it from there and does not repeat field lists. Reading and writing CSV files also goes through `schema/toxage_schema.py`. Rules for extending it are in `schema/README.md`.
- The engine is plain Python 3 without further packages. `engine/README.md` describes the model variables, the covariate mechanisms, the hazard model, the basis of every parameter group, the simplifications and the ideas for later extensions. The parameters themselves are in `engine/config/`.
- After every change of the model or its parameters, `python3 engine/calibrate.py` has to be run. It takes about one minute and rewrites `engine/config/calibration.json`, which is under version control.
- Generated data go to `engine/output/`, which is not under version control. Data are reproduced from the seed. 3000 patients under seven scenarios give about 770 000 observation records and take about 30 seconds; checking them against the schema and writing the files takes longer.
- Scenarios must stay comparable patient by patient. Every random decision in `course.py`, `interventions.py` and `measurements.py` therefore goes through `draws.py` with a purpose and a week, never through a shared random generator. A new decision gets a new purpose name.
- Tests run with `python3 -m unittest discover engine/tests`.
- The three tumour types always get equal numbers of patients. If the number of patients is not a multiple of three, the first tumour types get one patient more.

## Risk model

- The risk model has its own configuration in `risk-model/config/models.json`. It does not import the engine and does not read its parameters. Both draw on the same literature.
- `risk-model/toxage_risk.py` is the interface for the app: one class per model with risk, reference risk and factors. The calculations are in `models.py`. A new model is added in both places and then appears in the app without changes there.
- The engine generates outcomes with a richer process than the risk models assume. The evaluation in `risk-model/README.md` therefore shows how well simple baseline models do on these data. For lung toxicity and for cardiovascular events, engine and risk model use the same published hazard ratios; for cardiovascular events the engine adds factors the model does not know.
- A risk category that is to be as complete as lung toxicity and cardiovascular events touches every part: fields in the schema, rate and risk factors in the engine configuration, the event with its course in `course.py`, signals in `measurements.py`, a monitoring component and a scenario in `interventions.json`, an outcome field for the time window of the model, the model with scoring, fitting and evaluation, and a chart by grade in `app/explorer/timeline.py`.
- The risk model is plain Python 3 without further packages, like the engine. Refitting uses its own binomial regression in `glm.py`.
- Scores go to `risk-model/output/`, which is not under version control.
- Tests run with `python3 -m unittest discover risk-model/tests`. They generate data with the engine, so a change of the engine can make them fail.
- Possible extensions are collected in `risk-model/EXTENSIONS.md`. Items are removed there when done.

## App

- The app needs Django, and gunicorn in the container (`pyproject.toml`). Pages are Django templates, charts are drawn by a web component in plain JavaScript.
- `Dockerfile` and `docker-compose.yml` are in the repository root, because the image needs engine, risk model, schema and documents next to the app. The image was written and its start command tested outside a container; the image build itself has not been run yet.
- The server must run as one process. Data sets are generated in a thread of that process, and the rows of a scenario are kept in its memory.
- Model parameters: the JSON files of the repository are the defaults. The app stores only changed values, per file, in the table Setting. `params.engine_config()` gives the engine its configuration; the engine itself never reads the database.
- A new document for the app is one line in `explorer/docs.py`. A new parameter file is one entry in `explorer/params.py`.
- Data sets are generated on the page "Data" or with `python3 manage.py load_cohort`. In development the database is `app/db.sqlite3`, in the container `/data/db.sqlite3`; neither is under version control. Each patient has one course per scenario with outcome, events, alerts and weekly observations.
- The storage model has one initial migration. As long as no installation has to be kept, a change of the models replaces this migration; afterwards changes get migrations of their own.
- The rows of a scenario are kept in memory after first use. `cohort.clear_cache()` empties this store; `store.generate` calls it.
- Filters and the charts per patient characteristic are built from the schema, the status bar and risk filters from the registered risk models.
- The steps of tutorial and demo are in `explorer/static/explorer/tour-steps.js`. A new function of the app gets a step there. A step that changes data or parameters is marked with `changes`, and the demo must undo it in a later step; the server restores the state at the end in any case.
- Tests run in `app/` with `python3 manage.py test explorer` and `node --test "explorer/tests/*.test.mjs"`.

## Cloud environment

Sessions for this repository run in the cloud environment `toxage-sim`. Its network allows the package registries and these hosts:

- Literature services: `pubmed.ncbi.nlm.nih.gov`, `eutils.ncbi.nlm.nih.gov`, `pmc.ncbi.nlm.nih.gov`, `www.ebi.ac.uk`, `europepmc.org`, `api.crossref.org`, `doi.org`
- Publishers: `www.annalsofoncology.org`, `ascopubs.org`, `academic.oup.com`, `jamanetwork.com`, `www.esmoopen.com`, `www.nejm.org`, `www.thelancet.com`, `www.nature.com`

The literature services work from scripts. The publisher hosts answer scripted requests with a bot check and are of no use for downloads.

## Open points

- Add the PDFs of the eight added guidelines to `background/papers/` and read the six that are not yet covered by a full text.
- Extend the literature to the topics in section 9 of the report, first of all published prediction models and the evidence for home measurements.
- Replace the assumed parameters of the engine by literature values where possible, see the table "Basis of the parameters" in `engine/README.md`.
- Search the literature for the cardiovascular model: SCORE2 coefficients in place of the assumed hazard ratios, a second trial next to HERO, and data on warning signs before a cardiovascular event.
- Search the literature for unit costs, quality-of-life weights, hospital stays by event grade, participation rates and the effect of early treatment. The intervention model uses assumptions and placeholders for them.
- Replace the stand-ins for prediction and detection in the engine by the real risk models.
- Pick the next extensions of the engine from the list "Ideas for later" in `engine/README.md`.
- Extend the risk models, see `risk-model/EXTENSIONS.md`. The detection models for lung toxicity (2.1) and for cardiovascular events (5.1) can be built on the weekly observations.
- Build and run the Docker image once and check it on the target host.
- Decide whether the app needs a login before it is reachable outside a trusted network.
- Decide on a licence for the repository before it becomes public. The disclaimer of the app holds preliminary terms of use.
