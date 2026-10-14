"""`meetings` command: install, transcribe, status."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

USAGE = """usage: meetings <command> [options]

Transcribe client calls locally and track requirements.

commands:
  install [project]     set up .meetings/ and the AI agent playbooks in a project (run again to update)
  transcribe <input>    transcribe a meeting recording (any audio/video file or recording folder)
  status                check requirements against code, write .meetings/STATUS.md

Run `meetings <command> --help` for a command's options.
"""


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help", "help"}:
        print(USAGE)
        return
    if args[0] in {"-V", "--version"}:
        try:
            print(f"meetings {version('meetspec')}")
        except PackageNotFoundError:
            print("meetings (not installed as a package)")
        return

    command, rest = args[0], args[1:]
    if command == "install":
        from .install import main as run
    elif command == "transcribe":
        from .transcribe import main as run
    elif command == "status":
        from .req_status import main as run
    else:
        sys.exit(f"Unknown command: {command}\n\n{USAGE}")
    try:
        run(rest, prog=f"meetings {command}")
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(130)
