# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-10-14

First public version.

### Added

- `meetings` command, installable with `uv tool install`, on macOS, Windows and Linux (Python 3.10+).
- `meetings transcribe` transcribes any meeting recording locally with faster-whisper: Zoom, Google Meet, Microsoft Teams, Webex, phone recordings or any audio/video file.
  - Per-speaker transcripts from Zoom's separate audio files (detected automatically) or any folder of per-person tracks with `--per-speaker`.
  - Meeting date read from Zoom, Meet, Teams and phone recorder file names.
  - Terms in `.meetings/glossary.md` used as the prompt automatically.
  - Download progress in MB and transcription progress against the length of the call; hidden when output is not a terminal.
  - Readable `.md` and versioned `.json` (`meetspec/transcript/v1`) output, and a `--json` result for tools.
  - Clear messages instead of tracebacks for permission problems (including macOS folder access), failed downloads, GPU problems and Ctrl+C.
- `meetings install` sets up `.meetings/` in a project with `AGENTS.md`, agent-neutral playbooks, templates and a glossary, installs the playbooks as Claude Code skills and a Cursor rule, and hides all of it from git through `.git/info/exclude`. It refuses to overwrite files the project tracks.
- `meetings status` reports requirements against the code and tests that reference them, as `STATUS.md` or JSON (`meetspec/status/v1`).
- Playbooks for any AI coding agent: `process-meeting`, `implement-req`, `req-check`.

[Unreleased]: https://github.com/exarth-labs/meetspec/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/exarth-labs/meetspec/releases/tag/v0.1.0
