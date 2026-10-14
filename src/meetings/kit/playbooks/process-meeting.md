---
name: process-meeting
description: Turn a client meeting transcript into meeting notes, proposed requirement changes and a client confirmation email. Use when given a transcript from `meetings transcribe` or asked to process a meeting.
---

# Process a client meeting

Everything lives in `.meetings/` at the project root: `requirements/`, `meetings/`, `transcripts/`, `glossary.md`, `STATUS.md`. It is kept out of git on purpose. Never `git add` anything under it, never commit, never open a PR for this work.

Input: a transcript path, usually `.meetings/transcripts/<YYYY-MM-DD>-<slug>.json` (or `.md`). If none was given, list the newest files in `.meetings/transcripts/` and ask which one.

The transcript is machine-made from audio. Names, numbers, dates and technical words can be wrong. **Never invent or "fix" a requirement from guesswork.** Anything uncertain becomes an open question, not a requirement.

## Steps

1. **Read the context first**
   - The whole transcript. Take the meeting date from the file name (it is the recording date, not today).
   - Check `meta.mode`. If it is `single`, every line has the same speaker label: work out who is speaking from context, and when it matters (who asked for what, who agreed) and you are not sure, make it an open question.
   - All `.meetings/requirements/REQ-*.md`, the latest 2–3 files in `.meetings/meetings/`, and `.meetings/glossary.md`.
   - Note the highest existing REQ number; new IDs continue from it.

2. **Extract**, citing a transcript timestamp `[hh:mm:ss]` for every item:
   - Decisions made.
   - New requirements (what the client wants the system to do).
   - Changes to existing requirements (name the REQ ID).
   - Requirements the client dropped or put on hold.
   - Open questions: anything unclear, contradictory, or likely misheard. Quote the exact words.
   - Action items: who, what, by when (only if a date was said).
   - Ignore small talk.

3. **Check before you add**
   - For every "new" requirement, look for an existing one that already covers it. If one does, treat it as a change to that REQ, or skip it if nothing changed.
   - Compare names, products and technical words against the glossary. A word that looks like a mishearing of a glossary term (e.g. "jira" heard as "gyra") goes in open questions with your guess, never silently corrected.
   - Numbers, money, dates and deadlines: if the transcript is the only source, mark them for confirmation in the email.

4. **Write the meeting note** at `.meetings/meetings/<YYYY-MM-DD>-<slug>.md` using `.meetings/meetings/_template.md`. If a note for that meeting already exists, ask before overwriting.

5. **Update requirements**
   - New requirement → new file `.meetings/requirements/REQ-<NNN>-<slug>.md` from `.meetings/requirements/_template.md`, with `status: proposed`, `client_confirmed: no`, and `source:` pointing to the meeting note and timestamp. Keep the frontmatter on single lines; `meetings status` reads it.
   - Change to an existing requirement → do **not** rewrite it. Add a `## Proposed change (<date>)` section with the new wording, the reason, and the source. Leave status and acceptance criteria as they are.
   - Dropped requirement → add a `## Proposed change (<date>)` section saying the client wants it dropped. Do not change the status yourself.
   - Add a line under `## History` of every requirement you touched.
   - Never set `status: approved` or `client_confirmed: yes`. Only a human does that.

6. **Draft the client confirmation email** at `.meetings/meetings/<YYYY-MM-DD>-<slug>-confirmation.md`:
   - Short, plain, polite English. Short sentences. No jargon the client did not use.
   - "Here is what we understood from today's call" → numbered list of decisions and requirement changes, each with its REQ ID.
   - Then "Please confirm or correct" → the open questions, each a direct yes/no or short-answer question.
   - Do not send it. A human reviews and sends it.

7. **Run** `meetings status` to refresh `.meetings/STATUS.md`. If it reports errors in files you wrote, fix them. If the `meetings` command is not found, tell the user to install it (`uv tool install git+https://github.com/exarth-labs/meetspec`) and continue without it.

8. **Reply to the user**, short: number of new requirements, changed requirements, open questions, the files written, and anything that looked misheard.

## Rules

- Only what was said in the transcript. No assumptions about scope, prices, dates or technology.
- One requirement = one testable behavior. Split bundled asks.
- Write requirements from the client's point of view, in plain English. Acceptance criteria must be checkable: "Given …, when …, then …".
- Keep client data confidential: do not copy personal, medical, financial or payment data from the transcript into notes or requirements. Describe it ("the client shared a sample employee record") instead. Quote the transcript only in short pieces.
