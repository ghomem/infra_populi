import importlib.util
import sys
from pathlib import Path

import pytest

sys.dont_write_bytecode = True
GEN = Path(__file__).resolve().parents[2] / "gen_migration_order.py"


@pytest.fixture
def gen():
    spec = importlib.util.spec_from_file_location("gen_migration_order", GEN)
    module = importlib.util.module_from_spec(spec)
    sys.modules["gen_migration_order"] = module
    spec.loader.exec_module(module)
    return module


def test_baseline_name_comes_from_env_file(gen, tmp_path):
    env = tmp_path / "baseline.env"
    env.write_text("# c\nBASELINE_NAME=release-9.9.9\nBASELINE_COMMIT=x\n")
    gen.BASELINE_ENV = env
    assert gen.baseline_name() == "release-9.9.9"


def test_baseline_name_missing_fails(gen, tmp_path):
    env = tmp_path / "baseline.env"
    env.write_text("BASELINE_COMMIT=x\n")
    gen.BASELINE_ENV = env
    with pytest.raises(SystemExit):
        gen.baseline_name()


def test_repo_baseline_is_0_9_10(gen):
    assert gen.baseline_name() == "release-0.9.10"


# --- tracker marker grammar (HQ checkpoint-1 ruling 3)

@pytest.mark.parametrize(
    "line, expected",
    [
        ("user_base", ("user_base", False, "", "")),
        ("backup Done [from: release-0.9.10]", ("backup", True, "release-0.9.10", "")),
        ("Done firewall", ("firewall", True, "", "")),
        ("Done filesystem_yum [from: release-0.9.10]", ("filesystem_yum", True, "release-0.9.10", "")),
        (
            "puppet_boot_run Done [from: release-0.9.10; upstream defect fixed: ensure dropped]",
            ("puppet_boot_run", True, "release-0.9.10", "ensure dropped"),
        ),
        (
            "Done user_base [from: release-0.9.10; upstream defect fixed: exec guarded by its post-condition]",
            ("user_base", True, "release-0.9.10", "exec guarded by its post-condition"),
        ),
    ],
)
def test_tracker_line_grammar(gen, line, expected):
    entry = gen.parse_tracker_line(line)
    assert (entry.name, entry.done, entry.from_ref, entry.defect_fixed) == expected


@pytest.mark.parametrize(
    "line",
    [
        "backup [from: release-0.9.10]",  # marker without Done
        "backup Done [from release-0.9.10]",
        "backup Done [from: release-0.9.10; defect: x]",
        "backup Done [from: release-0.9.10; upstream defect fixed: ]",
        "backup Done extra",
    ],
)
def test_malformed_tracker_line_fails(gen, line):
    with pytest.raises(SystemExit):
        gen.parse_tracker_line(line)


def test_blank_and_comment_lines_are_skipped(gen):
    assert gen.parse_tracker_line("") is None
    assert gen.parse_tracker_line("# note") is None


def test_read_tracker_rejects_duplicates(gen, tmp_path):
    path = tmp_path / "migrated_classes.txt"
    path.write_text("backup Done [from: release-0.9.10]\nDone backup\n")
    with pytest.raises(SystemExit):
        gen.read_tracker(path)


def test_tracker_mismatches(gen, tmp_path):
    path = tmp_path / "migrated_classes.txt"
    path.write_text("a Done [from: r]\nDone b\nc\n")
    entries = gen.read_tracker(path)
    assert gen.tracker_mismatches(entries, {"a", "c"}) == (["c"], ["b"])



# HQ 2026-11-17 ruling 3: a retired class is removed from the module and carries its reason in the tracker.
def test_retired_tracker_line(gen):
    entry = gen.parse_tracker_line("old_ppa Retired [reason: PPA workarounds are not carried forward]")
    assert (entry.name, entry.done, entry.retired) == ("old_ppa", False, "PPA workarounds are not carried forward")


