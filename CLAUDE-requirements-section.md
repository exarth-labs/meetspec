## Requirements and meetings

<!-- Paste this section into the repo's CLAUDE.md -->

- Requirements live in `docs/requirements/REQ-###-*.md`. They are the source of truth for what to build.
- Only build requirements with `status: approved` or `in-progress`. If asked to build something with no approved requirement, say so and ask.
- Link work to requirements: `REQ-###` in a comment at the feature's entry point, in at least one test name, and in the PR title.
- Never set a requirement to `approved`, `done` or `client_confirmed: yes`. Humans do that.
- `transcripts/` holds confidential client conversations. Never commit, quote at length, or send them anywhere.
- Skills: `/process-meeting` after a client call, `/implement-req REQ-###` to build, `/req-check` for status.
