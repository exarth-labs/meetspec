#!/usr/bin/env python3
"""
Requirements vs code status check (Exarth meeting system).

Reads every docs/requirements/REQ-*.md file, scans the codebase for REQ-### references,
and writes docs/STATUS.md showing which requirements have code, which have tests,
and where docs and code disagree.

How code links to a requirement: put the ID anywhere in the code or test,
for example a comment `// REQ-012` or a test name `it("REQ-012 rejects expired invoices")`.

Usage:
  python scripts/req_status.py            # write docs/STATUS.md
  python scripts/req_status.py --check    # also exit 1 if there are errors (for CI)
  python scripts/req_status.py --stdout   # print the report instead of writing it

No dependencies beyond the Python standard library.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REQ_ID = re.compile(r"\bREQ-\d{3,}\b")
VALID_STATUSES = {"proposed", "approved", "in-progress", "done", "dropped"}
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".next", "out", "coverage",
             "__pycache__", ".venv", "venv", "transcripts", ".claude"}
SKIP_PREFIXES = ("docs/",)
SKIP_FILES = {"scripts/req_status.py"}
SKIP_SUFFIXES = (".md", ".markdown")  # docs are not code; a README mentioning an ID is not an implementation
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e)(/|$)|\.(test|spec)\.|_test\.|(^|/)test_", re.IGNORECASE)
MAX_FILE_BYTES = 2_000_000


@dataclass
class Requirement:
    id: str
    title: str
    status: str
    client_confirmed: str
    path: Path
    code_refs: list[str] = field(default_factory=list)
    test_refs: list[str] = field(default_factory=list)


@dataclass
class Finding:
    level: str  # ERROR or WARN
    req: str
    message: str


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[3:end].splitlines():
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            value = re.split(r"(?:^|\s)#", value, maxsplit=1)[0]  # drop inline `# comment`
            data[key.strip().lower()] = value.strip().strip('"').strip("'")
    return data


def load_requirements(req_dir: Path) -> tuple[dict[str, Requirement], list[Finding]]:
    reqs: dict[str, Requirement] = {}
    findings: list[Finding] = []
    if not req_dir.is_dir():
        return reqs, findings
    for path in sorted(req_dir.glob("REQ-*.md")):
        meta = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        rid = meta.get("id", "")
        name = path.name
        if not REQ_ID.fullmatch(rid):
            findings.append(Finding("ERROR", name, "missing or invalid `id` in frontmatter"))
            continue
        if not name.startswith(rid):
            findings.append(Finding("ERROR", rid, f"file name `{name}` does not start with its id"))
        if rid in reqs:
            findings.append(Finding("ERROR", rid, f"duplicate id in `{name}` and `{reqs[rid].path.name}`"))
            continue
        status = meta.get("status", "").lower()
        if status not in VALID_STATUSES:
            findings.append(Finding("ERROR", rid, f"invalid status `{status or '(empty)'}`; "
                                              f"use one of {', '.join(sorted(VALID_STATUSES))}"))
        reqs[rid] = Requirement(
            id=rid,
            title=meta.get("title", "(no title)"),
            status=status,
            client_confirmed=meta.get("client_confirmed", "no").lower(),
            path=path,
        )
    return reqs, findings


def list_files(root: Path) -> list[Path]:
    """Prefer git's file list (respects .gitignore); fall back to walking the tree."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=root, capture_output=True, check=True)
        files = [root / p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]
    except (subprocess.CalledProcessError, FileNotFoundError):
        files = [p for p in root.rglob("*") if p.is_file()]
    result = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        if (any(part in SKIP_DIRS for part in Path(rel).parts) or rel.startswith(SKIP_PREFIXES)
                or rel in SKIP_FILES or rel.lower().endswith(SKIP_SUFFIXES)):
            continue
        result.append(f)
    return result