@pytest.mark.parametrize("line", ["old_ppa Retired", "old_ppa Retired [reason: ]", "old_ppa Retired [from: r]",
                                  "old_ppa Done Retired [reason: x]"])
def test_malformed_retired_line_fails(gen, line):
    with pytest.raises(SystemExit):
        gen.parse_tracker_line(line)


def retired_setup(gen, tmp_path):
    path = tmp_path / "migrated_classes.txt"
    path.write_text("old_ppa Retired [reason: gone]\nbackup Done [from: r]\n")
    (tmp_path / "manifests").mkdir()
    return gen.read_tracker(path)


def test_retired_classes_must_be_gone_from_plan_blocked_and_manifests(gen, tmp_path):
    tracker = retired_setup(gen, tmp_path)
    row = gen.parse_plan()["backup"]
    assert gen.retired_classes(tracker, {"backup": row}, {}, tmp_path / "manifests") == {"old_ppa": "gone"}
    for rows, blocked in [({"old_ppa": row}, {}), ({}, {"old_ppa": "cat 5"})]:
        with pytest.raises(SystemExit):
            gen.retired_classes(tracker, rows, blocked, tmp_path / "manifests")
    (tmp_path / "manifests" / "old_ppa.pp").write_text("class x {}\n")
    with pytest.raises(SystemExit):
        gen.retired_classes(tracker, {}, {}, tmp_path / "manifests")


def test_render_counts_and_lists_retired_classes(gen):
    rows = gen.parse_plan()
    tracker = {"old_ppa": gen.TrackerEntry("old_ppa", False, "", "", retired="PPA for focal only")}
    text = gen.render(rows, set(), {}, set(), [], set(), set(), tracker)
    assert f"/ 1 retired / {len(rows) + 1} total." in text
    assert "## RETIRED" in text and "`puppet_infrastructure::old_ppa` — PPA for focal only" in text

@pytest.mark.repo_state  # inconsistent by design while record_green's own commit is being made
def test_repo_tracker_parses_and_matches_git(gen):
    entries = gen.read_tracker()
    rows = gen.parse_plan()
    owner_validated = {name for name, row in rows.items() if row.owner_validated}
    done = set(gen.git_migrations()) - set(gen.read_blocked()) - owner_validated
    assert gen.tracker_mismatches(entries, done) == ([], [])


def test_render_lists_upstream_defect_markers(gen):
    rows = gen.parse_plan()
    tracker = {"puppet_boot_run": gen.TrackerEntry("puppet_boot_run", True, "release-0.9.10", "ensure dropped")}
    text = gen.render(rows, set(), {}, set(), [], set(), set(), tracker)
    assert "## UPSTREAM DEFECTS FIXED LOCALLY" in text
    assert "`puppet_infrastructure::puppet_boot_run` [from: release-0.9.10] — ensure dropped" in text


# --- step 4.3: fleet-weighted order and the HQ re-migration queue

FLEET = """# x

## Class table (sorted by production node statements)

| class | prod | servers | desktop stmts | deleted | tests | via | conditional | migration status |
|---|---:|---:|---|---:|---:|---|---|---|
| `heavy` | 58 | 58 | 0 | 9 | 1 | via_composite=68 |  | PENDING |
| `light` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |

## Other table
| class | type |
|---|---|
| `ignored` | class |
"""


def row(gen, name, cx=1, deps=()):
    return gen.ClassRow(name, cx, 1, 1, "yes", tuple(deps), "class", "", (), (), "")


def test_prod_nodes_parse_only_the_class_table(gen, tmp_path):
    f = tmp_path / "fleet.md"
    f.write_text(FLEET)
    assert gen.read_prod_nodes(f) == {"heavy": 58, "light": 1}  # no desktop statements in the fixture
    assert gen.read_prod_nodes(tmp_path / "missing.md") == {}


