# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Works with any AI coding agent: `meetings install` now adds `.meetings/AGENTS.md`, agent-neutral playbooks in `.meetings/playbooks/`, and a Cursor rule, alongside the Claude Code skills.
- `meetings status --json` and `meetings transcribe --json` for tools and agents; progress goes to stderr, results to stdout.
- Transcript JSON carries `"schema": "ai-transcripter/transcript/v1"`.
- Transcripts note when speakers were not separated.
- Not just Zoom: meeting dates are read from Google Meet and Microsoft Teams recording names too, and `--per-speaker` transcribes any folder of per-person tracks (Riverside, Zencastr, Craig for Discord, …).

### Fixed

- Transcription crashed with `av` 19 (`unexpected keyword argument 'metadata_errors'`); `av` is now pinned below 19.
- Python 3.14 is supported.

## [0.1.0] - 2026-10-14

### Added

- `meetings` command, installable with `uv tool install`, on macOS, Windows and Linux.
- `meetings install` sets up `.meetings/` and the Claude Code skills in a project and keeps them out of git through `.git/info/exclude`.
- `meetings transcribe` transcribes Zoom recordings locally with faster-whisper, per speaker when Zoom records separate audio files, with download and transcription progress.
- `meetings status` reports requirements against the code that references them.
- Claude Code skills: `/process-meeting`, `/implement-req`, `/req-check`.

[Unreleased]: https://github.com/exarth-labs/ai-transcripter/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/exarth-labs/ai-transcripter/releases/tag/v0.1.0
