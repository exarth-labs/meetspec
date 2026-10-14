# Contributing

Thanks for helping. Bug reports, fixes and improvements to the skills are all welcome.

## Setup

You need [uv](https://docs.astral.sh/uv/) and git.

```bash
git clone https://github.com/exarth-labs/ai-transcripter
cd ai-transcripter
uv sync
uv run pytest
```

Run the CLI from your checkout with `uv run meetings …`, or install it as an editable tool to use it in other projects:

```bash
uv tool install --editable .
```

## Layout

```text
src/meetings/
  cli.py          `meetings` entry point
  install.py      `meetings install`
  transcribe.py   `meetings transcribe`
  req_status.py   `meetings status`
  project.py      finds the project's .meetings/ folder
  kit/            files copied into projects: templates, glossary, README, Claude skills
tests/
```

## Guidelines

- Keep transcription local. No feature may send audio or transcripts over the network.
- Keep `meetings status` dependency-free beyond the standard library.
- Add or update tests for behaviour changes. Tests must not download models; keep model work behind functions that tests do not call.
- Skills in `src/meetings/kit/skills/` are instructions for Claude. Keep them short, specific and testable, and never let them approve requirements or commit `.meetings/` files.
- Never put real client names, recordings or transcripts in issues, tests or examples.
- Update `CHANGELOG.md` under "Unreleased".

## Pull requests

1. Fork and create a branch.
2. Make the change with tests.
3. `uv run pytest` passes.
4. Open a pull request describing what changed and why.

CI runs the tests on macOS, Windows and Linux.
