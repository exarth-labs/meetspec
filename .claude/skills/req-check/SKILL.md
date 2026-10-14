---
name: req-check
description: Check whether the code actually does what the requirements say. Use when asked for project status, "docs vs code", whether a requirement is done, or before a client update or release.
---

# Requirements vs code check

`scripts/req_status.py` only knows whether code *mentions* a REQ ID. This skill checks whether the code *does* what the requirement says.

## Steps

1. Run `python scripts/req_status.py --stdout` and read the result.
2. Pick the requirements to check:
   - If the user named IDs, check those.
   - Otherwise check every requirement with status `in-progress` or `done`, plus any with errors in the report.
3. For each one:
   - Read its file in `docs/requirements/`, especially the acceptance criteria and any `Proposed change` sections.
   - Read the code and tests that reference it (paths are in the report; search for the ID).
   - Judge each acceptance criterion: **met**, **partly met**, **not met**, or **can't tell** (say what is missing to tell).
   - Note conflicts: code doing something the requirement does not ask for, or an approved change not yet in the code.
4. Do not change any code or requirement files. This is a read-only check.
5. Report to the user, shortest useful form:
   - One line overall: how many requirements are fully met, partly met, not met.
   - A table: ID · title · verdict · the one most important gap.
   - Then the details only for requirements that are not fully met, with file:line references.
   - Flag requirements marked `done` that are not actually met. These matter most before a client update.
