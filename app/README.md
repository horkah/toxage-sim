# app

Web app to inspect the synthetic data and the risk scores: for the whole cohort, for a filtered part of it, and for one patient compared with the others.

It is built with Django and nothing else. The pages are Django templates, the charts are drawn as SVG by a small web component in plain JavaScript.

## Run

```bash
pip install -r app/requirements.txt
cd app
python3 manage.py migrate
python3 manage.py load_cohort --n 5000 --seed 1
python3 manage.py runserver
```

Then open http://localhost:8000. `load_cohort` generates patients with the [engine](../engine/) and replaces the data that were stored before. The database is the file `app/db.sqlite3`, which is not under version control.

Environment variables for a deployment: `TOXAGE_DEBUG=0`, `TOXAGE_SECRET_KEY`, `TOXAGE_ALLOWED_HOSTS` (comma-separated), `TOXAGE_DB` (path of the database file).

## Tests

```bash
cd app
python3 manage.py test explorer
node --test "explorer/tests/*.test.mjs"
```

The first command tests the Python code, the second the chart helpers in JavaScript. Node.js is only needed for the second.

## How it works

### Disclaimer

Every page leads to the disclaimer until the user has accepted the limitations and terms of use. The acceptance is a cookie that holds the version of the terms. Without the box "Do not show this again" the cookie ends with the browser session, with the box it lasts one year. Raising `DISCLAIMER_VERSION` in `toxage_app/settings.py` asks every user again. The menu has a button to withdraw the acceptance.

### One view for cohort and patient

There is one page. Without a selected patient it shows the cohort. With a selected patient it shows the patient's data and risks on top, and marks the patient in every chart: the bar of the patient's group, a line at the patient's risk or event day, a ring around the patient's point.

A patient is selected by ID in the search field (`42` is enough for `P000042`), by the button "Random", which picks a patient of the current selection, or by a click on a point in a scatter plot. The whole state is in the address: filters, risk model and patient. A view can therefore be bookmarked and shared.

### Filters

The filters are built from the [schema](../schema/) and from the registered risk models. Every field of the baseline and the outcome table gets a filter that fits its type: check boxes for a fixed list of values, yes/no for booleans, a range for numbers. Every risk model gets a range filter for its risk in percent. A new field in the schema or a new risk model therefore gets a filter without code changes. A click on a bar of a chart sets the filter to that group or risk band.

### Charts

The status bar shows the size of the selection and, per risk model, the observed rate, the mean predicted risk, the AUC and the Brier score. A tab chooses the risk model that the charts show.

| Chart | Question it answers |
|---|---|
| Distribution of predicted risk | How are risks spread, and how many patients in each risk band had the event? |
| Calibration | Does the predicted risk match the observed rate, in ten groups of equal size? |
| Cumulative incidence by risk group | When do events occur, and how well do the risk thirds separate? |
| Predicted risk by age | How does risk depend on age, and where is the selected patient? |
| Risk across models | Are patients at high risk for one outcome also at high risk for the other? |
| One chart per patient characteristic | Observed rate and mean predicted risk per group, with the number of patients |

The charts per characteristic are built from the schema as well, so new fields appear without code changes. Categories come from the allowed values, from small integer ranges, or from round bins; a long tail of large values goes into an open top bin.

### Settings

The menu holds the settings: bright, dark or system theme, and a larger text size. They are stored in the browser (local storage).

## Files

| File | Content |
|---|---|
| `toxage_app/settings.py` | Settings, including the version of the terms |
| `explorer/models.py` | Data set and patients; records are stored in the layout of the schema |
| `explorer/cohort.py` | Loads the patients, adds the risks of all models, describes the schema fields |
| `explorer/filters.py` | Filters built from schema and risk models |
| `explorer/charts.py` | Data of all charts and key numbers |
| `explorer/views.py`, `middleware.py` | Pages, random patient, disclaimer |
| `explorer/templates/explorer/` | Templates |
| `explorer/static/explorer/charts.js` | Web component `<tox-chart>` that draws the charts |
| `explorer/static/explorer/app.js` | Settings and filter form |
| `explorer/static/explorer/style.css` | Layout and colours for bright and dark mode |
| `explorer/management/commands/load_cohort.py` | Generates and stores a cohort |
| `explorer/tests/` | Tests |

## Limits

- The data have one record per patient at the start of a therapy line. Follow-up over time is not modelled yet.
- All patients are loaded and scored on every request. This is fast enough for some ten thousand patients.
