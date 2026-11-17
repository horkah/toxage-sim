# Internal documentation

Technical and organisational details that go beyond the public [README](../README.md). All documentation in this repository describes the current status only. The history is in the git log.

## Working rules

- Tasks on the command line are recipes of the `justfile` in the repository root; `just` lists them. A new recurring command becomes a recipe there.
- The Python environment is managed by uv. `pyproject.toml` names the packages, `uv.lock` pins them, and the Docker image installs from the same lock file. Engine, risk models and schema need only the standard library; the packages are for the app.
- Work happens on `main`. Every change is committed and pushed unless a prompt says otherwise.
- Every prompt is logged in [prompting.log](prompting.log) with date-time, selected model, attachments and the prompt text. Nothing else goes into the log.
- [initial-prompt.txt](initial-prompt.txt) is the start prompt of the project.

## Folders

| Folder | Purpose |
|---|---|
| `background/` | Literature with the PDFs, the report on toxicity with the risk model candidates, the intervention model, figures for talks and the app |
| `schema/` | Central data schema with loader, validator, CSV reader and writer |
| `engine/` | Synthetic data generator: microsimulation, intervention scenarios, calibration, uncertainty analysis |
| `risk-model/` | Risk models with a common interface, the detection model, fitting and evaluation |
| `app/` | Inspection app with tutorial and demo; Docker image |
| `project/` | Prompt log, start prompt, screenshots, open findings of the code review, this file |

What exists in each folder is summed up in the section "Status" of the [README](../README.md) and described in the README of the folder.

## Where status, limits and open points are kept

Each kind of information has one place. Other documents link to it and do not repeat it.

| Information | Place |
|---|---|
| Which full texts are in the repository and what was read | `background/references.md`, table "Full texts" and its notes |
| Topics the literature does not cover | `background/toxicity-report.md`, section 9 |
| Risk model candidates and which of them exist as models | `background/toxicity-report.md`, section 8 |
| Which parameter of the engine comes from the literature and which is an assumption | `engine/README.md`, "Basis of the parameters"; in detail the `basis` notes in `engine/config/` |
| Literature anchors of the intervention parameters | `background/intervention-model.md`, section 5 |
| What the engine implements of the intervention model | `background/intervention-model.md`, section 6 |
| Where the engine is simpler than reality | `engine/README.md`, "Simplifications" |
| Open extensions of engine and interventions | `engine/README.md`, "Ideas for later" |
| How far the risk models can be trusted | `risk-model/README.md`, "Limits"; in detail the `basis` notes in `risk-model/config/models.json` |
| Open extensions of the risk models | `risk-model/EXTENSIONS.md` |
| Limits of the app | `app/README.md`, "Limits" |
| Open findings of the code review | `project/code-review-issues.md` |
| Open organisational points | this file, "Open points" |
| Summary of the whole project | `README.md`, "Status" |
| What the app tells its users about the state of the project | `app/explorer/templates/explorer/disclaimer.html` and `about.html`, the texts of `app/explorer/static/explorer/tour-steps.js` and of the stories in `app/explorer/static/explorer/stories/`, the notes in `app/explorer/views.py` |

## Literature

### Selection

The references have three parts:

