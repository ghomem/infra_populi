"""The turn-end scratch hook (HQ review of the behaviour suite, ruling 5)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "scratch_guard.py"


def repo_with_commit(tmp_path: Path) -> Path:
    repo = tmp_path / "work" / "proj"
    repo.mkdir(parents=True)
    env = {**os.environ, "GIT_AUTHOR_NAME": "p8test", "GIT_AUTHOR_EMAIL": "p8test@example.invalid",
           "GIT_COMMITTER_NAME": "p8test", "GIT_COMMITTER_EMAIL": "p8test@example.invalid",
           "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z"}
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "x"], check=True, env=env)
    return repo


def scratch(tmp_path: Path, repo: Path) -> Path:
    d = tmp_path / "scratch" / str(repo.resolve()).replace("/", "-") / "session1" / "scratchpad"
    d.mkdir(parents=True)
    return d


def hook(tmp_path, repo, event=None, args=()):
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(repo), "SCRATCH_ROOT": str(tmp_path / "scratch")}
    return subprocess.run([sys.executable, str(HOOK), *args], input=json.dumps(event or {}), capture_output=True,
                          text=True, env=env)


def test_no_scratch_lets_the_turn_end(tmp_path):
    repo = repo_with_commit(tmp_path)
    p = hook(tmp_path, repo, {"stop_hook_active": False})
    assert p.returncode == 0 and p.stdout == ""


def test_a_scratch_file_newer_than_the_last_commit_blocks_once(tmp_path):
    repo = repo_with_commit(tmp_path)
    f = scratch(tmp_path, repo) / "report_draft.md"
    f.write_text("x")
    p = hook(tmp_path, repo, {"stop_hook_active": False})
    out = json.loads(p.stdout)
    assert out["decision"] == "block" and str(f) in out["reason"] and ".codex_state/drafts/" in out["reason"]
    again = hook(tmp_path, repo, {"stop_hook_active": True})
    assert again.returncode == 0 and again.stdout == "" and str(f) in again.stderr


def test_a_file_older_than_the_last_commit_is_not_listed(tmp_path):
    repo = repo_with_commit(tmp_path)
    f = scratch(tmp_path, repo) / "old.log"
    f.write_text("x")
    old = time.mktime(time.strptime("2025-06-01", "%Y-%m-%d"))
    os.utime(f, (old, old))
    assert hook(tmp_path, repo, {}).stdout == ""


def test_another_projects_scratch_is_not_listed(tmp_path):
    repo = repo_with_commit(tmp_path)
    other = tmp_path / "scratch" / "-elsewhere" / "s" / "scratchpad"
    other.mkdir(parents=True)
    (other / "x").write_text("x")
    assert hook(tmp_path, repo, {}).stdout == ""


def test_list_mode_exits_1_with_files(tmp_path):
    repo = repo_with_commit(tmp_path)
    (scratch(tmp_path, repo) / "a.txt").write_text("x")
    p = hook(tmp_path, repo, args=["--list"])
    assert p.returncode == 1 and "a.txt" in p.stdout
