# Security

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's [private vulnerability reporting](https://github.com/exarth-labs/meetspec/security/advisories/new) instead. We aim to reply within a week.

## What this tool does with your data

- Audio and transcripts are processed locally. The only network request is downloading the speech model from Hugging Face on first use.
- `meetings install` adds `.meetings/`, the skills and the agent rule to `.git/info/exclude`, so transcripts, notes and requirements are not committed.
- When your AI agent (Claude Code, Codex, Cursor, …) follows a playbook, it reads the transcript like any other file in your project, and that content goes to the agent's provider under your own account's terms. Do not use an agent on recordings you are not allowed to share with that provider.
