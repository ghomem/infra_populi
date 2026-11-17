import importlib.util
import json
import subprocess
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


# HQ batch-7 ruling 3: "verified" splits into verified and verified with stand-in; what lifts each stand-in comes from
# its node fixture's one `# Lifted by:` header line (single source).
def test_lifted_by_reads_the_one_header_line(status, tmp_path):
    (tmp_path / "fx.pp").write_text("# MOCK-APPLY node fixture `fx`\n# Lifted by: a real thing\nfile { '/x': }\n")
    assert status.lifted_by("fx", tmp_path) == "a real thing"


@pytest.mark.parametrize("text", ["# MOCK-APPLY\nfile { '/x': }\n", "# Lifted by: a\n# Lifted by: b\n",
                                  "# Lifted by:   \n"])
def test_a_fixture_without_exactly_one_lifted_by_line_is_an_error(status, tmp_path, text):
    (tmp_path / "fx.pp").write_text(text)
    with pytest.raises(SystemExit):
        status.lifted_by("fx", tmp_path)


def test_standins_are_the_verified_classes_with_a_node_fixture(status, tmp_path):
    (tmp_path / "fx.pp").write_text("# Lifted by: a monitoring node\n")
    row = lambda fixture: type("Row", (), {"node_fixture": fixture})()  # noqa: E731
    rows = {"a": row("fx"), "b": row(""), "c": row("fx")}
    # c has a fixture but is not verified: it is not a verified stand-in
    assert status.standins(rows, ["b", "a"], tmp_path) == [("a", "fx", "a monitoring node")]


def test_every_repo_node_fixture_says_what_lifts_it(status):
    names = sorted(p.stem for p in status.NODE_FIXTURES.glob("*.pp"))
    assert names and all(status.lifted_by(name) for name in names)


def test_standins_flag_prints_only_tab_separated_rows():
    proc = subprocess.run([sys.executable, str(STATUS), "--standins"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    rows = [line.split("\t") for line in proc.stdout.splitlines()]
    assert rows and all(len(r) == 3 and r[2] for r in rows)
    assert {"letsencrypt_certificate", "node_base_domain_desktop"} <= {r[0] for r in rows}
