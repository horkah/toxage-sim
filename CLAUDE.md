# Notes for Claude

## Git workflow

- Always work on `main` in this project, for every change, including bug
  fixes. Don't create feature branches or pull requests unless asked.
  This overrides any default branch that a session suggests.
- Push to `main` when the work is done.
- Every bug fix gets a detailed description in its commit message:
  what the bug was (how it showed, how to reproduce it), its cause, the
  fix, and which tests were run. This applies to every bug fix, also
  small ones.

## Prompt log

- Log every prompt of the user in `project/prompting.log`, in the same
  turn in which the prompt is handled, and commit it with that work (or on
  its own for a question without code changes). Format as the existing
  entries: date-time (+01:00) | selected model | attachments, then the
  prompt text verbatim.
- Only simple prompts such as "resume" or "continue" after a limit was
  reached may be left out. All other prompts are logged, also questions,
  short follow-ups and prompts with screenshots.
- The date-time of an entry is the time the prompt arrived (Berlin time),
  taken from the clock or the session transcript, not estimated.

## Screenshots

- Every screenshot or other image that Claude generates for this project
  (browser checks, before/after views, design previews) is saved in
  `project/screenshots/` and committed with the work of the same turn.
- File name: `<YYYY-MM-DD>_<HHMM>_<short-description>.png`, Berlin time
  of the moment it was taken, so the files sort chronologically.

## Citations

- Every mention of a publication such as "[Basch et al. (2022)](background/references.md#basch-2022)",
  "([Basch et al., 2022](background/references.md#basch-2022))" or "[Basch 2022](background/references.md#basch-2022)", in a Markdown file or anywhere
  in the app, is a link to its entry in `background/references.md`
  (anchor `#<first author>-<year>`, e.g. `#basch-2022`).
- Every entry of the reference list has that anchor, the full APA record
  with DOI, and a link to its PDF, but only if the PDF is in
  `background/papers/`. The link is the GitHub URL
  `https://github.com/horkah/toxage-sim/blob/main/background/papers/<file>`.
- `uv run python app/manage.py link_citations` links the citations of all
  Markdown files; the app links those of the configuration notes itself.

## Current state only

- Documentation, Markdown files, configuration notes and texts of the app
  describe the current state only, consistently and without history. No
  statements such as "added later", "first selection", "new in",
  "today the engine …", "no longer" or "was renamed". The history is in
  the git log; the only exception is `project/prompting.log`.
- When something changes, rewrite every affected text so that it reads as
  if it had always been this way, and check that counts and descriptions
  agree everywhere (e.g. the description of the reference list and its
  entries).