def scan_code(root: Path) -> dict[str, list[tuple[str, bool]]]:
    """Return {REQ-ID: [(relative_path:line, is_test), ...]}."""
    refs: dict[str, list[tuple[str, bool]]] = {}
    for f in list_files(root):
        try:
            if not f.is_file() or f.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = f.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue  # binary
        rel = f.relative_to(root).as_posix()
        is_test = bool(TEST_PATH.search(rel))
        for lineno, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
            for rid in set(REQ_ID.findall(line)):
                refs.setdefault(rid, []).append((f"{rel}:{lineno}", is_test))
    return refs


def evaluate(reqs: dict[str, Requirement], refs: dict[str, list[tuple[str, bool]]]) -> list[Finding]:
    findings: list[Finding] = []
    for rid, places in sorted(refs.items()):
        if rid not in reqs:
            findings.append(Finding("ERROR", rid, f"referenced in code but no requirement file exists "
                                              f"({places[0][0]})"))
    for r in reqs.values():
        for place, is_test in refs.get(r.id, []):
            (r.test_refs if is_test else r.code_refs).append(place)
        has_any = bool(r.code_refs or r.test_refs)
        if r.status == "done" and not r.code_refs:
            findings.append(Finding("ERROR", r.id, "marked done but no code references it"))
        if r.status == "done" and not r.test_refs:
            findings.append(Finding("WARN", r.id, "marked done but no test references it"))
        if r.status == "dropped" and has_any:
            findings.append(Finding("WARN", r.id, "dropped but code still references it"))
        if r.status == "proposed" and has_any:
            findings.append(Finding("WARN", r.id, "code exists before the requirement was approved"))
        if r.status in {"approved", "in-progress", "done"} and r.client_confirmed != "yes":
            findings.append(Finding("WARN", r.id, "not confirmed by the client yet"))
    return findings


def progress(r: Requirement) -> str:
    if r.status == "dropped":
        return "dropped"
    if r.code_refs and r.test_refs:
        return "code + tests"
    if r.code_refs:
        return "code, no tests"
    if r.test_refs:
        return "tests only"
    return "no code yet"


def render(reqs: dict[str, Requirement], findings: list[Finding]) -> str:
    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]
    counts = {s: sum(1 for r in reqs.values() if r.status == s) for s in VALID_STATUSES}
    lines = [
        "# Requirements status",
        "",
        "Generated by `scripts/req_status.py`. Do not edit by hand.",
        "",
        f"**{len(reqs)} requirements** — done {counts['done']}, in progress {counts['in-progress']}, "
        f"approved {counts['approved']}, proposed {counts['proposed']}, dropped {counts['dropped']}. "
        f"**{len(errors)} errors, {len(warns)} warnings.**",
        "",
    ]
    if findings:
        lines += ["## Problems", "", "| Level | Requirement | Problem |", "| --- | --- | --- |"]
        for f in sorted(findings, key=lambda f: (f.level != "ERROR", f.req)):
            lines.append(f"| {f.level} | {f.req} | {f.message} |")
        lines.append("")
    lines += ["## All requirements", "",
              "| ID | Title | Status | Client confirmed | Code | Tests | Progress |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in sorted(reqs.values(), key=lambda r: r.id):
        title = r.title.replace("|", "\\|")
        lines.append(f"| [{r.id}](requirements/{r.path.name}) | {title} | {r.status} | {r.client_confirmed} "
                     f"| {len(r.code_refs)} | {len(r.test_refs)} | {progress(r)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check requirements against code.")
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root (default: .)")
    parser.add_argument("--check", action="store_true", help="exit 1 when there are errors")
    parser.add_argument("--stdout", action="store_true", help="print the report instead of writing docs/STATUS.md")
    args = parser.parse_args()

    root = args.root.resolve()
    reqs, findings = load_requirements(root / "docs" / "requirements")
    findings += evaluate(reqs, scan_code(root))
    report = render(reqs, findings)

    if args.stdout:
        print(report)
    else:
        out = root / "docs" / "STATUS.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Wrote {out.relative_to(root)}")

    errors = sum(1 for f in findings if f.level == "ERROR")
    warns = len(findings) - errors
    print(f"{len(reqs)} requirements, {errors} errors, {warns} warnings")
    if args.check and errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