def test_prod_is_the_secondary_key_after_dependencies(gen):
    rows = {r.name: r for r in [row(gen, "zero", cx=1), row(gen, "light", cx=1), row(gen, "heavy", cx=9),
                                row(gen, "heavy_child", cx=1, deps=["light"])]}
    order, _ = gen.topological_pending(rows, set(), set(), set(), {"heavy": 58, "light": 1, "heavy_child": 58})
    names = [r.name for r in order]
    assert names.index("heavy") < names.index("light") < names.index("zero")  # prod beats complexity
    assert names.index("light") < names.index("heavy_child")                  # dependencies still first
    assert names[-1] == "zero"                                                # zero declarations sink


def test_remigration_queue_drops_verified_classes_and_orders_next_class(gen, tmp_path):
    order = tmp_path / "order.txt"
    order.write_text("# c\nb first\na first\nz sink\n")
    reviews = tmp_path / "reviews"
    (reviews / "a").mkdir(parents=True)
    (reviews / "a" / "20261027T000000Z.json").write_text('{"verdict": "PASS", "migrate_commit": "aaaaaaaaaaaa"}')
    migrations = {n: gen.MigrationCommit(c * 40, "d") for n, c in (("a", "a"), ("b", "b"), ("z", "c"))}
    queue = gen.remigration_queue(migrations, set(), reviews, order)
    assert queue == [("b", "first"), ("z", "sink")]
    assert gen.next_class_name([row(gen, "p")], queue) == "puppet_infrastructure::b (re-migration)"
    assert gen.next_class_name([row(gen, "p")], [("z", "sink")]) == "puppet_infrastructure::p"
    assert gen.next_class_name([], [("z", "sink")]) == "puppet_infrastructure::z (re-migration)"


def test_bad_remigration_line_fails(gen, tmp_path):
    order = tmp_path / "order.txt"
    order.write_text("a later\n")
    with pytest.raises(SystemExit):
        gen.read_remigration_order(order)


def test_repo_queue_follows_the_hq_order(gen):
    migrations = gen.git_migrations()
    queue = gen.remigration_queue(migrations, gen.find_flagged_migrations(migrations))
    firsts = [n for n, w in queue if w == "first"]
    assert firsts == [n for n in ["rsyslog_base", "rsyslog_client", "docker_container", "filesystem_yum",
                                  "backup_rsnapshot_pre"] if n in firsts]


def test_mock_apply_marker_grammar(gen):
    e = gen.parse_tracker_line("user_sysmon Done [from: release-0.9.10; mock-apply: Naemon/Thruk paths synthetic]")
    assert (e.from_ref, e.defect_fixed, e.mock_apply) == ("release-0.9.10", "", "Naemon/Thruk paths synthetic")
    e = gen.parse_tracker_line("x Done [from: 874f854; upstream defect fixed: guard; mock-apply: stand-ins]")
    assert (e.from_ref, e.defect_fixed, e.mock_apply) == ("874f854", "guard", "stand-ins")


def test_repo_node_fixtures_exist_for_the_planned_classes(gen):
    rows = gen.parse_plan()
    assert rows["user_sysmon"].node_fixture == "sysmon_server"
    assert rows["user_samba"].node_fixture == "samba_dc_standin"
    assert rows["hashman_base"].node_fixture == ""  # HQ 2026-11-17 ruling 2: a plain GREEN (the agent ships the code tree)
    assert rows["hashman_web"].node_fixture == "hashman_master_standin"  # the site logo files
    assert rows["user_lock"].node_fixture == "hashman_user_via_hashman"  # a user hashman creates (a test asset)
    assert rows["letsencrypt_certificate"].node_fixture == "letsencrypt_cert_standin"  # stand-in live certificate
    assert rows["node_base_domain_desktop"].node_fixture == "puppet_agent_standin"  # Service['puppet'] without a daemon
    assert rows["openvpn_server"].node_fixture == "p8test_dhcp_primary"  # stand-in DHCP primary interface (veth + netns)
    assert rows["network_vpn"].node_fixture == "p8test_dhcp_primary"  # declares openvpn_server: same stand-in
    assert rows["node_base_desktop"].node_fixture == "puppet_agent_standin"  # Service['puppet'] without a daemon
    assert rows["openvpn_nm_connection"].node_fixture == "p8test_vpn_ca"  # the CA file it requires, never declares
    assert rows["mount_shares_desktop"].node_fixture == "p8test_desktop_home"  # the user's ~/Desktop, never declared
    assert rows["openvpn_domain"].node_fixture == "p8test_domain_dns"  # the lab domain's DNS (the DC p8lab-dc)
    assert sum(1 for r in rows.values() if r.node_fixture) == 12


