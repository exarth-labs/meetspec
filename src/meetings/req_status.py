"""
Requirements vs code status check.

Reads every .meetings/requirements/REQ-*.md file, scans the project for REQ-### references,
and writes .meetings/STATUS.md showing which requirements have code, which have tests,
and where docs and code disagree.

The .meetings folder is found from the current directory upwards;
the project root is the folder that contains it.

How code links to a requirement: put the ID anywhere in the code or test,
for example a comment `// REQ-012`, a test name `it("REQ-012 rejects expired invoices")`
or `def test_req_012_rejects_expired_invoices()`.

Usage:
  meetings status            # write .meetings/STATUS.md
  meetings status --check    # also exit 1 if there are errors
  meetings status --stdout   # print the report instead of writing it
  meetings status --json     # print a machine-readable report for tools and AI agents (read-only)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .project import require_base

REQ_ID = re.compile(r"\bREQ-\d{3,}\b")
# In code also accept the snake_case form used in Python test names: test_req_012_...
CODE_REF = re.compile(r"(?<![A-Za-z0-9])REQ[-_](\d{3,})(?!\d)", re.IGNORECASE)
VALID_STATUSES = {"proposed", "approved", "in-progress", "done", "dropped"}
SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".next", "out", "coverage",
             "__pycache__", ".venv", "venv", "transcripts", ".claude", ".meetings"}
SKIP_SUFFIXES = (".md", ".markdown")  # docs are not code; a README mentioning an ID is not an implementation
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e)(/|$)|\.(test|spec)\.|_test\.|(^|/)test_", re.IGNORECASE)
TEST_CLASS = re.compile(r"[a-z0-9]Tests?\.\w+$")  # Java, Kotlin, C#, Swift: InvoiceExportTest.java
CONFIRMED = {"yes", "y", "true"}
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
        meta = parse_frontmatter(path.read_text(encoding="utf-8-sig", errors="replace"))  # -sig: Windows BOM
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
            client_confirmed="yes" if meta.get("client_confirmed", "").lower() in CONFIRMED else "no",
            path=path,
        )
    return reqs, findings


def list_files(root: Path, skip: Path) -> list[Path]:
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
        if (any(part in SKIP_DIRS for part in Path(rel).parts) or f.is_relative_to(skip)
                or rel.lower().endswith(SKIP_SUFFIXES)):
            continue
        result.append(f)
    return result


def scan_code(root: Path, skip: Path) -> dict[str, list[tuple[str, bool]]]:
    """Return {REQ-ID: [(relative_path:line, is_test), ...]}."""
    refs: dict[str, list[tuple[str, bool]]] = {}
    for f in list_files(root, skip):
        try:
            if not f.is_file() or f.stat().st_size > MAX_FILE_BYTES:
                continue
            raw = f.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue  # binary
        rel = f.relative_to(root).as_posix()
        is_test = bool(TEST_PATH.search(rel) or TEST_CLASS.search(rel))
        for lineno, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
            for rid in {f"REQ-{n}" for n in CODE_REF.findall(line)}:
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
        "Generated by `meetings status`. Do not edit by hand.",
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


def to_json(reqs: dict[str, Requirement], findings: list[Finding], root: Path) -> dict:
    errors = sum(1 for f in findings if f.level == "ERROR")
    return {
        "schema": "meetspec/status/v1",
        "summary": {
            "requirements": len(reqs),
            "by_status": {s: sum(1 for r in reqs.values() if r.status == s) for s in sorted(VALID_STATUSES)},
            "errors": errors,
            "warnings": len(findings) - errors,
        },
        "requirements": [
            {
                "id": r.id,
                "title": r.title,
                "status": r.status,
                "client_confirmed": r.client_confirmed == "yes",
                "file": r.path.relative_to(root).as_posix() if r.path.is_relative_to(root) else str(r.path),
                "progress": progress(r),
                "code_refs": r.code_refs,
                "test_refs": r.test_refs,
            }
            for r in sorted(reqs.values(), key=lambda r: r.id)
        ],
        "problems": [{"level": f.level, "requirement": f.req, "message": f.message}
                     for f in sorted(findings, key=lambda f: (f.level != "ERROR", f.req))],
    }


def main(argv: list[str] | None = None, prog: str | None = None) -> None:
    parser = argparse.ArgumentParser(prog=prog, description="Check requirements against code.")
    parser.add_argument("--root", type=Path, default=None,
                        help="project root to scan (default: the folder that contains .meetings)")
    parser.add_argument("--check", action="store_true", help="exit 1 when there are errors")
    parser.add_argument("--stdout", action="store_true", help="print the report instead of writing .meetings/STATUS.md")
    parser.add_argument("--json", action="store_true",
                        help="print a JSON report to stdout instead (read-only; for tools and AI agents)")
    args = parser.parse_args(argv)

    base = require_base()
    root = args.root.resolve() if args.root else base.parent
    reqs, findings = load_requirements(base / "requirements")
    findings += evaluate(reqs, scan_code(root, base))
    errors = sum(1 for f in findings if f.level == "ERROR")
    warns = len(findings) - errors

    if args.json:
        print(json.dumps(to_json(reqs, findings, root), indent=2, ensure_ascii=False))
    elif args.stdout:
        print(render(reqs, findings))
        print(f"{len(reqs)} requirements, {errors} errors, {warns} warnings", file=sys.stderr)
    else:
        out = base / "STATUS.md"
        out.write_text(render(reqs, findings), encoding="utf-8")
        print(f"Wrote {out}")
        print(f"{len(reqs)} requirements, {errors} errors, {warns} warnings")
    if args.check and errors:
        sys.exit(1)

