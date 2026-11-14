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

### m4. Whole-number parameters accept fractions (needs a decision)

- Where: `app/explorer/params.py` (`parse`).
- What: a value keeps the type of its default, but a fraction is accepted
  where the default is a whole number: 2.5 for `simulation/weeks` is saved
  and fails only when a data set is generated (with a clear message, as the
  parameters page now tries every change on a small cohort). A whole number in the parameter files does not always mean "only
  whole numbers", though: costs such as 800 euros per hospital day may well
  get cents, so a general rule would be wrong.
- Options: mark the parameters that must be whole numbers (weeks, days,
  counts) in the parameter files, e.g. with a key "integer": true next to the
  value, and refuse fractions there; or rely on the check that every change
  now gets on a small cohort.
- Status: open, decision of the author.

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

None open.