- Toxicity in the three patient groups and the main therapy classes: combination chemotherapy, taxanes, androgen deprivation and androgen receptor inhibitors, PARP inhibitors, radioligand therapy, antibody–drug conjugates, checkpoint inhibitors, and CDK4/6 inhibitors. These are ten phase 3 trials, two cluster-randomised trials, one pooled safety analysis, one meta-analysis, one review and five guidelines, published between 2020 and 2024 in The New England Journal of Medicine, The Lancet, JAMA, JAMA Network Open, Journal of Clinical Oncology, Annals of Oncology, European Heart Journal, Nature Reviews Clinical Oncology and ESMO Open.
- Eight guidelines for the derivation of risk models. Treatment guidelines that define the therapy settings: ASCO on metastatic pancreatic cancer, ASCO and EAU on advanced prostate cancer, ESMO on metastatic breast cancer. Guidelines on risk assessment and monitoring: ASCO on older patients, ASCO on venous thromboembolism, ASCO and IDSA on febrile neutropenia (from 2018), ESMO on patient-reported outcome measures.
- Nine sources for the parameters of risk models and interventions: risk scores for chemotherapy toxicity in older patients ([Hurria 2011](../background/references.md#hurria-2011), [Hurria 2016](../background/references.md#hurria-2016), [Extermann 2012](../background/references.md#extermann-2012)) and for neutropenic complications ([Lyman 2011](../background/references.md#lyman-2011)), adherence and effect of symptom monitoring ([Absolom 2021](../background/references.md#absolom-2021)) and its costs ([Lizée 2019](../background/references.md#lizee-2019)), cardiovascular safety of androgen deprivation ([Lopes 2021](../background/references.md#lopes-2021)), management of lung toxicity under trastuzumab deruxtecan ([Swain 2022](../background/references.md#swain-2022)), and quality-of-life utilities ([Lloyd 2006](../background/references.md#lloyd-2006)).

Section 9 of the report lists the topics that the references do not cover.

### How references are checked

- Every reference is looked up in PubMed through the NCBI E-utilities. Title, authors, journal, year, volume, issue, pages and DOI come from the PubMed record.
- Author names are compared with Crossref, which keeps accents that PubMed drops.
- A reference only enters `references.md` after this check.

### Sources for the report

The report uses the PDFs in `background/papers/`, converted to text with `pdftotext`. For references without a PDF it uses the accepted manuscript from the PubMed Central article datasets where one exists, and the PubMed abstract otherwise. The table "Full texts" in `background/references.md` shows the source for each reference. Numbers in the report are taken from these texts only.

Sections 2 to 7 of the report state what the sources say. Section 8, the risk model candidates, is our own derivation and is marked as such.

Which texts were read in full, in selected sections or as abstract only is in the table "Full texts" of `background/references.md` and its notes. One limit of the text extraction: in the text of [Conroy 2023](../background/references.md#conroy-2023), the signs "≥" and "≤" are lost. The thresholds for Karnofsky score and bilirubin in section 3 of the report follow from the wording of the neighbouring recommendations.

### PDFs

The PDFs are in `background/papers/`. The table "Full texts" of `background/references.md` lists them and names the references without a PDF. File names follow the pattern `<first author>-<year>-<publisher file name>.pdf`, without spaces, so that the links of the reference list work. The file of [Haanen 2022](../background/references.md#haanen-2022) is spelled `Haanan-…` .

Automated download is limited because the publisher websites and the Europe PMC website block scripted access. The only automated source for PDFs is the PubMed Central article dataset on AWS (`pmc-oa-opendata`), which holds PDFs only for articles with an open licence.

### Licences of the stored PDFs

- [Powell 2022](../background/references.md#powell-2022) and [Nichetti 2024](../background/references.md#nichetti-2024) are open access under CC BY and may be redistributed. [Swain 2022](../background/references.md#swain-2022) is open access under CC BY-NC-ND.
- All other PDFs are publisher versions under publisher copyright, obtained through the access of an institution or free to read on the journal website. `background/papers/README.md` states their permitted use.

The copyrighted PDFs must not be in the repository when it becomes public, see "Open points".

## Schema and engine

- The schema in `schema/` is the single source for field names, types and allowed values. Code in other folders reads it from there and does not repeat field lists. Reading and writing CSV files also goes through `schema/toxage_schema.py`. Rules for extending it are in `schema/README.md`.
- The engine is plain Python 3 without further packages. It imports the risk models for the model-guided start and for lung monitoring. `engine/README.md` describes the model variables, the covariate mechanisms, the hazard model, the scenarios and the uncertainty analysis. The parameters themselves are in `engine/config/`.
- After every change of the model or its parameters, `python3 engine/calibrate.py` has to be run. It takes about two minutes and rewrites `engine/config/calibration.json`, which is under version control.
- Generated data go to `engine/output/`, which is not under version control. Data are reproduced from the seed. 3000 patients under eight scenarios give about 880 000 observation records and take about 45 seconds; checking them against the schema and writing the files takes longer.
- Scenarios must stay comparable patient by patient. Every random decision in `course.py`, `interventions.py` and `measurements.py` therefore goes through `draws.py` with a purpose and a week, never through a shared random generator. A new decision gets a new purpose name.
- Tests run with `python3 -m unittest discover engine/tests`.
- The tumour types follow their shares in every part of a cohort: each patient gets the type that is furthest behind its share. A selection of tumour types, subgroups and regimens travels as the entry `selection` of the engine configuration and is stored in the metadata of a data set.

## Risk model

- The risk model has its own configuration in `risk-model/config/models.json`. It does not import the engine and does not read its parameters. Both draw on the same literature.
- `risk-model/toxage_risk.py` is the interface for the app: one class per model with risk, reference risk and factors. The calculations are in `models.py`. A new model is added in both places and then appears in the app without changes there.
- The engine generates outcomes with a richer process than the risk models assume. The evaluation in `risk-model/README.md` therefore shows how well simple baseline models do on these data. For lung toxicity, neutropenia and cardiovascular events, engine and risk model use the same published ratios; the engine adds the frailty, which the models do not know.
- A risk category that is to be as complete as lung toxicity and cardiovascular events touches every part: fields in the schema, rate and risk factors in the engine configuration, the event with its course in `course.py`, signals in `measurements.py`, a monitoring component and a scenario in `interventions.json`, an outcome field for the time window of the model, the model with scoring, fitting and evaluation, and a chart by grade in `app/explorer/timeline.py`.
- Each model has a figure in `background/figures/` with its predictors, formula, a worked example, its properties and references; the overview of the project is there as well. `build.py` takes the numbers from `models.json` and `models.py` and the references from the reference list, `render.mjs` saves them as PNG (`just figures`). After a change of a model, of the scenarios or of the schema, the figures are built again and looked at: a longer table or text can run over the 16:9 page.
- The risk model is plain Python 3 without further packages, like the engine. Refitting uses its own binomial regression in `glm.py`.
- Scores go to `risk-model/output/`, which is not under version control.
- Tests run with `python3 -m unittest discover risk-model/tests`. They generate data with the engine, so a change of the engine can make them fail.

## App

- The app needs Django, and gunicorn in the container (`pyproject.toml`). Pages are Django templates, charts are drawn by a web component in plain JavaScript.
- `Dockerfile` and `docker-compose.yml` are in the repository root, because the image needs engine, risk model, schema and documents next to the app.
- The server must run as one process. Data sets are generated in a thread of that process, and the rows of a scenario are kept in its memory.
- Model parameters: the JSON files of the repository are the defaults. The app stores only changed values, per file, in the table Setting. `params.engine_config()` gives the engine its configuration; the engine itself never reads the database.
- A new document for the app is one line in `explorer/docs.py`. An image on a line of its own in a document is shown if it is a PNG of `background/figures/`, served at `/figures/<name>.png`. A new parameter file is one entry in `explorer/params.py`.
- Data sets are generated on the page "Data" or with `python3 manage.py load_cohort`. In development the database is `app/db.sqlite3`, in the container `/data/db.sqlite3`; neither is under version control. Each patient has one course per scenario with outcome, events, alerts and weekly observations.
- The storage model has one initial migration. As long as no installation has to be kept, a change of the models replaces this migration; afterwards changes get migrations of their own.
- The rows of a scenario are kept in memory after first use. `cohort.clear_cache()` empties this store; `store.generate` calls it.
- Filters and the charts per patient characteristic are built from the schema, the status bar and risk filters from the registered risk models.
- The steps of the tutorial are in `explorer/static/explorer/tour-steps.js`. A new function of the app gets a step there. A step that changes data or parameters is marked with `changes`; the tutorial points to deleting and resetting at its end, and the server restores the state after every story of the demo.
- The stories of the demo are in `explorer/static/explorer/stories/`, one file each, listed in `index.js`. Their steps name places of the app (`prerequisites.js`) instead of CSS selectors. When a page, chart or field changes, the place is updated there once; `just check-stories` (app running with `TOXAGE_SIMPLE_UI=1`) plays every story in both views and lists the steps whose place was not found. A place marked `full` leaves its steps out in the simple view. A new story is a new file and one line in `index.js`.
- Tests run in `app/` with `python3 manage.py test explorer` and `node --test "explorer/tests/*.test.mjs"`.

## Cloud environment

Sessions for this repository run in the cloud environment `toxage-sim`. Its network allows the package registries and these hosts:

- Literature services: `pubmed.ncbi.nlm.nih.gov`, `eutils.ncbi.nlm.nih.gov`, `pmc.ncbi.nlm.nih.gov`, `www.ebi.ac.uk`, `europepmc.org`, `api.crossref.org`, `doi.org`
- Publishers: `www.annalsofoncology.org`, `ascopubs.org`, `academic.oup.com`, `jamanetwork.com`, `www.esmoopen.com`, `www.nejm.org`, `www.thelancet.com`, `www.nature.com`

The literature services work from scripts. The publisher hosts answer scripted requests with a bot check and are of no use for downloads.

## Open points

Organisational points. The open work on literature, engine, risk models and app is in the places named in the section "Where status, limits and open points are kept".

- Add the PDFs that are missing in `background/papers/`.
- Decide on a licence for the repository before it becomes public. The disclaimer of the app holds preliminary terms of use.
- Before the repository becomes public, reduce `background/papers/` to openly licensed files and remove the other PDFs from the git history.
