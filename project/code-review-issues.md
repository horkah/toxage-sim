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
- Decision of the author: keep as is. The README names the missing login as
  a limit; a public installation can run with `TOXAGE_READ_ONLY=1`.

## Minor

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
