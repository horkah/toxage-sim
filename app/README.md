# app

Web app to inspect the synthetic data and the risk scores: for the whole cohort, for a filtered part of it, and for one patient compared with the others.

It is built with Django and nothing else; gunicorn serves it in the container. The packages are named in `pyproject.toml` in the repository root and pinned in `uv.lock`. The pages are Django templates, the charts are drawn as SVG by a small web component in plain JavaScript, and a small script loads pages in place, so the app reacts without reloading. Besides the explorer the app manages the data sets and the model parameters, keeps archives of them, and shows the schema and the scientific background of the project.

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
| `TOXAGE_DISK_LIMIT_MB` | Limit of the database on disk in MB, over all data sets; a data set that would not fit is not generated | `500` |
| `TOXAGE_CACHE_PATIENTS` | Patients whose rows and events are kept in memory, over all data sets and scenarios; about 400 MB for 60 000 | `60000` |
| `TZ` | Time zone of the server; the app shows all times in it: build, data sets, archives | `Europe/Berlin` (set in `docker-compose.yml`) |

The image holds the app, the engine, the risk models, the schema and the documents, without the PDFs of the literature and without the folder `project/` (prompt log and internal notes), which are for developers only. It runs gunicorn with one worker process and several threads. One process is required: data sets are generated in a thread of the server process, and the rows of a scenario are kept in its memory.

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

The first command tests the Python code, the second the helpers of the page script, the charts and the tours in JavaScript. Node.js (version 18 or newer) is only needed for the second.

## Version

The version of the app is the one in `pyproject.toml`. Every build gets a stamp on top: the Docker image writes the moment of the build (seconds since 1970) and the commit into the file `BUILD` (`just docker-build` passes the commit), and a working copy uses the moment and hash of the last commit. The app shows the moment as date and time in the time zone of the server, e.g. `20261113.2245 (abc1234)`. `TOXAGE_BUILD` overrides both and is shown as it is.

All times of the app are shown in the time zone of the server (`toxage_app/zone.py`): the variable `TZ`, else the zone configured in the system (`/etc/timezone` or `/etc/localtime`), else UTC. A container does not know the zone of its host, so `docker-compose.yml` passes `TZ`, by default `Europe/Berlin`; set `TZ` in `.env` for another zone. Version and build are shown in the footer of every page and on the page "About" (`toxage_app/version.py`).

## Sections

The bar at the top leads to five sections. Each piece of information has one place; links connect the places.

| Section | Content |
|---|---|
| Explore | Cohort and single patient: risk, patient characteristics, course over time, interventions |
| Data | Stored data sets: generate, choose for the explorer, inspect records, download as CSV, export and import archives, delete a scenario, a data set or everything |
| Parameters | All model parameters of the engine and the risk models, with their defaults and their basis; change, reset |
| Reference | The data schema with every table and field, and the scientific background: toxicity report, intervention model, references, data engine, risk models |
| About | What the project is, its authors and how it was made, version and build |

"Help" next to the sections starts the tutorial or the demo, "Settings" holds theme, text size and the offer of the tours. The footer has the disclaimer and the version.

The app shows the content of the project, not its development: the prompt log, the internal notes and the developer sections of the component documents (how to run, files, programming interface) stay in the repository.

## How it works

### Disclaimer

Every page leads to the disclaimer until the user has accepted the limitations and terms of use. The acceptance is a cookie that holds the version of the terms. Without the box "Do not show this again" the cookie ends with the browser session, with the box it lasts one year. Raising `DISCLAIMER_VERSION` in `toxage_app/settings.py` asks every user again. The settings have a button to withdraw the acceptance.

### Pages that change in place

Links and forms of the app load the next page in the background and swap only the changed part of the screen (`static/explorer/app.js`). A filter, a scenario, a risk model, a saved parameter or a deleted data set therefore changes the page without reloading it. Focus, scroll position and opened groups stay as they were, the address follows every change, and the back button works. Downloads, the disclaimer and other sites load as usual. Without JavaScript every link and form works as a normal page load.

Before anything is deleted or replaced, a warning with a red sign asks for confirmation.

### One view for cohort and patient

There is one page. A bar on top holds the context: the data set, the scenario with its comparison, and the patient. The cohort panel on the left counts the selected patients and shows every active filter as a chip that removes it on a click.

Without a selected patient the page shows the cohort. With a selected patient it shows a patient card with the key facts, all characteristics and the outcome, and in the view "Risk" the patient's risk under the chosen model with the factors behind it. The cards of the risk models add the patient's risk under every model. The patient is marked in every chart: the bar of the patient's group, a line at the patient's risk or event day, a ring around the patient's point.

