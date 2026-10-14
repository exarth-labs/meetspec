---
name: process-meeting
description: Turn a client meeting transcript into meeting notes, proposed requirement changes and a client confirmation email, then open a docs PR for review. Use when given a transcript from scripts/transcribe.py or asked to process a meeting.
---

# Process a client meeting

Input: a transcript path, usually `transcripts/<date>-<name>.json` (or `.md`). If none was given, list the newest files in `transcripts/` and ask which one.

The transcript is machine-made from audio. Names, numbers, dates and technical words can be wrong. **Never invent or "fix" a requirement from guesswork.** Anything uncertain becomes an open question, not a requirement.

## Steps

1. **Read the context first**
   - The whole transcript.
   - `docs/requirements/` (all `REQ-*.md`), the latest 2–3 files in `docs/meetings/`, and `docs/glossary.md` if present.
   - Note the highest existing REQ number; new IDs continue from it.

2. **Extract**, citing a transcript timestamp `[hh:mm:ss]` for every item:
   - Decisions made.
   - New requirements (what the client wants the system to do).
   - Changes to existing requirements (name the REQ ID).
   - Requirements the client dropped or put on hold.
   - Open questions: anything unclear, contradictory, or likely misheard. Quote the exact words.
   - Action items: who, what, by when (only if a date was said).
   - Ignore small talk.

3. **Write the meeting note** at `docs/meetings/<YYYY-MM-DD>-<slug>.md` using `docs/meetings/_template.md`.

4. **Update requirements**
   - New requirement → new file `docs/requirements/REQ-<NNN>-<slug>.md` from `docs/requirements/_template.md`, with `status: proposed`, `client_confirmed: no`, and `source:` pointing to the meeting note and timestamp.
   - Change to an existing requirement → do **not** rewrite it. Add a `## Proposed change (<date>)` section with the new wording, the reason, and the source. Leave status and acceptance criteria as they are.
   - Dropped requirement → add a `## Proposed change (<date>)` section saying the client wants it dropped. Do not change the status yourself.
   - Never set `status: approved` or `client_confirmed: yes`. Only a human does that.

5. **Draft the client confirmation email** at `docs/meetings/<YYYY-MM-DD>-<slug>-confirmation.md`:
   - Short, plain, polite English. Short sentences. No jargon the client did not use.
   - "Here is what we understood from today's call" → numbered list of decisions and requirement changes.
   - Then "Please confirm or correct" → the open questions, each a direct yes/no or short-answer question.
   - Do not send it. A human reviews and sends it.

6. **Run** `python scripts/req_status.py` to refresh `docs/STATUS.md`.

7. **Open a docs PR**
   - Branch `docs/meeting-<YYYY-MM-DD>-<slug>`. Commit only files under `docs/`. Never commit anything from `transcripts/`.
   - Commit message: `docs: meeting notes <YYYY-MM-DD> <slug>`.
   - If `gh` is available and authenticated, open the PR with the summary below as the description. Otherwise stop after committing and tell the user the branch name.
   - Never push to `main`.

8. **Reply to the user** with: number of new requirements, changed requirements, open questions, and the PR link or branch. Point out anything that looked misheard.

## Rules

- Only what was said in the transcript. No assumptions about scope, prices, dates or technology.
- One requirement = one testable behavior. Split bundled asks.
- Write requirements from the client's point of view, in plain English.
- Keep client data confidential: do not copy personal, medical or payment data from the transcript into docs. Describe it ("the client shared a sample patient record") instead.
