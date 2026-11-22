"""Reviewer v2 evidence tool: pure pieces, the PASS rule and verdict persistence."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from conftest import TOOLS, planned_inventory

sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
spec = importlib.util.spec_from_file_location("review_class", TOOLS / "review_class.py")
rc = importlib.util.module_from_spec(spec)
sys.modules["review_class"] = rc
spec.loader.exec_module(rc)

INV_TEXT = """MODULE resolv_conf env saz-resolv_conf 8.0.1
MODULE ssh env saz-ssh 13.1.0
MODULE cron_core vendored puppetlabs-cron_core 1.3.0
TYPE cron_core cron
CLASS resolv_conf resolv_conf
CLASS ssh ssh
CLASS ssh ssh::server
"""


@pytest.fixture
def inv():
    return rc.parse_inventory(INV_TEXT)


def test_parse_inventory(inv):
    assert inv["modules"]["resolv_conf"] == {"kind": "env", "forge": "saz-resolv_conf", "version": "8.0.1"}
    assert inv["types"]["cron"] == "cron_core" and inv["classes"]["ssh::server"] == "ssh"


def test_module_claims_find_author_name_and_version(inv):
    header = ["# Module dependency: puppetlabs-cron_core 1.3.0 (vendored).",
              "# Dependencies: `resolv_conf` class (from `puppet-resolv_conf` module).",
              "# an add-on to firewall_secure (not a module)"]
    assert rc.module_claims(header, inv) == [("puppetlabs-cron_core", "1.3.0"), ("puppet-resolv_conf", None)]



def test_module_claims_skip_filesystem_path_segments(inv):
    tmp = "/opt/puppet-infrastructure/linux-policies/TMP/p8testuser.sh.tmp"
    header = [f"# Expected run-2 events: File[{tmp}]; File_line[{tmp}_0] — upstream design",
              "# Module dependencies: puppetlabs-stdlib 9.7.0 (file_line); puppet-network 2.2.1."]
    assert rc.module_claims(header, inv) == [("puppetlabs-stdlib", "9.7.0"), ("puppet-network", "2.2.1")]

def test_modules_used_counts_env_modules_only(inv):
    manifest = "class x {\n  class { 'resolv_conf': }\n  include ssh::server\n  cron { 'c': }\n}\n"
    assert rc.modules_used(manifest, inv) == {"resolv_conf", "ssh"}


def test_header_block_stops_at_class_or_define():
    text = "# h1\n### Purpose\n# p\nclass puppet_infrastructure::x (\n# not header\n"
    assert rc.header_block(text) == ["# h1", "### Purpose", "# p"]
    assert rc.header_block("define puppet_infrastructure::y {}\n") == []


def test_diff_lines_detects_deleted_comments():
    added, removed = rc.diff_lines("### Purpose\n# keep me\nclass x {}\n", "# new header\nclass x {}\n")
    assert added == ["# new header"] and removed == ["### Purpose", "# keep me"]
    assert all(rc.is_comment(l) for l in removed)


def test_json_strings_walks_nested_values():
    data = {"lan_iface": "enp0s3", "list": ["a", {"user": "p8testuser"}], "n": 3}
    assert rc.json_strings(data) == [("lan_iface", "enp0s3"), ("list[0]", "a"), ("list[1].user", "p8testuser")]


def all_ok():
    return {n: {"status": "ok", "detail": ""} for n in rc.CHECKS}


def test_decide_requires_every_check_and_faithfulness():
    assert rc.decide(all_ok(), "ok", None) == "PASS"
    assert rc.decide(all_ok(), "fail", None) == "FAIL"
    for name in rc.CHECKS:
        checks = all_ok()
        checks[name]["status"] = "fail"
        assert rc.decide(checks, "ok", None) == "FAIL", name
    checks = all_ok()
    checks["idempotent"]["status"] = "skipped"
    assert rc.decide(checks, "ok", None) == "FAIL"  # a review without its harness run cannot PASS
    checks["idempotent"]["status"] = "needs-justification"
    assert rc.decide(checks, "ok", None) == "FAIL"
    assert rc.decide(checks, "ok", "baseline already has /etc/x with that content") == "PASS"


def test_verdict_persists_json_and_prints_report(tmp_path, monkeypatch, capsys):
    drafts, verdicts = tmp_path / "drafts", tmp_path / "reviews"
    drafts.mkdir()
    monkeypatch.setattr(rc, "DRAFTS", drafts)
    monkeypatch.setattr(rc, "VERDICTS", verdicts)
    monkeypatch.setattr(rc, "REPO", tmp_path)
    checks = all_ok()
    checks["records"] = {"status": "fail", "detail": ["no migration header"]}
    (drafts / "x.20261026T000000Z.draft.json").write_text(json.dumps(
        {"class": "x", "baseline": "release-0.9.10 (cf477c6)", "checks": checks, "migrate_commit": "abc"}))
    assert rc.main(["verdict", "x", "--faithful", "ok", "--evidence", "DIFF A: header comment only"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("VERDICT: FAIL\nclass: x\nchecks: git=ok scope=ok")
    assert "records: no migration header" in out
    (saved,) = list((verdicts / "x").glob("*.json"))
    record = json.loads(saved.read_text())
    assert record["verdict"] == "FAIL" and record["faithful"]["evidence"] == ["DIFF A: header comment only"]
    assert "author" not in json.dumps(record).lower()
    import os
    events = Path(os.environ["P8_METRICS_DIR"]) / "events.jsonl"
    (event,) = [json.loads(l) for l in events.read_text().splitlines()]
    assert event["class"] == "x" and event["kind"] == "review"
    assert event["data"]["verdict"] == "FAIL" and event["data"]["failed_checks"] == ["records"]


def test_verdict_requires_judgement_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "DRAFTS", tmp_path)
    with pytest.raises(SystemExit):
        rc.main(["verdict", "x", "--faithful", "maybe", "--evidence", "e"])
    with pytest.raises(SystemExit):
        rc.main(["verdict", "x", "--faithful", "ok"])



# HQ batch-7 ruling 2: a mock-apply GREEN needs the reviewer's fixture-scope judgement, persisted in the verdict.
def fixture_draft(tmp_path, monkeypatch):
    drafts, verdicts = tmp_path / "drafts", tmp_path / "reviews"
    drafts.mkdir()
    monkeypatch.setattr(rc, "DRAFTS", drafts)
    monkeypatch.setattr(rc, "VERDICTS", verdicts)
    monkeypatch.setattr(rc, "REPO", tmp_path)
    fixture = rc.node_fixture_summary("puppet_agent_standin")
    (drafts / "x.20261117T000000Z.draft.json").write_text(json.dumps(
        {"class": "x", "baseline": "release-0.9.10 (cf477c6)", "checks": all_ok(), "migrate_commit": "abc",
         "mock_apply": "stand-in (node fixture puppet_agent_standin: behaviour NOT verified)", "node_fixture": fixture}))
    return verdicts


def test_node_fixture_summary_lists_every_resource():
    fixture = rc.node_fixture_summary("puppet_agent_standin")
    assert fixture["resources"] == ["file[/etc/systemd/system/puppet.service.d]",
                                    "file[/etc/systemd/system/puppet.service.d/p8test-standin.conf]",
                                    "exec[p8test puppet.service stand-in daemon-reload]"]
    assert fixture["header"][0].startswith("# MOCK-APPLY node fixture `puppet_agent_standin`")


def test_a_mock_apply_verdict_needs_fixture_scope(tmp_path, monkeypatch):
    fixture_draft(tmp_path, monkeypatch)
    with pytest.raises(SystemExit, match="--fixture-scope"):
        rc.main(["verdict", "x", "--faithful", "ok", "--evidence", "DIFF A: header comment only"])


def test_fixture_scope_is_persisted(tmp_path, monkeypatch, capsys):
    verdicts = fixture_draft(tmp_path, monkeypatch)
    assert rc.main(["verdict", "x", "--faithful", "ok", "--evidence", "DIFF A: header comment only",
                    "--fixture-scope", "drop-in replaces ExecStart only"]) == 0
    assert "fixture-scope: drop-in replaces ExecStart only" in capsys.readouterr().out
    (saved,) = list((verdicts / "x").glob("*.json"))
    record = json.loads(saved.read_text())
    assert record["verdict"] == "PASS" and record["node_fixture"]["scope_evidence"] == "drop-in replaces ExecStart only"
    assert record["node_fixture"]["name"] == "puppet_agent_standin" and record["mock_apply"]

def test_tool_never_prints_commit_authors_or_bodies():
    source = (TOOLS / "review_class.py").read_text()
    assert "%an" not in source and "%ae" not in source and "%b" not in source
    assert '"--format=%H%x09%s"' in source


def test_first_migration_must_start_from_baseline_content():
    prov, _ = rc.provenance_problems(["diff"], ["manifests/x.pp"], remigration=False)
    assert prov and "drift predates the migration" in prov[0]
    prov, ok = rc.provenance_problems(["diff"], [], remigration=False)
    assert prov == [] and "started from baseline content" in ok


def test_remigration_replaces_earlier_content_and_is_judged_by_diff_a():
    prov, ok = rc.provenance_problems(["diff"], ["manifests/x.pp"], remigration=True)
    assert prov == [] and "re-migration" in ok and "manifests/x.pp" in ok


def test_a_migrate_commit_that_changes_no_class_file_fails_either_way():
    for remigration in (False, True):
        prov, _ = rc.provenance_problems([], [], remigration=remigration)
        assert prov == ["the migrate commit changed no class file (manifest/templates/files)"]


def test_migrate_commits_lists_newest_first(monkeypatch):
    log = "c3\tP8: migrate puppet_infrastructure::x\nc2\tP8: record x: header\nc1\tP8: migrate puppet_infrastructure::x\n" \
          "c0\tP8: migrate puppet_infrastructure::xy\n"
    monkeypatch.setattr(rc, "git", lambda *a, **k: log)
    assert rc.migrate_commits("x") == [("c3", "P8: migrate puppet_infrastructure::x"),
                                       ("c1", "P8: migrate puppet_infrastructure::x")]
    assert rc.migrate_commit("x")[0] == "c3"


def test_defect_registry_entries_parse(tmp_path):
    reg = tmp_path / "upstream_defects.md"
    reg.write_text("# x\n\n## filesystem_sec\n- Short: s\n- Ruled change: assign into a new\n  variable only\n"
                   "- Status: ruled\n\n## user_lock, mysql_server\n- Ruled change: none yet\n- Status: pending HQ\n")
    assert rc.defect_entry("filesystem_sec", reg) == {"status": "ruled", "change": "assign into a new variable only"}
    assert rc.defect_entry("mysql_server", reg)["status"] == "pending HQ"
    assert rc.defect_entry("backup", reg) is None
    reg.write_text("# list\n\n## mariadb_server (moved by 874f854)\n- Ruled change (proposal, lab-tested;\n  confirmed: yes): add `unless => \"a: b\"`\n- Status: ruled\n")
    assert rc.defect_entry("mariadb_server", reg) == {"status": "ruled", "change": 'add `unless => "a: b"`'}


def test_repo_registry_has_the_ruled_fixes():
    for cls in ("filesystem_sec", "puppet_boot_run", "openvpn_nm_connection", "user_base", "user_lock",
                "mariadb_server", "openvpn_server", "firewall_addon_hosting"):
        assert rc.defect_entry(cls)["status"].startswith(("ruled", "applied")), cls
    assert rc.defect_entry("linux_policies_user")["status"] == "ruled"


def test_run2_justification_rules():
    header = "# Puppet 8 migration: release-0.9.10 manifest validated unchanged.\n# Module dependency: puppetlabs-apt 11.3.2.\n"
    body = "class puppet_infrastructure::packages_base {\n}\n"
    ok = header + ("# Expected run-2 events: Exec[apt_update] — apt update frequency 'always' is upstream's choice. "
                   "Exec[dnf-makecache] — the RedHat branch runs dnf makecache on every run\n") + body
    assert rc.run2_justification_problems("packages_base", ok) == []
    assert "no `# Expected run-2 events" in rc.run2_justification_problems("packages_base", header + body)[0]
    bare = header + "# Expected run-2 events: Exec[apt_update]; Exec[dnf-makecache]\n" + body
    assert "gives no justification" in rc.run2_justification_problems("packages_base", bare)[0]
    assert "plan lists none" in rc.run2_justification_problems("backup", ok.replace("packages_base", "backup"))[0]


# HQ 2026-11-16: --fresh on a class whose migrate commit is not HEAD (bar record_green's own record commits) is a usage
# error — refused before any check or harness run, no draft, and no verdict can be recorded from an older draft.
def fake_history(monkeypatch, later):
    monkeypatch.setattr(rc, "migrate_commit", lambda cls: ("c0ffee" * 6 + "abcd", f"P8: migrate puppet_infrastructure::{cls}"))
    monkeypatch.setattr(rc, "git", lambda *a, **k: "".join(f"{s}\n" for s in later))


@pytest.mark.parametrize("later", [[], ["P8: regenerate migration order after x"],
                                   ["P8: record review x", "P8: regenerate migration order after x"]])
def test_fresh_is_valid_right_after_a_migration(monkeypatch, later):
    fake_history(monkeypatch, later)
    assert rc.fresh_usage_error("x") is None


@pytest.mark.parametrize("later", [["P8: engine: b4-A7 — network steps"], ["P8: record x"] * 4])
def test_fresh_on_a_long_recorded_class_is_a_usage_error(monkeypatch, later):
    fake_history(monkeypatch, later)
    assert "is not HEAD" in rc.fresh_usage_error("x") and "Re-run without --fresh" in rc.fresh_usage_error("x")


def test_refused_fresh_check_runs_nothing_writes_no_draft_and_blocks_the_verdict(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rc, "DRAFTS", tmp_path)
    old = tmp_path / "x.20261110T000000Z.draft.json"  # a draft from an earlier, valid check
    old.write_text(json.dumps({"class": "x", "baseline": "b", "checks": {}, "diffs": {}}))
    fake_history(monkeypatch, ["P8: engine: something later"])

    def boom(*a, **k):
        raise AssertionError("run_checks must not run (no harness, no node revert)")
    monkeypatch.setattr(rc, "run_checks", boom)
    assert rc.main(["check", "x", "--fresh"]) == 2
    assert "USAGE ERROR: --fresh on x" in capsys.readouterr().err
    assert sorted(p.name for p in tmp_path.glob("*.draft.json")) == [old.name]  # no new draft
    import os
    os.utime(old, (old.stat().st_mtime - 60,) * 2)
    with pytest.raises(SystemExit, match="was refused"):
        rc.cmd_verdict(["x", "--faithful", "ok", "--evidence", "e"])
    assert not (tmp_path.parent / "reviews").exists()


def test_a_new_valid_check_clears_the_refusal(tmp_path, monkeypatch):
    import os
    monkeypatch.setattr(rc, "DRAFTS", tmp_path)
    refused = tmp_path / "x.refused"
    refused.write_text("t --fresh on x: ...\n")
    os.utime(refused, (refused.stat().st_mtime - 60,) * 2)
    newer = tmp_path / "x.20261116T000000Z.draft.json"
    newer.write_text("{}")
    assert rc.latest_draft("x") == newer


def test_every_verdict_shows_revert_first_and_node_fresh():
    text = ("NODE_FRESH: yes (boot 985deef4 of the latest revert, no agent run since)\n"
            "RUN1_EVENTS: 27 catalog, 164 pluginsync (rc 2; node reverted first)\nGREEN: run 2 exited 0\n")
    assert rc.fresh_node_facts(text) == {"revert_first": True, "node_fresh": True}
    stale = text.replace("NODE_FRESH: yes (boot", "NODE_FRESH: no (an agent run happened").replace(
        "node reverted first", "node NOT reverted first")
    assert rc.fresh_node_facts(stale) == {"revert_first": False, "node_fresh": False}
    src = (TOOLS / "review_class.py").read_text()
    assert '"--revert-first", f"puppet_infrastructure::{cls}"' in src  # the reviewer always reverts first
    assert "GREEN, but not on a freshly reverted node" in src


# batch 5 (hashman_web): class trees may hold images. The tool crashed decoding a PNG as UTF-8; binary files are now
# compared byte for byte and reported in one line, and a binary change counts as a code change.
PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def test_binary_class_files_are_compared_as_bytes():
    assert rc.as_text(PNG) is None and rc.as_text(b"class x {}\n") == "class x {}\n" and rc.as_text(None) is None
    assert rc.is_binary(PNG, None) and not rc.is_binary(b"a\n", None)
    line = rc.change(PNG, PNG + b"\x01", "files/x.png", "release-0.9.10", "HEAD")
    assert line == "Binary file files/x.png differs (release-0.9.10 -> HEAD; 16 -> 17 bytes)\n"
    assert rc.change(b"a\n", b"b\n", "manifests/x.pp", "A", "B").startswith("--- A:manifests/x.pp")


def test_show_reads_a_binary_blob_without_crashing(monkeypatch):
    class Proc:
        returncode, stdout = 0, PNG
    monkeypatch.setattr(rc.subprocess, "run", lambda *a, **k: Proc())
    assert rc.show_bytes("HEAD", "files/x.png") == PNG and rc.show("HEAD", "files/x.png") is None



def test_node_identities_count_device_backed_nics_only(monkeypatch):
    # 2026-11-17 (openvpn_server): the fixture's veth p8test0 and the class's bridge br0 are not real NICs
    calls = []

    def fake_run(argv, **kw):
        calls.append(argv)
        return type("P", (), {"returncode": 0, "stdout": "enp0s3\nenp0s8\n---\nsalatiel\np8testuser\n"})()
    import nodes
    monkeypatch.setattr(nodes, "select", lambda inv, cls=None: {"alias": "puppet8node"})
    monkeypatch.setattr(rc.subprocess, "run", fake_run)
    assert rc.node_identities("openvpn_server") == ({"enp0s3", "enp0s8"}, {"salatiel"})
    assert "/device" in calls[0][-1]


# HQ batch-8 ruling 6: a verdict per node (the RedHat branches on rhel9)
def test_a_per_node_verdict_is_kept_beside_the_class_verdicts(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("P8_NODE", "")  # registers P8_NODE so pytest restores it: node_option exports it
    monkeypatch.delenv("P8_NODE")
    drafts, verdicts = tmp_path / "drafts", tmp_path / "reviews"
    drafts.mkdir()
    monkeypatch.setattr(rc, "DRAFTS", drafts)
    monkeypatch.setattr(rc, "VERDICTS", verdicts)
    monkeypatch.setattr(rc, "REPO", tmp_path)
    (drafts / "x.20261118T000000Z.draft.json").write_text(json.dumps(
        {"class": "x", "baseline": "release-0.9.10 (cf477c6)", "checks": all_ok(), "migrate_commit": "abc",
         "node": "rhel9", "node_option": "rhel9"}))
    with pytest.raises(SystemExit, match="checked with --node rhel9, not --node None"):
        rc.main(["verdict", "x", "--faithful", "ok", "--evidence", "e"])  # a plain verdict never takes a node draft
    assert rc.main(["verdict", "x", "--node", "rhel9", "--faithful", "ok", "--evidence", "RedHat branch: e"]) == 0
    assert "class: x (node rhel9)" in capsys.readouterr().out
    assert list((verdicts / "x").glob("*.json")) == []  # the class's own verdicts are untouched
    (saved,) = list((verdicts / "x" / "nodes" / "rhel9").glob("*.json"))
    assert json.loads(saved.read_text())["node"] == "rhel9" and json.loads(saved.read_text())["verdict"] == "PASS"
    import os
    events = Path(os.environ["P8_METRICS_DIR"]) / "events.jsonl"
    assert not events.exists() or "review" not in events.read_text()  # not a Phase 1 attempt


@pytest.mark.parametrize("cls,kind,message", [
    ("user_kde_lock_screen", "rhel9", "the plan pins user_kde_lock_screen to node kubuntu"),
    ("ssh_secure", "future", "is not an active node kind"),  # conftest's synthetic planned kind
    ("ssh_secure", "nope", "is not an active node kind"),
])
def test_the_node_option_is_refused_where_it_would_mislead(monkeypatch, tmp_path, cls, kind, message):
    monkeypatch.setenv("P8_NODES", planned_inventory(tmp_path))
    monkeypatch.setenv("P8_NODE", "")  # registers P8_NODE so pytest restores it: node_option exports it
    monkeypatch.delenv("P8_NODE")
    with pytest.raises(SystemExit, match=message):
        rc.node_option(cls, ["--node", kind])


def test_the_node_option_exports_the_node(monkeypatch):
    monkeypatch.setenv("P8_NODE", "")  # registers P8_NODE so pytest restores it: node_option exports it
    monkeypatch.delenv("P8_NODE")
    import os
    assert rc.node_option("ssh_secure", ["--node", "rhel9"]) == "rhel9" and os.environ["P8_NODE"] == "rhel9"
    assert rc.node_kind("ssh_secure") == "rhel9"  # every node lookup of the review follows it
    assert rc.node_option("ssh_secure", []) is None


def test_local_change_rows_and_test_asset_fixtures(tmp_path):
    # HQ 2026-11-18: policy B purpose fixes are rows of rules/local_changes.md; ruling 9: a test asset is no stand-in
    lc = tmp_path / "local_changes.md"
    lc.write_text("| # | class | change (file:line) | check | reviewer | date |\n|---|---|---|---|---|---|\n"
                  "| 1 | rsyslog_base | subscribe to the TLS files (rsyslog_base.pp:79) | a | b | 2026-11-18 |\n")
    assert rc.local_change_entry("rsyslog_base", lc) == "#1: subscribe to the TLS files (rsyslog_base.pp:79)"
    assert rc.local_change_entry("hashman_web", lc) is None
    assets = tmp_path / "assets.txt"
    assets.write_text("# comment\nhashman_master_standin  the site's logo placeholders\n")
    assert rc.test_asset_fixtures(assets) == {"hashman_master_standin"}
    assert rc.test_asset_fixtures(tmp_path / "missing.txt") == set()


def test_tracker_text_writes_a_local_change_marker():
    import records
    out = records.tracker_text("rsyslog_base Done [from: release-0.9.10]\n", "rsyslog_base", "release-0.9.10", "",
                               local="#1")
    assert out == "rsyslog_base Done [from: release-0.9.10; local changes: #1]\n"


def test_local_change_numbers_are_the_class_rows(tmp_path):
    # HQ batch-12 ruling 4: the tracker marker lists the numbers of the class's rows in rules/local_changes.md
    lc = tmp_path / "local_changes.md"
    lc.write_text("| # | class | change | check | reviewer | date |\n|---|---|---|---|---|---|\n"
                  "| 3 | sysmon_base | net-tools | a | b | 2026-11-18 |\n| 4 | sysmon_base | lock notice | a | b | 2026-11-18 |\n"
                  "| 5 | firewall_secure_extra | blacklist | a | b | 2026-11-18 |\n")
    assert rc.local_change_numbers("sysmon_base", lc) == [3, 4]
    assert rc.local_change_numbers("hashman_web", lc) == []
    assert rc.local_change_numbers("x", tmp_path / "missing.md") == []


def test_local_marker_grows_and_never_shrinks_without_the_flag():
    import records
    assert records.local_marker("c", "", [3], False) == "#3"
    assert records.local_marker("c", "#3", [3, 4], False) == "#3, #4"
    with pytest.raises(SystemExit, match="shrinks only with --shrink-local-changes"):
        records.local_marker("c", "#3, #4", [3], False)
    assert records.local_marker("c", "#3, #4", [3], True) == "#3"


def test_local_marker_replaces_legacy_text_and_guards_its_removal():
    import records
    assert records.local_marker("c", "net-tools installed for the connection checks", [3, 4], False) == "#3, #4"
    with pytest.raises(SystemExit, match="needs --shrink-local-changes"):
        records.local_marker("c", "backend bound to 127.0.0.1", [], False)
    assert records.local_marker("c", "backend bound to 127.0.0.1", [], True) == ""


# HQ batch-15 ruling 2: a class with a local change gets its Phase 1 PASS only once the change's after-check passed,
# on the class's current code.
def after_fixture(tmp_path, row_check, results):
    lc = tmp_path / "local_changes.md"
    lc.write_text("| # | class | change | check | reviewer | date |\n|---|---|---|---|---|---|\n"
                  f"| 9 | p8cls | x | {row_check} | pending | 2026-11-19 |\n")
    rdir = tmp_path / "results" / "p8cls"
    rdir.mkdir(parents=True)
    for name, (runner, passed) in results.items():
        (rdir / f"{name}.json").write_text(json.dumps({"runner": runner, "applied": [
            {"id": i, "passed": p} for i, p in passed.items()]}))
    return lc, tmp_path / "results"


GOOD = "chk-a and chk-b: FAIL before (x); PASS after (results/p8cls/20261119T100000Z-author: ok)"


def test_a_local_change_whose_after_check_passed_on_the_current_code_is_accepted(tmp_path):
    lc, res = after_fixture(tmp_path, GOOD, {"20261119T100000Z-author": ("c1", {"chk-a": True, "chk-b": True})})
    assert rc.local_change_after_problems("p8cls", ["m.pp"], lc, res, changed=lambda r, f: False) == []


@pytest.mark.parametrize("row, results, changed, message", [
    ("chk-a: FAIL before (x); PASS after: pending", {}, False, "names no after result"),
    (GOOD, {"20261119T090000Z-author": ("c1", {"chk-a": True, "chk-b": True})}, False, "does not exist"),
    (GOOD, {"20261119T100000Z-author": ("c1", {"chk-a": True, "chk-b": False})}, False, "check chk-b did not pass in"),
    (GOOD, {"20261119T100000Z-author": ("c1", {"chk-a": True, "chk-b": True})}, True, "changed since"),
    (GOOD, {"20261119T100000Z-author": ("c1", {"chk-a": True, "chk-b": True}),
            "20261119T110000Z-reviewer": ("c2", {"chk-a": False, "chk-b": True})}, False, "latest result"),
])
def test_a_local_change_without_a_current_passing_after_check_is_refused(tmp_path, row, results, changed, message):
    lc, res = after_fixture(tmp_path, row, results)
    problems = rc.local_change_after_problems("p8cls", ["m.pp"], lc, res, changed=lambda r, f: changed)
    assert any(message in p for p in problems), problems


def test_the_after_check_gate_ignores_other_classes_rows(tmp_path):
    lc, res = after_fixture(tmp_path, "chk-a: PASS after: pending", {})
    assert rc.local_change_after_problems("another", ["m.pp"], lc, res, changed=lambda r, f: False) == []


# HQ 2026-11-22 ruling 2: a changed or removed upstream comment line passes comments_preserved only when the class's
# local-change row lists that exact line and its replacement.
LC_TABLE = ("| # | class | change (file:line) | check | reviewer | date |\n|---|---|---|---|---|---|\n"
            "| 30 | p8test_klass | files/x.py: reads it directly; comment `# This runs the command` -> "
            "`# This reads the file`; comment `#the old list of dicts` -> (removed) | c | r | d |\n"
            "| 31 | other_klass | comment `# not ours` -> (removed) | c | r | d |\n")


def test_listed_comment_changes_are_read_from_the_class_rows_only(tmp_path):
    p = tmp_path / "local_changes.md"
    p.write_text(LC_TABLE)
    assert rc.listed_comment_changes("p8test_klass", p) == [("# This runs the command", "# This reads the file"),
                                                            ("#the old list of dicts", None)]
    assert rc.listed_comment_changes("nobody", p) == []


def test_a_listed_change_is_accepted_only_with_its_replacement_present(tmp_path):
    p = tmp_path / "local_changes.md"
    p.write_text(LC_TABLE)
    listed = rc.listed_comment_changes("p8test_klass", p)
    removed = [("files/x.py", "        # This runs the command"), ("files/x.py", "    #the old list of dicts"),
               ("files/x.py", "    # an unlisted upstream comment")]
    unlisted, accepted = rc.unlisted_comment_removals(removed, listed, {"# This reads the file", "code()"})
    assert unlisted == ["files/x.py: # an unlisted upstream comment"]
    assert accepted == ["files/x.py: # This runs the command", "files/x.py: #the old list of dicts"]
    # the listed replacement missing from the final file: the line is not accepted
    unlisted, accepted = rc.unlisted_comment_removals(removed[:1], listed, {"code()"})
    assert unlisted == ["files/x.py: # This runs the command"] and accepted == []


def test_another_class_rows_do_not_excuse_a_removal(tmp_path):
    p = tmp_path / "local_changes.md"
    p.write_text(LC_TABLE)
    unlisted, _ = rc.unlisted_comment_removals([("f.pp", "# not ours")], rc.listed_comment_changes("p8test_klass", p),
                                               set())
    assert unlisted == ["f.pp: # not ours"]
