"""approval_report.py (HQ after batch 20, item 5): the behaviour approval report, one row per done class, generated from
the recorded state only."""

import sys

import pytest

from conftest import TOOLS

sys.path.insert(0, str(TOOLS))
import approval_report  # noqa: E402
import gen_migration_order as generator  # noqa: E402


def done_classes():
    rows = generator.parse_plan()
    migrations = generator.git_migrations()
    blocked = generator.read_blocked()
    tracker = generator.read_tracker()
    owner_validated = {n for n, r in rows.items() if r.owner_validated}
    retired = generator.retired_classes(tracker, rows, blocked)
    return set(migrations) - set(blocked) - owner_validated - set(retired)


def test_one_row_per_done_class_on_the_repo():
    rows, meta = approval_report.collect()
    names = [r["class"] for r in rows]
    assert len(names) == len(set(names)), "a class appears twice"
    assert set(names) == done_classes()
    assert meta["done"] == len(names)
    text = approval_report.render(rows, meta)
    for name in names:
        assert f"\n### {name}\n" in text and f"\n| {name} | " in text


def test_local_changes_are_read_by_exact_class_cell(tmp_path):
    p = tmp_path / "local_changes.md"
    p.write_text("| # | class | change (file:line) | check | reviewer | date |\n|---|---|---|---|---|---|\n"
                 "| 7 | backup | templates/x.erb:3: the dir declared. More words here. | c | r | d |\n"
                 "| 8 | backup | manifests/y.pp: one more; then a second clause | c | r | d |\n"
                 "| 9 | puppet_backup | not backup's | c | r | d |\n"
                 "| x | backup | not a numbered row | c | r | d |\n")
    got = approval_report.local_changes(p)
    assert got["backup"] == [("7", "templates/x.erb:3: the dir declared."), ("8", "manifests/y.pp: one more;")]
    assert got["puppet_backup"] == [("9", "not backup's")]


def test_a_set_splits_into_proven_and_open_rows(tmp_path, monkeypatch):
    (tmp_path / "p8test_klass.yml").write_text(
        "class: p8test_klass\nbaseline: release-0.9.10 (cf477c6)\nfixture: defaults\n"
        "purpose: >-\n  Does a thing\n  well.\n"
        "outcomes:\n"
        "  - outcome: the thing is done\n    from: manifests/x.pp:1\n    checks: [a, b]\n"
        "  - outcome: the other thing\n    from: manifests/x.pp:2\n"
        "    uncovered: {why: no node, lifted_by: 'capability: one', evidence: e}\n"
        "checks: []\n")
    monkeypatch.setenv("P8_PHASE3_DIR", str(tmp_path))
    row = approval_report.class_row("p8test_klass", None, None, 3, ("fx", "a lift"), [("5", "a change")])
    assert row["purpose"] == "Does a thing well."
    assert row["proven"] == [{"outcome": "the thing is done", "checks": ["a", "b"]}]
    assert row["open"] == [{"outcome": "the other thing", "why": "no node", "lifted_by": "capability: one",
                            "accepted_gap": []}]
    assert row["node"] == "ubuntu" and row["prod"] == 3 and row["standin"] == ("fx", "a lift")


@pytest.mark.parametrize("cls, start", [
    ("user_lock", "to be lifted:"),
    ("node_base_desktop", "to be lifted:"),
    ("user_samba", "accepted; to be tested against the client's Zentyal server"),  # Salatiel 2026-11-27
    ("user_sysmon", "accepted; to be tested on the monitoring server at the cutover"),
    ("openvpn_domain", "accepted (Salatiel, 2026-11-27)"),
    ("letsencrypt_certificate", "stays; for Salatiel's explicit acceptance: a real lift needs a sandbox DNS zone"),
    ("network_vpn", "accepted (Salatiel, 2026-11-27)"),
    ("p8test_no_such_class", "not in HQ's lift list"),
])
def test_standin_plans_follow_hq_item_6(cls, start):
    assert approval_report.standin_plan(cls).startswith(start)


def test_check_mode_reports_a_stale_report(tmp_path, monkeypatch, capsys):
    out = tmp_path / "approval_report.md"
    monkeypatch.setattr(approval_report, "OUT", out)
    monkeypatch.setattr(approval_report, "REPO", tmp_path)
    monkeypatch.setattr(approval_report, "collect", lambda: ([], {"done": 0, "verified": 0, "owner_validated": [],
                                                                  "blocked": [], "retired": []}))
    monkeypatch.setattr(approval_report, "open_escalations", lambda: [])
    assert approval_report.main([]) == 0 and out.is_file()
    assert approval_report.main(["--check"]) == 0
    out.write_text(out.read_text() + "hand edit\n")
    assert approval_report.main(["--check"]) == 1
    assert "APPROVAL REPORT STALE" in capsys.readouterr().err
    assert approval_report.main(["--bogus"]) == 2


def test_accepted_gaps_are_listed_for_salatiels_acceptance(tmp_path, monkeypatch):
    """HQ 2026-11-23 ruling 1c: a parameter variant no production node sets is listed for Salatiel's acceptance."""
    (tmp_path / "p8test_klass.yml").write_text(
        "class: p8test_klass\nbaseline: release-0.9.10 (cf477c6)\nfixture: defaults\n"
        "purpose: >-\n  Does a thing well.\n"
        "outcomes:\n"
        "  - outcome: the strict mode refuses unknown rules\n    from: manifests/x.pp:1\n"
        "    uncovered: {why: one set holds one fixture, accepted_gap: [strict_purge], evidence: e}\n"
        "checks: []\n")
    monkeypatch.setenv("P8_PHASE3_DIR", str(tmp_path))
    row = approval_report.class_row("p8test_klass", None, None, 0, None, [])
    assert row["open"][0]["accepted_gap"] == ["strict_purge"]
    text = approval_report.render([row], {"blocked": [], "done": 1, "owner_validated": [], "retired": [], "verified": 1})
    assert "### Accepted gaps (parameter variants production does not use)" in text
    assert "- **p8test_klass** — strict_purge: the strict mode refuses unknown rules — one set holds one fixture" in text
    assert "accepted gap (production does not use strict_purge)" in text
