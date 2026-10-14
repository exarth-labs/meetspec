---
name: implement-req
description: Implement an approved requirement by its REQ ID, linking code and tests back to it. Use when asked to implement, build or work on REQ-###.
---

# Implement a requirement

Input: one REQ ID, e.g. `REQ-012`.

1. Read `docs/requirements/REQ-012-*.md` and `CLAUDE.md`.
2. **Check it is ready.**
   - `status` must be `approved` or `in-progress`. If it is `proposed`, stop: it has not been approved.
   - If `client_confirmed` is not `yes`, warn the user and ask whether to continue.
   - If there is an unapproved `Proposed change` section, ask which version to build.
   - If acceptance criteria are missing or unclear, ask. Do not guess.
3. **Plan.** Read the related code, then tell the user the plan (files, approach, tests) and wait for approval if the change is large (per CLAUDE.md).
4. **Build** on a branch `feature/req-012-<slug>`, following CLAUDE.md.
5. **Link it.**
   - Put `REQ-012` in a short comment at the main entry point of the feature (not on every line).
   - Name at least one test with the ID, e.g. `it("REQ-012 rejects expired invoices")` / `def test_req_012_rejects_expired_invoices()`.
   - Put `REQ-012` in the PR title.
6. Set the requirement's `status` to `in-progress` while working. Do not set `done`; the lead does that after review.
7. Run lint, typecheck, tests and `python scripts/req_status.py`. Report results.
