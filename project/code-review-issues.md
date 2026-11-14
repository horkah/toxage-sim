# Code review: open issues

Review of the whole code base: schema, engine, risk models, app (Python,
templates, JavaScript) and the container setup. Every class and function now
has a comment or docstring, and so do the less common statements.

Each finding has a level:

- **Major**: wrong results, a crash, data loss or a security risk in normal use.
- **Minor**: a defect in rare cases, or code that is easy to get wrong.
- **Cosmetic**: wording, duplication, naming; no effect on results.

Findings that are fixed leave this file; their commits describe issue and fix.
What remains needs a decision of the author.

## Major

### M1. Changed parameters are not checked; one wrong value breaks the explorer for everyone

- Where: `app/explorer/params.py` (`save`), `app/explorer/views.py`, engine and risk models.
- What: the parameters page accepts every value of the right type. A regimen
  rate of 0, 1 or 2 in the risk models is saved, and from then on every page
  of the explorer answers with a server error (500), for all users, until the
  value is reset (math domain error in the logit, or a negative base). A
  negative hazard ratio is saved and silently gives risks below 0 or above 1.
  Engine values such as a probability above 1 or a calibration window of 0
  make every generation fail.
- Fix: check a change before it is kept. Risk model values: score a small
  synthetic cohort with the new configuration; every risk must be a number
  from 0 to 1. Engine values: generate a small cohort under all scenarios
  and check the records against the schema. A change that fails is refused
  with the reason, the stored values stay. The explorer shows a clear page
  instead of a 500 if stored values break the risk models anyway.

### M2. Background generation is not coordinated

- Where: `app/explorer/store.py`, `app/explorer/pages.py`, `app/explorer/tour.py`.
- What: the page disables "Generate" while a data set is being generated, but
  the server does not: a second tab or a direct request starts a second
  generation at the same time (twice the memory and CPU; the README promises
  one at a time). A data set that is deleted while it is generated (e.g. "Stop
  the demo" during "Progress", or "Delete all") is not stopped: its thread
  simulates to the end and then fails with "FOREIGN KEY constraint failed"
  and a traceback in the log.
- Fix: the server refuses a second generation while one is running. The
  thread checks after each scenario whether its data set still exists and
  ends quietly if not.

### M3. The cache of rows and events has no limit

- Where: `app/explorer/cohort.py` (`_CACHE`).
- What: the scored rows and the events of every data set and scenario that a
  page used stay in memory until parameters or data change. The view
  "Interventions" loads all seven scenarios. With several large data sets
  (up to 20 000 patients each) the memory of the single server process grows
  without limit, and the container can be killed.
- Fix: keep only the most recently used entries (least recently used out).

### M4. No access control on a public installation (needs a decision)

- Where: whole app; `docker-compose.yml` (`TOXAGE_READ_ONLY` defaults to 0).
- What: the app has no login. On a public address everyone can generate
  data sets (CPU and disk), import archives of any size, change parameters
  and delete everything. The README names this as a limit for a trusted
  network, but the installation is public.
- Options: set `TOXAGE_READ_ONLY=1` on the public server and change data
  only on a private one; or protect the changing actions (generate, import,
  delete, parameters) with a password or the login of the reverse proxy
  (e.g. basic auth in Caddy); or add user accounts.
- Status: open, decision of the author.

## Minor

### m1. A share of 0 flagged patients still flags one patient

- Where: `engine/interventions.py` (`flag_threshold`).
- What: with `risk_adapted_start/share_flagged` = 0 the threshold is the
  highest score, so the patient with that score is flagged.

### m2. The baseline risk of the lung and heart models can be wrong for protective factors

- Where: `risk-model/models.py` (`ild_baseline_risk`, `cv_baseline_risk`).
- What: the bisection searches r0 between 0 and the target rate. That holds
  only if the reference population has a mean hazard ratio of at least 1. With
  a hazard ratio below 1 (possible on the parameters page) r0 must be above
  the target, and the result sticks at the target. The same bisection is
  written twice.

### m3. The regression does not say whether it converged

- Where: `risk-model/glm.py` (`fit`).
- What: after `max_iter` rounds without convergence the last coefficients are
  returned as if they were the result.

### m4. Whole-number parameters accept fractions

- Where: `app/explorer/params.py` (`parse`).
- What: 2.5 for a whole-number parameter (e.g. `simulation/weeks`) is saved
  as 2.5 and fails only later, when a data set is generated.

### m5. weeks=0 is taken as "not given"

- Where: `engine/course.py` (`simulate`).
- What: `weeks or params[...]` replaces an explicit 0 with the default.

### m6. Every page view of "Data" writes to the database

- Where: `app/explorer/store.py` (`mark_interrupted`).
- What: called by every view of the data page, its polling and
  `/tour/state/` (every 0.4 s in the demo), it runs an UPDATE each time, which
  needs the write lock of SQLite even when nothing changes. While a large data
  set is stored, these requests wait for the lock.

### m7. A page number beyond the end reads the whole table

- Where: `app/explorer/pages.py` (`records`).
- What: `?page=100000` reads every record of the table to find nothing.

### m8. DEBUG is on unless it is switched off (needs a decision)

- Where: `app/toxage_app/settings.py`.
- What: without `TOXAGE_DEBUG` the app runs in debug mode, which shows
  details of the code on errors. The Dockerfile and `just serve-prod` switch
  it off, so only other ways of running the app are affected.
- Options: default off and `TOXAGE_DEBUG=1` in `just serve`; or leave as is.
- Status: open, decision of the author.

### m9. Thresholds of risk factors are fixed in the code (needs a decision)

- Where: `engine/hazards.py` (`multipliers`, `general_multiplier`),
  `engine/population.py`, `risk-model/models.py`.
- What: the hazard and odds ratios are parameters, but the thresholds they
  apply from are not: age 70 and 65, haemoglobin 12.5 g/dl, bilirubin 1.5
  times the upper limit, SpO2 95%, more than 4 years since diagnosis. They
  cannot be changed on the parameters page.
- Options: move them into the parameter files (changes the files and the
  parameter pages), or keep them in the code as part of the published
  definitions of the risk factors.
- Status: open, decision of the author.

### m10. Purposes of random numbers could share their numbers (needs a decision)

- Where: `engine/draws.py` (`purpose`).
- What: a purpose name is reduced to a number modulo 1 000 003. Two names
  with the same number would get the same random numbers, so two decisions
  would be coupled. The 103 names in use today have no collision.
- Options: use a hash of the full name (e.g. 64 bits of SHA-256). This
  changes every generated patient for a given seed and needs a new
  calibration, so stored seeds give other patients than before.
- Status: open, decision of the author.

## Cosmetic

### c1. Wrong docstring of `generate.run`

- Where: `engine/generate.py`.
- What: says it yields (latent, plan, course, multipliers); it yields
  (latent, draws, regimen, course, multipliers).

### c2. The crosshair of a scatter plot has a fixed left edge

- Where: `app/explorer/static/explorer/charts.js` (`scatter`).
- What: the horizontal line starts at x = 50, a copy of the default margin of
  `frame()`; it would be wrong if the margin changed.

### c3. Small helpers are written several times in the engine

- Where: `engine/population.py`, `engine/interventions.py`, `engine/measurements.py`.
- What: `_sigmoid` and `_clip` exist twice each.

### c4. Fallback event rates in the observations have no explanation

- Where: `engine/measurements.py`.
- What: `rates.get("neutropenia", 0.05)` and similar use rates for regimens
  without a published rate of that event; the numbers are not explained.