def test_expected_run2_events_parse(gen):
    rows = gen.parse_plan()
    assert rows["packages_base"].expected_run2_events == ("Exec[apt_update]", "Exec[dnf-makecache]")  # RedHat: rhel9 pass
    # every entry is a reviewed, justified exception (HQ 2026-11-10 ruling 1): keep this set explicit
    assert {n for n, r in rows.items() if r.expected_run2_events} == {"packages_base", "node_base", "nginx_frontend_domain",
                                                                      "nginx_frontend", "hashman_web", "linux_policies_user",
                                                                      "node_base_domain_desktop", "mariadb_server",
                                                                      "node_base_desktop", "nginx_frontend_mail"}
    assert rows["node_base"].expected_run2_events == ("Exec[apt_update]", "Exec[dnf-makecache]")
    # HQ batch-7 ruling 1: each resource named exactly (the p8testuser fixture's titles), no glob
    tmp = "/opt/puppet-infrastructure/linux-policies/TMP/p8testuser.sh.tmp"
    assert rows["linux_policies_user"].expected_run2_events == (f"File[{tmp}]", f"File_line[{tmp}_0]",
                                                                f"File_line[{tmp}_1]",
                                                                # with a desktop session: the policies run every agent run
                                                                "Exec[Execute linux policies for: p8testuser]")



def test_desktop_statement_weighs_twenty_machines(gen, tmp_path):
    f = tmp_path / "fleet.md"
    f.write_text("| class | prod | servers | desktop stmts | deleted |\n|---|---:|---:|---|---:|\n"
                 "| `both` | 59 | 58 | 1 (≈20) | 9 |\n| `desk` | 1 | 0 | 1 (≈20) | 0 |\n| `three` | 3 | 3 | 0 | 0 |\n")
    assert gen.read_prod_nodes(f) == {"both": 78, "desk": 20, "three": 3}


def test_repo_desktop_closure_sorts_above_the_three_node_tier(gen):
    prod = gen.read_prod_nodes()
    assert prod["gnome_lock_screen"] == 20 and prod["firewall_secure"] == 78
    assert prod["gnome_lock_screen"] > prod["openvpn_server"] == 3


def test_plan_node_column_names_a_lab_node_kind(gen, tmp_path, monkeypatch):
    """HQ 2026-11-16 item 2: a plan row may name the node kind it is tested on; empty = the inventory default."""
    rows = gen.parse_plan()
    assert all(r.node in ("",) or r.node in gen.lab_node_kinds() for r in rows.values())
    text = gen.PLAN_PATH.read_text()
    lines = text.splitlines(keepends=True)
    i = next(i for i, l in enumerate(lines) if l.startswith("| `puppet_infrastructure::gnome_lock_screen` |"))
    lines[i] = lines[i].rstrip("\n")[:-1] + "kubuntu|\n"
    plan = tmp_path / "plan.md"
    plan.write_text("".join(lines))
    monkeypatch.setattr(gen, "PLAN_PATH", plan)
    assert gen.parse_plan()["gnome_lock_screen"].node == "kubuntu"
    lines[i] = lines[i].replace("kubuntu|", "solaris|")
    plan.write_text("".join(lines))
    with pytest.raises(SystemExit):
        gen.parse_plan()


