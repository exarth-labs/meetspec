import subprocess

import pytest

from meetings.install import CURSOR_RULE, PLAYBOOKS, install


def git_status(repo) -> str:
    return subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=repo, capture_output=True, text=True, check=True).stdout


def test_install_creates_kit_and_hides_it_from_git(git_repo):
    install(git_repo)

    base = git_repo / ".meetings"
    for path in ("AGENTS.md", "README.md", "glossary.md", "requirements/_template.md", "meetings/_template.md"):
        assert (base / path).is_file(), path
    assert (base / "transcripts").is_dir()
    for name in PLAYBOOKS:
        playbook = (base / "playbooks" / f"{name}.md").read_text()
        assert (git_repo / ".claude" / "skills" / name / "SKILL.md").read_text() == playbook
        assert f"playbooks/{name}.md" in (base / "AGENTS.md").read_text()
    assert ".meetings/AGENTS.md" in (git_repo / CURSOR_RULE).read_text()
    assert git_status(git_repo) == ""


def test_reinstall_updates_kit_but_keeps_user_files(git_repo):
    install(git_repo)
    base = git_repo / ".meetings"
    (base / "glossary.md").write_text("my words")
    (base / "requirements" / "REQ-001-x.md").write_text("mine")
    skill = git_repo / ".claude" / "skills" / "req-check" / "SKILL.md"
    skill.write_text("edited")

    install(git_repo)

    assert (base / "glossary.md").read_text() == "my words"
    assert (base / "requirements" / "REQ-001-x.md").read_text() == "mine"
    assert skill.read_text() != "edited"
    exclude = (git_repo / ".git" / "info" / "exclude").read_text().splitlines()
    assert exclude.count(".meetings/") == 1


def test_install_from_a_subfolder_uses_repo_root(git_repo):
    sub = git_repo / "src"
    sub.mkdir()
    install(sub)
    assert (git_repo / ".meetings").is_dir()
    assert not (sub / ".meetings").exists()


def test_install_outside_git_fails(tmp_path):
    with pytest.raises(SystemExit):
        install(tmp_path)


def test_other_claude_files_stay_visible(git_repo):
    install(git_repo)
    (git_repo / ".claude" / "settings.json").write_text("{}")
    assert ".claude/settings.json" in git_status(git_repo)
