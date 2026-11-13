# app

Web app to inspect the synthetic data and the risk scores: for the whole cohort, for a filtered part of it, and for one patient compared with the others.

It is built with Django and nothing else; gunicorn serves it in the container. The packages are named in `pyproject.toml` in the repository root and pinned in `uv.lock`. The pages are Django templates, the charts are drawn as SVG by a small web component in plain JavaScript. Besides the explorer the app manages the data sets and the model parameters and shows the schema and the documents of the project.

## Run with Docker

```bash
docker compose up -d --build
```

Then open http://localhost:8000, accept the terms, and generate a first data set on the page "Data". The database and the secret key are in the volume `toxage-data`, so they survive a new container.

| Variable | Meaning | Default in the container |
|---|---|---|
| `TOXAGE_ALLOWED_HOSTS` | Host names under which the app is reached, separated by commas | `*` |
| `TOXAGE_CSRF_TRUSTED_ORIGINS` | Addresses with scheme from which forms may be sent; needed behind a proxy with HTTPS | empty |
| `TOXAGE_READ_ONLY` | `1`: data and parameters can be viewed but not changed | `0` |
| `TOXAGE_SECRET_KEY` | Secret key; without it one is created once and kept in the data folder | created |
| `TOXAGE_DATA_DIR` | Folder of the database and the secret key | `/data` |
| `TOXAGE_DEBUG` | `1` for development | `0` |

The image holds the app, the engine, the risk models, the schema and the documents, without the PDFs of the literature. It runs gunicorn with one worker process and several threads. One process is required: data sets are generated in a thread of the server process, and the rows of a scenario are kept in its memory.

The app has no login. Everyone who reaches it can generate and delete data and change parameters, unless `TOXAGE_READ_ONLY=1` is set. It is a demonstrator for a trusted network.

## Run for development

```bash
just setup
```

```bash
just serve
```

Then open http://localhost:8000. `just setup` creates the Python environment with uv, `just serve` updates the database and starts the development server. Data sets are generated on the page "Data" or from the command line:

```bash
just load 1500 1
```

Without just, the same commands are `uv sync`, `uv run python app/manage.py migrate`, `uv run python app/manage.py runserver` and `uv run python app/manage.py load_cohort --n 1500 --seed 1`.

`load_cohort` replaces the stored data sets unless `--keep` is given; `--scenarios` limits the scenarios. The database is the file `app/db.sqlite3`, which is not under version control. After a change of the storage model in development, delete this file and run `migrate` again.

## Tests

```bash
just test-app
```

```bash
just test-js
```

The first command tests the Python code, the second the chart helpers in JavaScript. Node.js is only needed for the second.

## Sections

The bar at the top and the menu lead to every part of the project:

| Section | Content |
|---|---|
| Explore | Cohort and single patient: risk, patient characteristics, course over time, interventions |
| Data | Stored data sets: generate, choose for the explorer, inspect records, download as CSV, delete a scenario, a data set or everything |
| Parameters | All model parameters of the engine and the risk models, with their defaults and notes; change, save, reset |
| Schema | Tables and fields of the central data schema |
| Documents | The documents of the repository: project overview, toxicity report, references, intervention model, the components, internal documentation, prompt log |
| Guided tours | Tutorial and demo; in the menu |
| Disclaimer and licence | Terms of use; in the menu |

## How it works

### Disclaimer

Every page leads to the disclaimer until the user has accepted the limitations and terms of use. The acceptance is a cookie that holds the version of the terms. Without the box "Do not show this again" the cookie ends with the browser session, with the box it lasts one year. Raising `DISCLAIMER_VERSION` in `toxage_app/settings.py` asks every user again. The menu has a button to withdraw the acceptance.

### One view for cohort and patient

There is one page. Without a selected patient it shows the cohort. With a selected patient it shows the patient's data and risks on top, and marks the patient in every chart: the bar of the patient's group, a line at the patient's risk or event day, a ring around the patient's point.

A patient is selected by ID in the search field (`42` is enough for `P000042`), by the button "Random", which picks a patient of the current selection, or by a click on a point in a scatter plot. The whole state is in the address: filters, risk model and patient. A view can therefore be bookmarked and shared.

