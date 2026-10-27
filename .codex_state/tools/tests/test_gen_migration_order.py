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
    assert gen.read_prod_nodes(f) == {"heavy": 58, "light": 1}
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
    assert sum(1 for r in rows.values() if r.node_fixture) == 2