A patient is selected by ID in the search field (`42` is enough for `P000042`), by the button "Random", which picks a patient of the current selection, by a click on a point in a scatter plot, or by a click on a patient ID in the records. The whole state is in the address: data set, filters, scenario, view, risk model and patient. A view can therefore be bookmarked and shared.

Objects are linked to their other places: a field of the patient card or of the records to its description in the schema, a scenario in a table to its charts, a data set to its card on the page "Data", a risk model to its documentation and its parameters, a changed parameter of a data set to its row on the page "Parameters".

### Scenarios

The engine simulates the same patients under several intervention scenarios. Two choices in the context bar set which scenario the page shows and which one it is compared with. Usual care is the default; a newly chosen scenario is compared with usual care unless something else is chosen. Filters, cohort, model cards and patient data refer to the outcome in the selected scenario.

### Views

Four views share the scenario, the filters and the selected patient:

| View | Content |
|---|---|
| Risk | Predicted risk against the observed outcome for the chosen risk model |
| Patient characteristics | Observed rate and mean predicted risk per group of every baseline field |
| Course over time | For the cohort: first severe adverse event, share on therapy and survival over time, for the selected scenario and the comparison. For a selected patient: dose, blood values, oxygen saturation, blood pressure and reported symptoms per week under both scenarios, with the adverse events, alerts and the end of therapy marked, and a table of the adverse events under each scenario. |
| Interventions | All scenarios side by side for the selected patients: a table of key numbers, including costs and quality-adjusted life years against usual care, bar charts, lung toxicity and cardiovascular events by grade, and for a scenario with monitoring the days gained and the grades of the events recognised early. |

### Filters

The filters are built from the [schema](../schema/) and from the registered risk models. Every field of the baseline and the outcome table gets a filter that fits its type: check boxes for a fixed list of values, yes/no for booleans, a range for numbers. Every risk model gets a range filter for its risk in percent. A new field in the schema or a new risk model therefore gets a filter without code changes. A click on a bar of a chart sets the filter to that group or risk band.

### Charts

In the views "Risk" and "Patient characteristics" one card per risk model shows the observed rate, the mean predicted risk, the AUC and the Brier score in the selection. A click on a card chooses the risk model that the charts show.

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

Generating runs in the background. The card of the data set shows the progress and updates itself until the data set is ready. If the server restarts meanwhile, the data set is marked as failed and can be deleted. The form offers to calibrate the event rates again first; this is needed after changes of the regimens or the simulation parameters and takes about a minute.

Records can be inspected table by table in the layout of the [schema](../schema/), by scenario and by patient, and downloaded as CSV files that `schema/toxage_schema.py` reads back.

The database has a limit on disk, 500 MB unless `TOXAGE_DISK_LIMIT_MB` sets another (in `.env` for Docker). Before a data set is generated, its size is estimated: about 5.5 KB per patient and scenario, so 1500 patients under all seven scenarios need about 58 MB. If it would not fit next to the stored data sets, it is not generated, and the page says how much it would need and how much is free. The form shows the estimate while size and scenarios are chosen. After generating, the size is measured again; a data set that did not fit after all is deleted again and stays as a failed entry with the reason. In both cases other data sets can be deleted, or a smaller one generated. The same limit holds for archive imports: before importing, the data sets of the archive are estimated the same way (next to the stored ones when they are added, alone when everything is replaced), and an archive that would not fit is refused. The import is measured again before it is committed; if it does not fit after all, it is rolled back and the app stays as it was, the old data sets included.

Deleting a scenario removes the courses of all patients in it; the last scenario of a data set stays. Deleting gives the space on disk back at once.

### Archive

"Export everything" saves all data sets that are ready and the changed parameters into one file; "Export" on a data set saves only that data set. An archive can be imported later, into the same or another installation of the app:

- **Add its data sets**: the data sets of the archive are added; data sets and parameters of the app stay.
- **Replace everything**: all data sets and parameter changes of the app are replaced by those of the archive. The app asks first.

The file is gzip-compressed JSON Lines (`.jsonl.gz`), described in `explorer/archive.py`: a header with the format version, the version of the app and of the schema tables, then one line per data set and one per patient with all its courses, and an end line with the counts. The records keep the layout of the schema, so an archive can also be read without the app. On import every patient record is checked against the schema; a file that is not an archive of the app, is newer than the app, is damaged or was cut off is refused, and the app stays as it was.

### Parameters

The defaults are the JSON files of the repository: `engine/config/regimens.json`, `parameters.json`, `interventions.json` and `risk-model/config/models.json`. Each value can be changed in the app and is saved as soon as its field is left. Only the changed values are stored, in the database, and they stay until they are reset: one value, one file, or everything. Changed values are marked, the default is shown next to each, and the side bar counts the changes per file and group. A search field narrows the list.

