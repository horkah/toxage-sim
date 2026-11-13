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
