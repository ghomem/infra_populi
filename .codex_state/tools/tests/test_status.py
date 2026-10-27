import importlib.util
import json
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
STATUS = Path(__file__).resolve().parents[1] / "status.py"


@pytest.fixture
def status():
    spec = importlib.util.spec_from_file_location("status_under_test", STATUS)
    module = importlib.util.module_from_spec(spec)
    sys.modules["status_under_test"] = module
    spec.loader.exec_module(module)
    return module


def write_verdict(reviews, name, stamp, verdict, commit):
    (reviews / name).mkdir(parents=True, exist_ok=True)
    (reviews / name / f"{stamp}.json").write_text(json.dumps(
        {"class": name, "verdict": verdict, "migrate_commit": commit,
         "checks": {"records": {"status": "ok" if verdict == "PASS" else "fail"}},
         "faithful": {"status": "ok"}}))


def migration(status, commit):
    return status.generator.MigrationCommit(commit=commit, date="2026-10-27")


def test_pass_on_current_commit_is_verified(status, tmp_path):
    write_verdict(tmp_path, "backup", "20261026T000000Z", "PASS", "9d01a9fadc4f")
    state, _ = status.verification_state("backup", migration(status, "9d01a9fadc4f" + "0" * 28), set(), tmp_path)
    assert state == status.VERIFIED


def test_latest_verdict_wins(status, tmp_path):
    write_verdict(tmp_path, "c", "20261026T000000Z", "PASS", "aaaaaaaaaaaa")
    write_verdict(tmp_path, "c", "20261027T000000Z", "FAIL", "aaaaaaaaaaaa")
    state, verdict = status.verification_state("c", migration(status, "a" * 40), set(), tmp_path)
    assert state == status.PENDING_RECONCILIATION
    assert "records" in status.failing_checks(verdict)


def test_pass_on_an_older_commit_does_not_carry_over_to_a_fix_commit(status, tmp_path):
    write_verdict(tmp_path, "c", "20261026T000000Z", "PASS", "aaaaaaaaaaaa")
    state, verdict = status.verification_state("c", migration(status, "b" * 40), set(), tmp_path)
    assert state == status.PENDING_RECONCILIATION
    assert status.failing_checks(verdict) == "PASS on an older commit"


def test_manifest_touched_after_the_reviewed_commit_is_not_verified(status, tmp_path):
    write_verdict(tmp_path, "c", "20261026T000000Z", "PASS", "aaaaaaaaaaaa")
    state, _ = status.verification_state("c", migration(status, "a" * 40), {"c"}, tmp_path)
    assert state == status.PENDING_RECONCILIATION


def test_no_verdict_is_pending(status, tmp_path):
    state, verdict = status.verification_state("c", migration(status, "a" * 40), set(), tmp_path)
    assert state == status.PENDING_RECONCILIATION
    assert status.failing_checks(verdict) == "no v2 verdict"


def test_marker_rendering(status):
    entry = status.generator.TrackerEntry
    assert status.marker(entry("x", True, "release-0.9.10", "ensure dropped")) == \
        "[from: release-0.9.10; upstream defect fixed: ensure dropped]"
    assert status.marker(entry("x", True, "", "")) == "plain Done"
    assert status.marker(None) == "(not Done in tracker)"


def test_repo_sweep_result_is_8_verified(status):
    gen = status.generator
    rows = gen.parse_plan()
    migrations = gen.git_migrations()
    owner_validated = {n for n, r in rows.items() if r.owner_validated}
    done = set(migrations) - set(gen.read_blocked()) - owner_validated
    flagged = gen.find_flagged_migrations(migrations)
    verified = {n for n in done if status.verification_state(n, migrations[n], flagged)[0] == status.VERIFIED}
    # checkpoint 1: exactly the 8 sweep PASSes; grows only through new v2 PASSes after fix commits
    assert {"backup", "filesystem_base", "filesystem_base_desktop", "hello_world_flask_common",
            "network_static", "puppet_backup", "puppet_commush", "user_kde_lock_screen_common"} <= verified
