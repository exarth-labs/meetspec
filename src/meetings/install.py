"""
Install (or update) the meetings kit into a project, kept out of its git.

Creates <project>/.meetings/ with AGENTS.md, the task playbooks, templates, glossary, README
and empty folders, then makes the playbooks discoverable by coding agents:
  .claude/skills/<name>/SKILL.md   Claude Code skills (/process-meeting, ...)
  .cursor/rules/meetings.mdc       Cursor rule pointing to .meetings/AGENTS.md
Other agents (Codex, Gemini CLI, Copilot, ...) read .meetings/AGENTS.md when pointed to it.

Everything installed is added to the repo's .git/info/exclude (like .gitignore, but only on
this machine; the project's .gitignore is not touched).

Safe to run again to update: AGENTS.md, playbooks, templates, README, skills and the rule are
replaced; requirements, meeting notes, transcripts, glossary and STATUS.md are never touched.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from importlib.resources import as_file, files
from pathlib import Path

from .project import DIR_NAME

PLAYBOOKS = ("process-meeting", "implement-req", "req-check")
CURSOR_RULE = ".cursor/rules/meetings.mdc"


def git(project: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True, check=True)
    except FileNotFoundError:
        sys.exit("git is not installed or not on PATH.")
    except subprocess.CalledProcessError:
        sys.exit(f"Not a git repository: {project}")
    return out.stdout.strip()


def add_excludes(project: Path, lines: list[str]) -> Path:
    exclude = Path(git(project, "rev-parse", "--git-path", "info/exclude"))
    if not exclude.is_absolute():
        exclude = project / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
    missing = [line for line in lines if line not in existing]
    if missing:
        with exclude.open("a", encoding="utf-8") as fh:
            if existing and existing[-1].strip():
                fh.write("\n")
            fh.write("# ai-transcripter (local only)\n")
            fh.write("".join(f"{line}\n" for line in missing))
    return exclude


def install(project: Path) -> None:
    project = Path(git(project, "rev-parse", "--show-toplevel"))
    base = project / DIR_NAME
    skills_dir = project / ".claude" / "skills"

    with as_file(files("meetings") / "kit") as kit:
        for sub in ("requirements", "meetings", "transcripts", "playbooks"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        for rel in ("AGENTS.md", "README.md", "requirements/_template.md", "meetings/_template.md"):
            shutil.copyfile(kit / rel, base / rel)
        if not (base / "glossary.md").exists():
            shutil.copyfile(kit / "glossary.md", base / "glossary.md")

        for name in PLAYBOOKS:
            shutil.copyfile(kit / "playbooks" / f"{name}.md", base / "playbooks" / f"{name}.md")
            skill = skills_dir / name
            shutil.rmtree(skill, ignore_errors=True)
            skill.mkdir(parents=True)
            shutil.copyfile(kit / "playbooks" / f"{name}.md", skill / "SKILL.md")

        rule = project / CURSOR_RULE
        rule.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(kit / "cursor-rule.mdc", rule)

    ours = [f"{DIR_NAME}/", *(f".claude/skills/{name}/" for name in PLAYBOOKS), CURSOR_RULE]
    exclude = add_excludes(project, ours)

    print(f"Installed into {project}")
    print(f"  {DIR_NAME}/              AGENTS.md, playbooks, templates, glossary; your requirements and notes")
    print(f"  .claude/skills/        {', '.join(PLAYBOOKS)} (Claude Code)")
    print(f"  {CURSOR_RULE}  (Cursor)")
    print(f"  other agents: tell them to follow {DIR_NAME}/AGENTS.md")
    print(f"  kept out of git via {exclude}")
    if (base / "scripts").is_dir():
        print(f"  note: {DIR_NAME}/scripts/ is from the old kit and no longer used; you can delete it "
              f"(and {DIR_NAME}/.venv/ if present).")
    if git(project, "status", "--porcelain", "--untracked-files=all", "--", *ours):
        print(f"WARNING: git still sees some of these files. Check `git -C \"{project}\" status`.", file=sys.stderr)


def main(argv: list[str] | None = None, prog: str | None = None) -> None:
    parser = argparse.ArgumentParser(prog=prog, description="Install or update the meetings kit in a project.")
    parser.add_argument("project", type=Path, nargs="?", default=Path("."),
                        help="project folder (default: current folder)")
    args = parser.parse_args(argv)
    install(args.project.expanduser().resolve())
