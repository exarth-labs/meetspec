---
name: implement-req
description: Implement an approved requirement by its REQ ID, linking code and tests back to it. Use when asked to implement, build or work on REQ-###.
---

# Implement a requirement

Input: one REQ ID, e.g. `REQ-012`.

Requirements live in `.meetings/requirements/` at the project root. `.meetings/` is kept out of git on purpose: never `git add` anything under it.

1. **Read** `.meetings/requirements/REQ-012-*.md`, the project's `CLAUDE.md` / `AGENTS.md`, and any meeting note in its `source:`.
2. **Check it is ready.**
   - `status` must be `approved` or `in-progress`. If it is `proposed`, `done` or `dropped`, stop and say why.
   - If `client_confirmed` is not `yes`, warn the user and ask whether to continue.
   - If there is an unapproved `Proposed change` section, ask which version to build.
   - If acceptance criteria are missing, vague or not testable, ask. Do not guess.
3. **Plan.** Read the related code, then tell the user the plan: files to change, approach, and which test covers each acceptance criterion. Wait for approval if the change is large or the project's instructions ask for it.
4. **Build** on a new branch. Use the project's branch convention if it documents one; otherwise `feature/req-012-<slug>`. Never build on `main` or a release branch.
5. **Link it.**
   - Put `REQ-012` in a short comment at the main entry point of the feature (not on every line).
   - Name at least one test with the ID, e.g. `it("REQ-012 rejects expired invoices")` / `def test_req_012_rejects_expired_invoices()`.
   - Put `REQ-012` in the commit message and PR title.
6. **Status.** Set the requirement's `status` to `in-progress` when you start and add a `## History` line. Do not set `done`; the lead does that after review.
7. **Verify.** Run the project's lint, typecheck and tests, then `meetings status`.
8. **Report**, short: each acceptance criterion as met / not met with the test that proves it, test results as they actually came out, and anything left open.
