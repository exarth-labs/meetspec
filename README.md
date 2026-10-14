# ai-transcripter

[![CI](https://github.com/exarth-labs/ai-transcripter/actions/workflows/ci.yml/badge.svg)](https://github.com/exarth-labs/ai-transcripter/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![macOS | Windows | Linux](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)

Turn client calls into requirements you can build against, without the audio ever leaving your machine.

`ai-transcripter` transcribes Zoom recordings locally with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), then hands the transcript to your AI coding agent (Claude Code, Codex, Cursor, Gemini CLI, Copilot, …) with playbooks to write meeting notes, propose requirements, draft a confirmation email for the client, implement approved requirements, and check that the code actually does what was agreed.

```text
Zoom call ──► meetings transcribe ──► /process-meeting ──► you review, client confirms
                (local, offline)        notes, REQ files,          │
                                        confirmation email         ▼
                    meetings status ◄── /implement-req REQ-012 ◄── approved requirement
                    /req-check          code + tests linked by ID
```

## Contents

- [Features](#features)
- [Install](#install)
- [Quick start](#quick-start)
- [Commands](#commands)
- [AI agents](#ai-agents)
- [Requirement files](#requirement-files)
- [Choosing a model](#choosing-a-model)
- [Zoom setup](#zoom-setup)
- [Privacy](#privacy)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Local transcription.** Audio is processed on your computer. After the one-time model download, nothing goes over the network.
- **Speakers by name.** With Zoom's per-participant audio, each line is labelled with who said it. No guessing.
- **Progress you can see.** Download progress in MB and transcription progress against the length of the call.
- **Requirements as files.** Each requirement is a Markdown file with a status, a client confirmation flag and acceptance criteria.
- **Code linked to requirements.** `REQ-012` in a comment or test name ties code to a requirement; `meetings status` reports what is missing.
- **Works with any AI agent.** An `AGENTS.md`, step-by-step playbooks, versioned JSON for transcripts and status, and `--json` output on the CLI. Claude Code skills and a Cursor rule are installed for you.
- **Stays out of your project's git.** Everything lives in a `.meetings/` folder hidden through `.git/info/exclude`, on your machine only. The project's `.gitignore` is never touched.
- **macOS, Windows and Linux.**

## Install

You need [git](https://git-scm.com/) and [uv](https://docs.astral.sh/uv/). uv installs Python for you if it is missing.

### 1. Install uv (once per computer)

macOS / Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows (PowerShell):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Install ai-transcripter

```bash
uv tool install git+https://github.com/exarth-labs/ai-transcripter
```

This adds the `meetings` command. Check it with `meetings --version`.

### Update

To get the latest version:

```bash
uv tool upgrade ai-transcripter
```

Then run `meetings install` again in each project to refresh its playbooks, skills and templates.

### Uninstall

`uv tool uninstall ai-transcripter`. Downloaded models stay in the Hugging Face cache (`~/.cache/huggingface/hub`); delete them there if you want the space back.

## Quick start

```bash
cd ~/code/client-project
meetings install                      # once per project

meetings transcribe "~/Documents/Zoom/2026-10-13 18.19.15 Kickoff" \
  --prompt "Acme, Stripe, HIPAA"      # names and words used in the call
```

Then ask your AI agent, inside the project:

| Agent | Say |
| --- | --- |
| Claude Code | `/process-meeting .meetings/transcripts/2026-10-13-kickoff.json` |
| Cursor | "Process the meeting in .meetings/transcripts/2026-10-13-kickoff.json" |
| Codex, Gemini CLI, others | "Follow .meetings/AGENTS.md to process .meetings/transcripts/2026-10-13-kickoff.json" |

Review the notes and proposed requirements it wrote in `.meetings/`, send the drafted confirmation email, and mark confirmed requirements `approved`. Then ask it to implement one: `/implement-req REQ-001` in Claude Code, or "implement REQ-001" elsewhere.

## Commands

### `meetings install [project]`

Sets up a project. Run it in the project folder (or pass the path). It must be a git repository.

| Creates | Purpose |
| --- | --- |
| `.meetings/requirements/` | Requirement files and their template |
| `.meetings/meetings/` | Meeting notes and confirmation emails |
| `.meetings/transcripts/` | Transcripts |
| `.meetings/glossary.md` | Names and technical words, for better spelling |
| `.meetings/README.md` | How the folder works, for people |
| `.meetings/AGENTS.md` | How the folder works, for AI agents |
| `.meetings/playbooks/` | Step-by-step instructions for each task |
| `.claude/skills/` | The playbooks as Claude Code skills |
| `.cursor/rules/meetings.mdc` | A Cursor rule pointing to `.meetings/AGENTS.md` |

All of it is added to `.git/info/exclude`, so git ignores it on this machine only. Running it again updates the templates, playbooks, skills and rule, and never touches your requirements, notes, transcripts or glossary.

### `meetings transcribe <input>`

Transcribes a Zoom recording folder or a single audio/video file (`.m4a`, `.mp3`, `.wav`, `.mp4`, `.mov`, …).

- A Zoom folder with an `Audio Record` subfolder is transcribed per speaker, with names from the file names.
- Otherwise the best single file is used (the audio-only file if there is one), and every line gets one label.

Output goes to `.meetings/transcripts/` inside a project, or `./transcripts/` elsewhere: a readable `.md` and a `.json` for the skills. The file name uses the meeting date from the Zoom folder name.

| Option | Default | |
| --- | --- | --- |
| `--model` | `large-v3` | See [Choosing a model](#choosing-a-model) |
| `--language` | `en` | Language code, or `auto` to detect |
| `--prompt` | | Names and terms used in the call; improves their spelling |
| `--speakers` | | JSON file mapping detected names to labels, e.g. `{"John Smith": "Client - John"}` |
| `--label` | `Speaker` | Label for single-file recordings |
| `--device` | `auto` | `cpu` or `cuda` |
| `--compute-type` | `int8` on CPU | e.g. `float16` on GPU |
| `--out` | | Output folder |
| `--no-vad` | | Keep silent parts (try this if speech is missing) |
| `--json` | | Print the result (file paths, line count, speakers) as JSON |

### `meetings status`

Scans the project for requirement IDs and writes `.meetings/STATUS.md`: every requirement with its status, client confirmation, code and test references, and problems such as:

- code that references a requirement that does not exist
- a requirement marked `done` with no code or no tests
- code written for a requirement that is still `proposed` or already `dropped`
- approved work not yet confirmed by the client

`--stdout` prints the report instead; `--json` prints it as JSON without writing anything; `--check` exits with status 1 when there are errors. It checks that code is *linked*, not that it is *correct*. That is what the `req-check` playbook is for.

## AI agents

Everything an agent needs is in plain files, so any coding agent can do the work.

| Playbook | What the agent does |
| --- | --- |
| `process-meeting` | Writes the meeting note, proposes new and changed requirements (each citing a transcript timestamp), lists open questions, and drafts a client confirmation email. It never approves anything itself. |
| `implement-req` | Refuses unapproved requirements, plans the work against the acceptance criteria, builds on a branch, links code and tests to the ID, and reports each criterion as met or not. |
| `req-check` | Read-only review of whether the code really meets each requirement's acceptance criteria. Use it before a client update or release. |

**How each agent finds them**

| Agent | How |
| --- | --- |
| Claude Code | Installed as skills: `/process-meeting`, `/implement-req`, `/req-check`. |
| Cursor | Installed rule `.cursor/rules/meetings.mdc` sends it to `.meetings/AGENTS.md` when you mention meetings, transcripts or requirements. |
| Codex, Gemini CLI, Copilot, Aider, others | Tell it to follow `.meetings/AGENTS.md`. To make that automatic, add one line to your own instructions file (`AGENTS.md`, `GEMINI.md`, …): `For client meetings and REQ-### requirements, follow .meetings/AGENTS.md.` |
| ChatGPT or Claude in the browser | Upload the transcript `.md` (or `.json`) together with the playbook `.md` you want it to follow. |

**For tool builders**, the formats are stable and versioned:

- Transcripts: `.meetings/transcripts/*.json` with `"schema": "ai-transcripter/transcript/v1"`, a `meta` block and `segments` of `{start, end, speaker, text}` (seconds from the start of the recording).
- Status: `meetings status --json` with `"schema": "ai-transcripter/status/v1"`, a `summary`, every requirement with its code and test references, and `problems`.
- CLI: progress goes to stderr, results to stdout. `meetings status --check` exits with 1 when there are errors.

The full description an agent reads is in [`src/meetings/kit/AGENTS.md`](src/meetings/kit/AGENTS.md).

Transcripts are machine-made. The playbooks treat names, numbers and dates as uncertain and turn anything unclear into a question for the client rather than a requirement.

## Requirement files

`.meetings/requirements/REQ-012-invoice-export.md`:

```markdown
---
id: REQ-012
title: Export invoices as CSV
status: approved          # proposed | approved | in-progress | done | dropped
client_confirmed: yes
confirmed_on: 2026-10-15
source: .meetings/meetings/2026-10-13-kickoff.md [00:14:32]
owner: Ikram
---

# REQ-012: Export invoices as CSV

## What the client wants
...

## Acceptance criteria
- [ ] Given a month is selected, when I export, then only that month's invoices are included
```

Link code to it with the ID in a comment at the feature's entry point and in at least one test name: `// REQ-012`, `it("REQ-012 …")` or `def test_req_012_…()`.

| Status | Meaning | Set by |
| --- | --- | --- |
| `proposed` | Heard in a meeting, not reviewed | `/process-meeting` |
| `approved` | Reviewed and confirmed by the client | A person |
| `in-progress` | Being built | Developer or `/implement-req` |
| `done` | Built, tested and reviewed | A person |
| `dropped` | No longer wanted | A person |

## Choosing a model

Models download once on first use (to `~/.cache/huggingface/hub`) and are shared by every project.

| Model | Size | Notes |
| --- | --- | --- |
| `large-v3` | ~3 GB | Most accurate, any language. Slow on CPU. |
| `turbo` | ~1.6 GB | Close to `large-v3`, much faster. Good default for mixed languages. |
| `distil-large-v3` | ~1.5 GB | Fast and accurate, **English only**. |
| `small`, `base`, `tiny` | 75–500 MB | Quick tests. Expect mistakes. |

On a laptop without an NVIDIA GPU, start with `--model distil-large-v3` for English calls or `--model turbo` otherwise, and compare against `large-v3` on one real call.

## Zoom setup

Settings → Recording → **Local recording** → tick **Record a separate audio file for each participant**.

Zoom then writes an `Audio Record` folder with one file per person, and the transcript labels every line with the speaker's name. Without it you still get a transcript; speakers are just not separated.

## Privacy

- Recordings and transcripts are read and written only on your computer. The only network access is downloading the model from Hugging Face the first time.
- `.meetings/` is excluded from git, so transcripts and notes are never committed by accident. That also means **they are not backed up**. Back the folder up yourself if you need to.
- Recording laws differ by country and state, and some require everyone's consent. Ask at the start of every call.

See [SECURITY.md](SECURITY.md) to report a vulnerability.

## Troubleshooting

**`Operation not permitted` on macOS.** macOS blocks terminal apps from `Documents`, `Desktop` and `Downloads` until you allow it: System Settings → Privacy & Security → Files and Folders → your terminal app (Terminal, iTerm, VS Code) → enable the folder. Quit and reopen the app. Or copy the recording somewhere else.

**Transcription is slow.** Use a smaller model (see above). On CPU the default `int8` compute type is already the fastest.

**Windows with an NVIDIA GPU fails to start.** GPU mode needs the CUDA 12 and cuDNN 9 libraries. Install them, or run with `--device cpu`.

**"You are sending unauthenticated requests to the HF Hub".** Harmless. Set `HF_TOKEN` to a free Hugging Face token if downloads are slow.

**Words or names are wrong.** Pass them with `--prompt`, and add them to `.meetings/glossary.md` so `/process-meeting` can spot mishearings.

**`No .meetings/ folder here`.** Run `meetings install` in the project root first.

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
