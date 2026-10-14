"""`meetings` command: install, transcribe, status."""

from __future__ import annotations

import sys
from importlib.metadata import version

USAGE = """usage: meetings <command> [options]

Transcribe client calls locally and track requirements.

commands:
  install [project]     set up .meetings/ and the Claude skills in a project (run again to update)
  transcribe <input>    transcribe a Zoom recording folder or audio/video file
  status                check requirements against code, write .meetings/STATUS.md

Run `meetings <command> --help` for a command's options.
"""


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help", "help"}:
        print(USAGE)
        return
    if args[0] in {"-V", "--version"}:
        print(f"meetings {version('exarth-meetings')}")
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
    run(rest, prog=f"meetings {command}")