### Scenarios

The engine simulates the same patients under several intervention scenarios. Two choices above the charts set which scenario the page shows and which one it is compared with. Usual care is the default; another scenario is compared with usual care unless something else is chosen. Filters, status bar and patient data refer to the outcome in the selected scenario.

### Views

Four views share the scenario, the filters and the selected patient:

| View | Content |
|---|---|
| Risk | Predicted risk against the observed outcome for the chosen risk model |
| Patient characteristics | Observed rate and mean predicted risk per group of every baseline field |
| Course over time | For the cohort: first severe adverse event, share on therapy and survival over time, for the selected scenario and the comparison. For a selected patient: dose, blood values, oxygen saturation and reported symptoms per week under both scenarios, with the adverse events, alerts and the end of therapy marked, and a table of the adverse events under each scenario. |
| Interventions | All scenarios side by side for the selected patients: a table of key numbers, including costs and quality-adjusted life years against usual care, bar charts, lung toxicity by grade, and for a scenario with monitoring the days gained and the grades of the events recognised early. |

### Filters

The filters are built from the [schema](../schema/) and from the registered risk models. Every field of the baseline and the outcome table gets a filter that fits its type: check boxes for a fixed list of values, yes/no for booleans, a range for numbers. Every risk model gets a range filter for its risk in percent. A new field in the schema or a new risk model therefore gets a filter without code changes. A click on a bar of a chart sets the filter to that group or risk band.

### Charts

The status bar shows the size of the selection and, per risk model, the observed rate, the mean predicted risk, the AUC and the Brier score. A tab chooses the risk model that the charts show.

| Chart | Question it answers |
|---|---|
| Distribution of predicted risk | How are risks spread, and how many patients in each risk band had the event? |
| Calibration | Does the predicted risk match the observed rate, in ten groups of equal size? |
| Cumulative incidence by risk group | When do events occur within the window of the risk model, and how well do the risk thirds separate? |
| Predicted risk by age | How does risk depend on age, and where is the selected patient? |
| Risk across models | Are patients at high risk for one outcome also at high risk for the other? |
| One chart per patient characteristic | Observed rate and mean predicted risk per group, with the number of patients |

The charts per characteristic are built from the schema as well, so new fields appear without code changes. Categories come from the allowed values, from small integer ranges, or from round bins; a long tail of large values goes into an open top bin.

### Data sets

A data set is one cohort, simulated under one or several scenarios with the parameters of that moment. Several data sets can be stored side by side. The explorer shows the data set chosen on the page "Data", else the newest.

Generating runs in the background. The page shows the progress and reloads until the data set is ready. If the server restarts meanwhile, the data set is marked as failed and can be deleted. The form offers to calibrate the event rates again first; this is needed after changes of the regimens or the simulation parameters and takes about a minute.

Records can be inspected table by table in the layout of the [schema](../schema/), by scenario and by patient, and downloaded as CSV files that `schema/toxage_schema.py` reads back.

Deleting a scenario removes the courses of all patients in it; the last scenario of a data set stays. Deleting gives the space on disk back at once.

### Parameters

The defaults are the JSON files of the repository: `engine/config/regimens.json`, `parameters.json`, `interventions.json` and `risk-model/config/models.json`. Each value can be changed in the app. Only the changed values are stored, in the database, and they stay until they are reset: one value, one file, or everything. Changed values are marked, and the default is shown next to each.

- Engine parameters apply to data sets generated from then on. A data set keeps the changed values it was made with and shows their number.
- Risk model parameters apply to the risks in the explorer at once.
- Texts that explain a value, such as its source, are shown and cannot be changed.
- A value keeps the type of its default: number, true or false, text, or a list in JSON notation.

### Storage

The database is SQLite in one file, with four tables:

| Table | Content |
|---|---|
| Dataset | Name, size, seed, state and progress, scenarios, record counts, and the changed parameters it was made with |
| Patient | One patient of a data set with the baseline record |
| Course | One patient in one scenario: outcome, adverse events, alerts, and the weekly observations as one list per field |
| Setting | The changed values of one parameter file |

Records are stored as JSON in the layout of the schema, so the database needs no change when the schema grows. The outcome is kept apart from the bulky observations, so that cohort views read only what they need. 1500 patients under six scenarios take about 40 MB.

