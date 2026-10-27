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
