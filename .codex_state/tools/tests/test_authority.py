"""HQ 2026-11-11 ruling 2: advisor-only files cannot be committed under the Codex run marker (hook) and any attempt
is reported after the run (wrapper audit, which also catches --no-verify)."""

import shutil
import subprocess

import pytest

from conftest import TOOLS

pytestmark = pytest.mark.slow  # excluded from the per-commit fast subset (HQ 2026-11-11 ruling 3)

REPO = TOOLS.parents[1]


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, env=env)


@pytest.fixture
def hook_repo(tmp_path):
    repo = tmp_path / "r"
    (repo / ".codex_state" / "rules").mkdir(parents=True)
    (repo / ".codex_state" / "tools").mkdir()
    shutil.copy(TOOLS / "pre-commit", repo / ".codex_state" / "tools" / "pre-commit")
    shutil.copy(REPO / ".codex_state" / "rules" / "advisor_only.txt", repo / ".codex_state" / "rules" / "advisor_only.txt")
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "user.name", "t")
    (repo / ".git" / "hooks" / "pre-commit").symlink_to("../../.codex_state/tools/pre-commit")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "init", "--no-verify")
    return repo


def commit(repo, path, marker):
    import os
    f = repo / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x\n")
    git(repo, "add", path)
    env = dict(os.environ, **({"CODEX_RUN": "1"} if marker else {}))
    env.pop("CODEX_RUN", None) if not marker else None
    return git(repo, "commit", "-q", "-m", f"touch {path}", env=env)


@pytest.mark.parametrize("path", [".codex_state/migration_plan.md", ".codex_state/tools/compile/composites.txt",
                                  ".codex_state/blocked.txt", ".codex_state/DESIGN_DECISIONS.md",
                                  ".codex_state/rules/CODEX_RUNBOOK.md", ".claude/settings.json"])
def test_hook_refuses_advisor_only_files_under_the_marker(hook_repo, path):
    proc = commit(hook_repo, path, marker=True)
    assert proc.returncode != 0 and "advisor-only files staged" in proc.stderr


def test_hook_allows_the_same_file_without_the_marker(hook_repo):
    assert commit(hook_repo, ".codex_state/migration_plan.md", marker=False).returncode == 0


@pytest.mark.parametrize("path", [".codex_state/migrated_classes.txt", ".codex_state/migration_order.md",
                                  ".codex_state/lab/Puppetfile"])
def test_hook_allows_record_green_files_under_the_marker(hook_repo, path):
    assert commit(hook_repo, path, marker=True).returncode == 0


@pytest.fixture
def wrapper_clone(tmp_path, lab):
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(REPO), str(work)], check=True)
    git(work, "config", "user.email", "t@example.invalid")
    git(work, "config", "user.name", "t")
    for src in [*TOOLS.glob("*.py"), *TOOLS.glob("*.sh"), TOOLS / "codex_migrate_class", TOOLS / "pre-commit",
                REPO / ".codex_state/rules/advisor_only.txt", REPO / ".codex_state/rules/CODEX_RUNBOOK.md"]:
        dst = work / src.relative_to(REPO)
        dst.write_bytes(src.read_bytes())
        dst.chmod(src.stat().st_mode)
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "overlay", "--no-verify")
    return work


def stub_codex(lab, script):
    path = lab.bin / "codex"
    path.write_text("#!/usr/bin/env bash\n" + script + "\n")
    path.chmod(0o755)


def test_wrapper_audit_reports_a_plan_commit_made_with_no_verify(wrapper_clone, lab):
    stub_codex(lab, '[ "$CODEX_RUN" = 1 ] || exit 9\necho x >> .codex_state/migration_plan.md\n'
                    'git commit -q -a -m "plan(x): sneaky" --no-verify')
    proc = lab.run([str(wrapper_clone / ".codex_state/tools/codex_migrate_class"), "puppet_infrastructure::dns_client"],
                   cwd=wrapper_clone)
    assert proc.returncode == 5
    assert "AUTHORITY_VIOLATION" in proc.stderr and ".codex_state/migration_plan.md" in proc.stderr


def test_wrapper_audit_is_quiet_for_record_files_and_reports_uncommitted_edits(wrapper_clone, lab):
    stub_codex(lab, 'echo x >> .codex_state/migration_order.md\ngit commit -q -a -m "P8: regenerate" --no-verify\n'
                    'echo y >> .codex_state/blocked.txt')
    proc = lab.run([str(wrapper_clone / ".codex_state/tools/codex_migrate_class"), "puppet_infrastructure::dns_client"],
                   cwd=wrapper_clone)
    assert proc.returncode == 5 and "uncommitted: .codex_state/blocked.txt" in proc.stderr
    assert "migration_order" not in proc.stderr.split("AUTHORITY_VIOLATION", 1)[1]


def test_wrapper_audit_ignores_advisor_edits_that_predate_the_run(wrapper_clone, lab):
    (wrapper_clone / ".codex_state/migration_plan.md").write_text("advisor's work in progress\n")
    stub_codex(lab, "exit 0")
    proc = lab.run([str(wrapper_clone / ".codex_state/tools/codex_migrate_class"), "puppet_infrastructure::dns_client"],
                   cwd=wrapper_clone)
    assert proc.returncode == 0, proc.stderr
    assert "AUTHORITY_VIOLATION" not in proc.stderr
