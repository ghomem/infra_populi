"""HQ 2026-11-11 ruling 3: the pre-commit hook runs the fast subset on every commit and the full suite when a batch
report is staged; no commit lands with a failing test."""

import os
import shutil
import subprocess

import pytest

from conftest import TOOLS

pytestmark = pytest.mark.slow
REPO = TOOLS.parents[1]

CONFTEST = '''
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: x")
    config.addinivalue_line("markers", "repo_state: x")
'''


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "r"
    tests = r / ".codex_state" / "tools" / "tests"
    tests.mkdir(parents=True)
    (r / ".codex_state" / "rules").mkdir()
    shutil.copy(TOOLS / "pre-commit", r / ".codex_state" / "tools" / "pre-commit")
    shutil.copy(REPO / ".codex_state/rules/advisor_only.txt", r / ".codex_state/rules/advisor_only.txt")
    (tests / "conftest.py").write_text(CONFTEST)
    (tests / "test_fast.py").write_text("def test_ok():\n    assert True\n")
    git(r, "init", "-q")
    git(r, "config", "user.email", "t@example.invalid")
    git(r, "config", "user.name", "t")
    (r / ".git" / "hooks" / "pre-commit").symlink_to("../../.codex_state/tools/pre-commit")
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "init", "--no-verify")
    return r


def commit(r, path, text="x\n"):
    (r / path).parent.mkdir(parents=True, exist_ok=True)
    (r / path).write_text(text)
    git(r, "add", "-A")
    env = {k: v for k, v in os.environ.items() if k != "CODEX_RUN"}
    return git(r, "commit", "-q", "-m", f"touch {path}", env=env)


def test_passing_fast_subset_lets_the_commit_through(repo):
    proc = commit(repo, "notes.txt")
    assert proc.returncode == 0, proc.stderr
    assert "TESTS: fast subset passed" in proc.stderr  # git relays hook output on stderr


def test_a_failing_test_rejects_the_commit(repo):
    (repo / ".codex_state/tools/tests/test_broken.py").write_text("def test_broken():\n    assert False\n")
    proc = commit(repo, "notes.txt")
    assert proc.returncode != 0 and "TESTS: commit rejected — the fast subset failed" in proc.stderr


def test_slow_tests_run_only_when_a_batch_report_is_staged(repo):
    (repo / ".codex_state/tools/tests/test_slow.py").write_text(
        "import pytest\npytestmark = pytest.mark.slow\ndef test_slow_broken():\n    assert False\n")
    assert commit(repo, "notes.txt").returncode == 0  # fast subset skips the slow failure
    proc = commit(repo, ".codex_state/escalations/batch-2026-11-11-3.md", "# report\n")
    assert proc.returncode != 0 and "full suite (batch report staged) failed" in proc.stderr


# HQ batch-3 acceptance item 4: skipped tests carry a reason, printed by the hook and named in a batch report.
SKIPPED = ('import pytest\n'
           '@pytest.mark.skipif(True, reason="needs the lab (set P8_LAB_TESTS=1)")\n'
           'def test_needs_lab():\n    pass\n')


def test_each_skipped_test_is_printed_with_its_reason(repo):
    (repo / ".codex_state/tools/tests/test_lab.py").write_text(SKIPPED)
    proc = commit(repo, "notes.txt")
    assert proc.returncode == 0, proc.stderr
    assert "TESTS: skipped test_lab::test_needs_lab — needs the lab (set P8_LAB_TESTS=1)" in proc.stderr


def test_a_skip_without_a_reason_rejects_the_commit(repo):
    (repo / ".codex_state/tools/tests/test_bare.py").write_text(
        "import pytest\n@pytest.mark.skip\ndef test_bare():\n    pass\n")
    proc = commit(repo, "notes.txt")
    assert proc.returncode != 0 and "test_bare::test_bare is skipped without a reason" in proc.stderr


def test_a_batch_report_must_name_every_skipped_test(repo):
    (repo / ".codex_state/tools/tests/test_lab.py").write_text(SKIPPED)
    proc = commit(repo, ".codex_state/escalations/batch-2026-11-12-4.md", "# report\n")
    assert proc.returncode != 0 and "does not name these skipped tests" in proc.stderr
    assert "test_lab::test_needs_lab — needs the lab (set P8_LAB_TESTS=1)" in proc.stderr
    proc = commit(repo, ".codex_state/escalations/batch-2026-11-12-4.md",
                  "# report\n## Skipped tests\n- test_lab::test_needs_lab — needs the lab (set P8_LAB_TESTS=1)\n")
    assert proc.returncode == 0, proc.stderr
