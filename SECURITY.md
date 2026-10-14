# Security

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's [private vulnerability reporting](https://github.com/exarth-labs/ai-transcripter/security/advisories/new) instead. We aim to reply within a week.

## What this tool does with your data

- Audio and transcripts are processed locally. The only network request is downloading the speech model from Hugging Face on first use.
- `meetings install` adds `.meetings/` and the installed skills to `.git/info/exclude`, so transcripts, notes and requirements are not committed.
- The Claude Code skills read transcripts as part of your Claude Code session. That content is sent to Anthropic under your own Claude account's terms, like any other file Claude Code reads. Do not use the skills on recordings you are not allowed to share with that service.