def test_required_base_os_family_qualifier(gen):
    """HQ 2026-11-18 ruling A2: production composes these classes under node_base, which includes filesystem_lib64 on
    Debian only and extra_packages_el (through packages_base) on RedHat only; the harness follows the target's family."""
    rows = gen.parse_plan()
    sysmon = rows["sysmon_base"]
    assert sysmon.bases_for("Debian") == ("filesystem_base", "packages_base", "filesystem_lib64")
    assert sysmon.bases_for("RedHat") == ("filesystem_base", "packages_base")
    assert sysmon.required_base == sysmon.bases_for("Debian")  # its lab node is the Ubuntu default
    for name in ("hello_world_flask_common", "hello_world_flask"):
        assert "extra_packages_el" in rows[name].bases_for("RedHat")
        assert "extra_packages_el" not in rows[name].required_base
    assert {n for n, r in rows.items() for _, only in r.required_base_spec if only} == {
        "sysmon_base", "hello_world_flask_common", "hello_world_flask"}


def test_required_base_qualifier_must_name_an_os_family(gen, tmp_path, monkeypatch):
    text = gen.PLAN_PATH.read_text()
    plan = tmp_path / "plan.md"
    plan.write_text(text.replace("packages_base, filesystem_lib64 [Debian]", "packages_base, filesystem_lib64 [Suse]"))
    monkeypatch.setattr(gen, "PLAN_PATH", plan)
    with pytest.raises(SystemExit):
        gen.parse_plan()


def test_classify_resolves_required_base_for_the_os_family(monkeypatch):
    import json
    import os
    import subprocess

    def classify(*extra, env=None):
        return subprocess.run([sys.executable, str(GEN), "--classify", "sysmon_base", *extra], capture_output=True,
                              text=True, env={**os.environ, **(env or {})})

    monkeypatch.delenv("P8_NODE", raising=False)
    plain = json.loads(classify(env={"P8_NODE": ""}).stdout)
    assert plain["required_base_os_family"] == "Debian" and "filesystem_lib64" in plain["required_base"]
    assert "filesystem_lib64 [Debian]" in plain["required_base_spec"]
    redhat = json.loads(classify("--os-family", "RedHat").stdout)
    assert redhat["required_base"] == ["filesystem_base", "packages_base"]
    by_node = json.loads(classify(env={"P8_NODE": "rhel9"}).stdout)  # review_class --node rhel9 exports P8_NODE
    assert by_node["required_base_os_family"] == "RedHat" and "filesystem_lib64" not in by_node["required_base"]
    assert classify("--os-family", "Suse").returncode != 0


def test_local_change_marker_grammar(gen):
    # HQ 2026-11-18 policy B: a purpose fix is marked in the tracker, before any mock-apply
    e = gen.parse_tracker_line("rsyslog_base Done [from: release-0.9.10; local change: restarts on TLS file changes]")
    assert e.local_change == "restarts on TLS file changes" and e.defect_fixed == "" and e.mock_apply == ""
    e = gen.parse_tracker_line("x Done [from: release-0.9.10; upstream defect fixed: d; local change: l; mock-apply: m]")
    assert (e.defect_fixed, e.local_change, e.mock_apply) == ("d", "l", "m")


def test_local_changes_marker_lists_row_numbers(gen):
    # HQ batch-12 ruling 4: `; local changes: #N, #M`, generated; the legacy free-text form still parses
    e = gen.parse_tracker_line("sysmon_base Done [from: release-0.9.10; local changes: #3, #4]")
    assert e.local_change == "#3, #4" and gen.local_change_numbers(e.local_change) == [3, 4]
    e = gen.parse_tracker_line("x Done [from: release-0.9.10; upstream defect fixed: d; local changes: #5; mock-apply: m]")
    assert (e.defect_fixed, e.local_change, e.mock_apply) == ("d", "#5", "m")
    assert gen.local_change_numbers("restarts on TLS file changes") is None
    assert gen.local_change_numbers("") is None
