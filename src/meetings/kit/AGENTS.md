# Instructions for AI agents

This `.meetings/` folder holds client meeting transcripts, meeting notes and requirements for the project one level up. It was created by [ai-transcripter](https://github.com/exarth-labs/ai-transcripter). Any coding agent (Claude Code, Codex, Cursor, Gemini CLI, Copilot, …) can follow these instructions.

## Hard rules

- **Never commit, stage or push anything under `.meetings/`.** It is excluded from git on purpose and holds confidential client conversations.
- **Never set `status: approved`, `status: done` or `client_confirmed: yes`.** Only a person does that.
- **Transcripts are machine-made.** Names, numbers, dates and technical words can be wrong. Never invent or "fix" a requirement from guesswork; turn anything uncertain into an open question.
- Do not copy personal, medical, financial or payment data from transcripts into notes or requirements. Describe it instead. Quote transcripts only in short pieces.
- Only build requirements whose status is `approved` or `in-progress`.

## Tasks

Each task has a step-by-step playbook. Read it fully before starting.

| When the user asks to… | Follow |
| --- | --- |
| process a meeting / transcript, write meeting notes, update requirements after a call | [`playbooks/process-meeting.md`](playbooks/process-meeting.md) |
| implement / build / work on `REQ-###` | [`playbooks/implement-req.md`](playbooks/implement-req.md) |
| check status, "docs vs code", whether a requirement is done, before a client update or release | [`playbooks/req-check.md`](playbooks/req-check.md) |

## Folder layout

```text
.meetings/
  AGENTS.md                 this file
  playbooks/                step-by-step task instructions
  transcripts/<date>-<slug>.json / .md
  meetings/<date>-<slug>.md                 meeting note (template: meetings/_template.md)
  meetings/<date>-<slug>-confirmation.md    draft email to the client
  requirements/REQ-###-<slug>.md            one requirement per file (template: requirements/_template.md)
  glossary.md               correct spellings of names, products and terms
  STATUS.md                 generated; do not edit
```

## Transcript format

`transcripts/<date>-<slug>.json` (read this one; the `.md` is the same content for people):

```json
{
  "schema": "ai-transcripter/transcript/v1",
  "meta": {
    "source_name": "2026-10-13 18.19.15 Kickoff",
    "transcribed_at": "2026-10-14T10:00:00",
    "mode": "per-speaker",
    "model": "large-v3",
    "language": "en",
    "speakers": ["Client - John", "Team - Ikram"],
    "files": ["audioJohnSmith11.m4a", "audioIkramKhan22.m4a"]
  },
  "segments": [
    { "start": 872.4, "end": 879.1, "speaker": "Client - John", "text": "We need the invoices as CSV by Friday." }
  ]
}
```

- `start` / `end` are seconds from the start of the recording. Cite them as `[hh:mm:ss]`.
- `mode` is `per-speaker` when each person had their own audio file (speaker names are reliable) or `single` (one label for everyone; infer speakers from context and say so).
- The date in the file name is the meeting date.

## Requirement format

YAML-style frontmatter, one `key: value` per line, then Markdown:

```markdown
---
id: REQ-012
title: Export invoices as CSV
status: proposed          # proposed | approved | in-progress | done | dropped
client_confirmed: no      # yes only after written client confirmation
confirmed_on:
source: .meetings/meetings/2026-10-13-kickoff.md [00:14:32]
owner:
---
```

Sections: `What the client wants`, `Acceptance criteria` (checkable "Given … when … then …" items), `Notes`, `History`. Changes to an existing requirement go in a new `## Proposed change (<date>)` section; never rewrite an approved requirement.

Link code to a requirement by putting its ID in a comment at the feature's entry point and in at least one test name: `// REQ-012`, `it("REQ-012 …")`, `def test_req_012_…()`.

## Commands

The `meetings` command may be installed (`uv tool install git+https://github.com/exarth-labs/ai-transcripter`). Run it from anywhere inside the project. Progress goes to stderr; results go to stdout.

| Command | Use |
| --- | --- |
| `meetings status --json` | Requirements, their code/test references and problems, as JSON. Read-only. |
| `meetings status` | Same check; writes `STATUS.md`. Exit code 1 with `--check` when there are errors. |
| `meetings transcribe <recording file or folder> --json` | Transcribe locally; prints the output paths as JSON. Slow; only run it when the user asks. |

If `meetings` is not installed, do the same work by reading the files directly.
