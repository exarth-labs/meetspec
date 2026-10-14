---
name: req-check
description: Check whether the code actually does what the requirements say. Use when asked for project status, "docs vs code", whether a requirement is done, or before a client update or release.
---

# Requirements vs code check

`meetings status` only knows whether code *mentions* a REQ ID. This playbook checks whether the code *does* what the requirement says.

Requirements live in `.meetings/requirements/` at the project root. `.meetings/` is kept out of git on purpose: never `git add` anything under it.

This is a read-only check. Do not change any code or requirement files.

## Steps

1. Run `meetings status --stdout` and read the result. If the `meetings` command is not found, search the code for each REQ ID yourself and mention that the tool is not installed.
2. Pick the requirements to check:
   - If the user named IDs, check those.
   - Otherwise check every requirement with status `in-progress` or `done`, plus any with errors in the report.
3. For each one:
   - Read its file, especially the acceptance criteria and any `Proposed change` sections.
   - Read the code and tests that reference it (paths are in the report), then search around them: the feature may span files that do not mention the ID.
   - Judge each acceptance criterion: **met**, **partly met**, **not met**, or **can't tell** (say what is missing to tell). "Met" needs code that does it; say whether a test also proves it.
   - If the project's tests can be run quickly, run the ones that reference the ID and use the result. Say when you did not run them.
   - Note conflicts: code doing something the requirement does not ask for, or an approved change not yet in the code.
4. Report to the user, shortest useful form:
   - One line overall: how many requirements are fully met, partly met, not met.
   - A table: ID · title · verdict · the one most important gap.
   - Then details only for requirements that are not fully met, with file:line references.
   - Flag requirements marked `done` that are not actually met, and work not yet confirmed by the client. These matter most before a client update.
