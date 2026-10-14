from pathlib import Path

import pytest

from meetings import req_status
from meetings.req_status import CODE_REF, Requirement, evaluate, parse_frontmatter


def write_req(base: Path, rid: str, status: str, confirmed: str = "no") -> None:
    (base / "requirements").mkdir(parents=True, exist_ok=True)
    (base / "requirements" / f"{rid}-thing.md").write_text(
        f"---\nid: {rid}\ntitle: A thing\nstatus: {status}   # proposed | approved\n"
        f"client_confirmed: {confirmed}   # yes only after written confirmation\n---\n\n# {rid}\n",
        encoding="utf-8",
    )


def test_frontmatter_ignores_inline_comments():
    meta = parse_frontmatter("---\nstatus: proposed   # a | b\nconfirmed_on:   # YYYY-MM-DD\ntitle: \"Hi\"\n---\n")
    assert meta == {"status": "proposed", "confirmed_on": "", "title": "Hi"}


@pytest.mark.parametrize(
    ("line", "ids"),
    [
        ("// REQ-012: export", ["012"]),
        ("def test_req_012_exports():", ["012"]),
        ('it("req-0042 works")', ["0042"]),
        ("PREQ-012 and REQ-12", []),
    ],
)
def test_code_references(line, ids):
    assert CODE_REF.findall(line) == ids


def test_evaluate_flags_mismatches(tmp_path):
    reqs = {
        "REQ-001": Requirement("REQ-001", "Done, no code", "done", "yes", tmp_path),
        "REQ-002": Requirement("REQ-002", "Proposed with code", "proposed", "no", tmp_path),
    }
    refs = {"REQ-002": [("src/a.py:1", False)], "REQ-009": [("src/b.py:3", False)]}
    found = {(f.level, f.req, f.message.split(" (")[0]) for f in evaluate(reqs, refs)}
    assert ("ERROR", "REQ-001", "marked done but no code references it") in found
    assert ("ERROR", "REQ-009", "referenced in code but no requirement file exists") in found
    assert ("WARN", "REQ-002", "code exists before the requirement was approved") in found


def test_status_end_to_end(git_repo, capsys):
    base = git_repo / ".meetings"
    write_req(base, "REQ-001", "in-progress", "yes")
    (git_repo / "src").mkdir()
    (git_repo / "src" / "export.py").write_text("# REQ-001: export\n")
    (git_repo / "tests").mkdir()
    (git_repo / "tests" / "test_export.py").write_text("def test_req_001_exports(): pass\n")
    (git_repo / "README.md").write_text("Mentions REQ-777 but docs are not code.\n")

    (git_repo / "src" / "deep").mkdir()
    (git_repo / "src" / "deep" / "x.py").write_text("")
    import os
    os.chdir(git_repo / "src" / "deep")  # finds .meetings from a subfolder
    req_status.main(["--check"])

    report = (base / "STATUS.md").read_text()
    assert "| [REQ-001](requirements/REQ-001-thing.md) | A thing | in-progress | yes | 1 | 1 | code + tests |" in report
    assert "REQ-777" not in report
    assert "0 errors" in capsys.readouterr().out


def test_status_check_fails_on_errors(git_repo):
    write_req(git_repo / ".meetings", "REQ-001", "done", "yes")
    with pytest.raises(SystemExit) as exc:
        req_status.main(["--check", "--stdout"])
    assert exc.value.code == 1


def test_status_needs_meetings_folder(git_repo):
    with pytest.raises(SystemExit) as exc:
        req_status.main([])
    assert "meetings install" in str(exc.value.code)
