# Exarth meeting system

Client call → local transcript → meeting notes + requirement changes → human approval → client confirmation → code linked to requirements → live status.

Requirements in this repo are the source of truth. Google Docs is only for sharing a copy with the client.

## The flow

1. **Zoom call.** Turn on live captions. Ask for recording consent at the start ("Is it OK if we record this so we don't miss anything?"). If something is unclear, ask on the call.
2. **Transcribe locally.** `python scripts/transcribe.py "<zoom folder>" --prompt "<client and product names>"`
3. **Process.** In Claude Code: `/process-meeting transcripts/<file>.json`
   It writes meeting notes, proposes requirement changes, drafts a confirmation email, and opens a docs PR.
4. **Review.** Lead checks the PR against the recording where anything looks wrong. Merge.
5. **Confirm with client.** Send the drafted email. When the client replies, set `client_confirmed: yes`, `confirmed_on:`, and `status: approved` on those requirements.
6. **Build.** `/implement-req REQ-012`
7. **Status.** A GitHub Action checks requirements against code on every PR and shows the report in the job summary; it fails the PR on errors. `python scripts/req_status.py` refreshes `docs/STATUS.md` locally (the skills run it too). Before a client update, run `/req-check` for a real check of code against acceptance criteria.

## One-time setup per computer

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
```

The first transcription downloads the model once (~3 GB for `large-v3`). After that it runs fully offline.

Speed: `large-v3` is the most accurate but slow on CPU. With an NVIDIA GPU use `--device cuda`. On CPU, try `--model distil-large-v3 --compute-type int8` for English-only meetings and compare quality on one real call.

## Zoom settings

Settings → Recording → **Local recording** → tick **Record a separate audio file for each participant**.

With this on, each speaker has their own file, so the transcript labels speakers by name with no guessing. The script finds the `Audio Record` folder automatically. Without it, the transcript still works but all lines get one label.

Rename speakers if needed with a small JSON map:

```json
{ "John Smith": "Client - John", "Ikram Khan": "Exarth - Ikram" }
```

`python scripts/transcribe.py "<folder>" --speakers speakers.json`

## Adding this to a project repo

Copy into the repo root:

- `scripts/` (transcribe, status check)
- `.claude/skills/` (process-meeting, req-check, implement-req)
- `docs/` (templates, glossary, this guide)
- `.github/workflows/req-status.yml`

Then:

- Add the lines from `gitignore-additions.txt` to `.gitignore`.
- Paste `CLAUDE-requirements-section.md` into the repo's `CLAUDE.md`.
- Commit.

## Requirement statuses

| Status | Meaning | Who sets it |
| --- | --- | --- |
| proposed | Heard in a meeting, not reviewed | Claude (`/process-meeting`) |
| approved | Lead reviewed and client confirmed | Lead |
| in-progress | Being built | Developer or Claude |
| done | Built, tested, reviewed | Lead |
| dropped | Client no longer wants it | Lead |

## Linking code to requirements

Put the ID in a comment at the feature's entry point, in at least one test name, and in the PR title:

```ts
// REQ-012: invoice CSV export
export async function exportInvoices() { … }

it("REQ-012 exports only the selected month", …)
```

`scripts/req_status.py` finds these and reports: requirements with no code, `done` with no code or tests, code referencing unknown or dropped requirements, and work not yet confirmed by the client. It checks that code is *linked*, not that it is *correct*; `/req-check` does the correctness review.

## Rules

- Transcripts and recordings stay on the company machine. They are in `.gitignore`. Never upload them to free tools.
- Machine transcripts make mistakes with names and numbers. Nothing becomes a requirement without a human review and client confirmation.
- Recording laws differ by country and US state; some require everyone's consent. Always ask at the start, and add a recording clause to the contract.