- Engine parameters apply to data sets generated from then on. A data set keeps the changed values it was made with and shows their number.
- Risk model parameters apply to the risks in the explorer at once.
- Texts that explain a value, such as its source, are shown and cannot be changed.
- A value keeps the type of its default: number, true or false, text, or a list in JSON notation.
- A change is tried before it is kept: the risk models score 300 synthetic patients, the engine simulates 21 patients under all scenarios. A value that makes them fail, such as a regimen rate of 1 or a negative hazard ratio, is refused with the reason, and the stored values stay. If stored values break the risk models anyway, e.g. from an older version, the explorer says so and links to the parameters.

### Storage

The database is SQLite in one file, with four tables:

| Table | Content |
|---|---|
| Dataset | Name, size, seed, state and progress, scenarios, record counts, and the changed parameters it was made with |
| Patient | One patient of a data set with the baseline record |
| Course | One patient in one scenario: outcome, adverse events, alerts, and the weekly observations as one list per field |
| Setting | The changed values of one parameter file |

Records are stored as JSON in the layout of the schema, so the database needs no change when the schema grows. The outcome is kept apart from the bulky observations, so that cohort views read only what they need. 1500 patients under seven scenarios take about 65 MB.

SQLite fits because there is one server process, the data are written once per data set and then only read, and one file in a volume is easy to keep and to back up. Write-ahead logging lets pages be read while a data set is stored and keeps disk writes low. A database server would be the choice for several server processes or many users writing at the same time; Django makes that change a matter of settings.

### Tutorial and demo

Two guided tours lead through the whole app in about 70 steps: help and settings, generating a data set, the archive, the risk models and their charts, filters, a single patient, patient characteristics, the course over time, the scenarios and interventions, the parameters, records, deleting and resetting, the reference and the page "About". Each step shows a hint with a short explanation next to the part of the page it is about.

- In the **tutorial** the user does every step herself. The hint says what to do and moves on when it is done. "Do it for me" carries out a step, "Back" and "Next" move freely, "End" stops. The tutorial changes nothing on its own and leaves the data sets and parameters as the user made them; its last steps point to the ways to delete and reset.
- The **demo** does every step itself and runs in an endless loop until it is stopped; before each new round the state before the demo is brought back. Two speed values control it: the reading time in seconds per 20 words of a hint (0 to 30, default 6.7, about three words per second), and the seconds a new state of the screen is shown before the next step. The right arrow key or a swipe to the left goes to the next step at once. The controls (pause, stop, speed) show on the first step and otherwise only after a click or touch on the hint; while they are shown the demo waits five seconds longer, and a second click hides them. Each new step starts with the controls hidden. A deletion in the demo needs no confirmation.

In the tutorial the right arrow key or a swipe to the left works like "Next" where it is offered.

The demo leaves the app exactly as it was. At its start the server notes the changed parameters, the stored data sets and the chosen data set. The demo deletes what it created and resets what it changed step by step, and at its end, or when it is stopped, the server puts the noted state back: parameters, data sets and chosen data set. If a demo is cut off, for example by closing the browser, the next page offers to restore the state.

The app offers both tours once per browser session after the disclaimer. This offer can be turned off in the offer itself and turned on and off in the settings. Both tours can be started under "Help" at any time.

In read-only mode the tours leave out all steps that change data or parameters.

### Settings

"Settings" holds bright, dark or system theme, a larger text size, and whether the tours are offered at start. They are stored in the browser (local storage).

## Files

| File | Content |
|---|---|
| `toxage_app/settings.py` | Settings, including the version of the terms and the address of the source code |
| `toxage_app/version.py` | Version and build of the app |
| `explorer/models.py` | Data sets, patients, one course per patient and scenario, and the changed parameters |
| `explorer/store.py` | Generates data sets in the background, stores them, reads records, exports CSV, deletes |
| `explorer/params.py` | Model parameters: defaults from the repository, changes of the user |
| `explorer/pages.py` | Pages for data sets, archive, records, parameters, schema and documents |
| `explorer/archive.py` | Export and import of archives |
| `explorer/docs.py` | The documents shown in the app, without their developer sections, and a small Markdown renderer |
| `explorer/cohort.py` | Loads the patients, adds the risks of all models, describes the schema fields |
| `explorer/filters.py` | Filters built from schema and risk models |
| `explorer/charts.py` | Data of the risk charts and key numbers |
| `explorer/timeline.py` | Data of the charts over time and across scenarios |
| `explorer/views.py`, `middleware.py` | Explorer, random patient, about, disclaimer |
| `explorer/templates/explorer/` | Templates |
| `explorer/static/explorer/charts.js` | Web component `<tox-chart>` that draws the charts |
| `explorer/static/explorer/app.js` | Pages in place, warnings before deleting, messages, settings, forms that apply on change |
| `explorer/static/explorer/img/logo.svg` | Logo and icon of the app |
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
