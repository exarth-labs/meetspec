# Agent instructions for this repository

This repo builds the `meetings` CLI (Python package `meetspec`, source in `src/meetings/`). For what the tool does, read `README.md`; for layout and rules, `CONTRIBUTING.md`.

- Set up and test with uv: `uv sync`, then `uv run pytest`. `RUN_E2E=1 uv run pytest` also runs a real transcription (downloads a ~75 MB model once).
- Run the CLI from the checkout with `uv run meetings …`.
- `src/meetings/kit/` is copied into users' projects by `meetings install`. `kit/AGENTS.md` and `kit/playbooks/` are instructions for agents working in *those* projects, not in this one.
- Keep transcription local: nothing may send audio or transcripts over the network.
- `meetings status` must stay standard-library only.
- The JSON schemas `meetspec/transcript/v1` and `meetspec/status/v1` are public: add fields, never rename or remove them without a new version.
- Never add real client names, recordings or transcripts to code, tests, docs or examples. `tests/fixtures/speech.m4a` is a synthetic voice.
- Update `CHANGELOG.md` under "Unreleased" for user-visible changes.
