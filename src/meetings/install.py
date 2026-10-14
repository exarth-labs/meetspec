"""
Install (or update) the meetings kit into a project, kept out of its git.

Creates <project>/.meetings/ (templates, glossary, README and empty folders) and copies the
skills to <project>/.claude/skills/, then adds both to the repo's .git/info/exclude
(like .gitignore, but only on this machine; the project's .gitignore is not touched).

Safe to run again to update: templates, README and skills are replaced;
requirements, meeting notes, transcripts, glossary and STATUS.md are never touched.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from importlib.resources import as_file, files
from pathlib import Path

from .project import DIR_NAME

SKILLS = ("process-meeting", "implement-req", "req-check")


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
        for sub in ("requirements", "meetings", "transcripts"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(kit / "requirements" / "_template.md", base / "requirements" / "_template.md")
        shutil.copyfile(kit / "meetings" / "_template.md", base / "meetings" / "_template.md")
        shutil.copyfile(kit / "README.md", base / "README.md")
        if not (base / "glossary.md").exists():
            shutil.copyfile(kit / "glossary.md", base / "glossary.md")

        skills_dir.mkdir(parents=True, exist_ok=True)
        for name in SKILLS:
            shutil.rmtree(skills_dir / name, ignore_errors=True)
            shutil.copytree(kit / "skills" / name, skills_dir / name)

    exclude = add_excludes(project, [f"{DIR_NAME}/", *(f".claude/skills/{name}/" for name in SKILLS)])

    print(f"Installed into {project}")
    print(f"  {DIR_NAME}/         templates, glossary, your requirements and notes")
    print(f"  .claude/skills/   {', '.join(SKILLS)}")
    print(f"  kept out of git via {exclude}")
    if (base / "scripts").is_dir():
        print(f"  note: {DIR_NAME}/scripts/ is from the old kit and no longer used; you can delete it "
              f"(and {DIR_NAME}/.venv/ if present).")
    leaked = git(project, "status", "--porcelain", "--", DIR_NAME, ".claude/skills")
    if any(name in leaked for name in (DIR_NAME, *SKILLS)):
        print(f"WARNING: git still sees some of these files. Check `git -C \"{project}\" status`.", file=sys.stderr)


def main(argv: list[str] | None = None, prog: str | None = None) -> None:
    parser = argparse.ArgumentParser(prog=prog, description="Install or update the meetings kit in a project.")
    parser.add_argument("project", type=Path, nargs="?", default=Path("."),
                        help="project folder (default: current folder)")
    args = parser.parse_args(argv)
    install(args.project.expanduser().resolve())
