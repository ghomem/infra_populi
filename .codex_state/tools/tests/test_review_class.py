"""Reviewer v2 evidence tool: pure pieces, the PASS rule and verdict persistence."""

import importlib.util
import json
import sys

import pytest

from conftest import TOOLS

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


def test_verdict_requires_judgement_and_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "DRAFTS", tmp_path)
    with pytest.raises(SystemExit):
        rc.main(["verdict", "x", "--faithful", "maybe", "--evidence", "e"])
    with pytest.raises(SystemExit):
        rc.main(["verdict", "x", "--faithful", "ok"])


def test_tool_never_prints_commit_authors_or_bodies():
    source = (TOOLS / "review_class.py").read_text()
    assert "%an" not in source and "%ae" not in source and "%b" not in source
    assert '"--format=%H%x09%s"' in source