SQLite fits because there is one server process, the data are written once per data set and then only read, and one file in a volume is easy to keep and to back up. Write-ahead logging lets pages be read while a data set is stored and keeps disk writes low. A database server would be the choice for several server processes or many users writing at the same time; Django makes that change a matter of settings.

### Tutorial and demo

Two guided tours lead through the whole app in about 70 steps: the menu, generating a data set, the risk models and their charts, filters, a single patient, patient characteristics, the course over time, the scenarios and interventions, the parameters, records, deleting and resetting, the schema and the documents. Each step shows a hint with a short explanation next to the part of the page it is about.

- In the **tutorial** the user does every step herself. The hint says what to do and moves on when it is done. "Do it for me" carries out a step, "Back" and "Next" move freely, "End" stops. The tutorial changes nothing on its own and leaves the data sets and parameters as the user made them; its last steps point to the ways to delete and reset.
- The **demo** does every step itself. Two speed values control it: words per second for reading a hint, and seconds a new state of the screen is shown before the next step. Both can be changed while the demo runs, and it can be paused and stopped.

The demo leaves the app exactly as it was. At its start the server notes the changed parameters, the stored data sets and the chosen data set. The demo deletes what it created and resets what it changed step by step, and at its end, or when it is stopped, the server puts the noted state back: parameters, data sets and chosen data set. If a demo is cut off, for example by closing the browser, the next page offers to restore the state.

The app offers both tours once per browser session after the disclaimer. This offer can be turned off in the offer itself and turned on and off in the settings. Both tours can be started from the menu at any time.

In read-only mode the tours leave out all steps that change data or parameters.

### Settings

The menu holds the settings: bright, dark or system theme, a larger text size, and whether the tours are offered at start. They are stored in the browser (local storage).

## Files

| File | Content |
|---|---|
| `toxage_app/settings.py` | Settings, including the version of the terms |
| `explorer/models.py` | Data sets, patients, one course per patient and scenario, and the changed parameters |
| `explorer/store.py` | Generates data sets in the background, stores them, reads records, exports CSV, deletes |
| `explorer/params.py` | Model parameters: defaults from the repository, changes of the user |
| `explorer/pages.py` | Pages for data sets, records, parameters, schema and documents |
| `explorer/docs.py` | The documents of the repository and a small Markdown renderer |
| `explorer/cohort.py` | Loads the patients, adds the risks of all models, describes the schema fields |
| `explorer/filters.py` | Filters built from schema and risk models |
| `explorer/charts.py` | Data of the risk charts and key numbers |
| `explorer/timeline.py` | Data of the charts over time and across scenarios |
| `explorer/views.py`, `middleware.py` | Pages, random patient, disclaimer |
| `explorer/templates/explorer/` | Templates |
| `explorer/static/explorer/charts.js` | Web component `<tox-chart>` that draws the charts |
| `explorer/static/explorer/app.js` | Settings and filter form |
| `explorer/static/explorer/tour.js` | Tutorial and demo: hints, speed, offer at start |
| `explorer/static/explorer/tour-steps.js` | The steps of the tours: text, page, target, action |
| `explorer/tour.py` | State of the app for the tours; notes and restores the state around a demo |
| `explorer/static/explorer/style.css` | Layout and colours for bright and dark mode |
| `explorer/management/commands/load_cohort.py` | Generates and stores a data set from the command line |
| `../Dockerfile`, `../docker-compose.yml` | Container image and its start |
| `explorer/tests/` | Tests |

## Limits

- The app has no login and no user accounts. Parameters and data sets are shared by all users.
- A demo restores the state of the whole app. Data sets and parameter changes that another user makes while a demo runs are removed with it.
- One data set is generated at a time, and at most 20 000 patients per data set.
- The Markdown renderer covers what the documents of the repository use, not all of Markdown.
- The risk models describe the risk at therapy start without an intervention. In a scenario with an intervention the observed rates are lower than predicted.
- The charts of the Risk view show time to event within the window of the risk model. The longer course is in the view "Course over time".
- All patients are loaded and scored on every request. This is fast enough for some ten thousand patients.
