# ai-transcripter

Exarth meeting system: transcribe client calls locally, turn them into requirements, and check code against them.

Everything a project needs is in [`meetings-kit/`](meetings-kit/). How it works: [`meetings-kit/README.md`](meetings-kit/README.md).

## Install into a project

```bash
./install.sh /path/to/project
```

This copies the kit to `<project>/.meetings/` and the skills to `<project>/.claude/skills/`, and keeps both out of the project's git through `.git/info/exclude` (only on this machine; the project's `.gitignore` is not touched).

Run it again any time to update a project: scripts, templates and skills are replaced; requirements, meeting notes, transcripts and the glossary are left alone.
