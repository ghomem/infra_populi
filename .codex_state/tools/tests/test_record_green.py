"""record_green.sh (step 3.2) in a throwaway clone with a bare origin: it refuses unless the code is what
went GREEN, the header is there and the worktree holds only the class; then tracker + commits + push."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import TOOLS

REPO = TOOLS.parents[1]
CLS = "sysmon_fs_health"  # pending, identical to the baseline, plain tracker line
HEADER = ("# Puppet 8 migration: release-0.9.10 manifest validated unchanged.\n"
          "# Module dependencies: none.\n")
INVENTORY = "MODULE firewall env puppetlabs-firewall 8.3.0\n"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def clone(tmp_path, lab):
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", "--bare", str(REPO), str(origin)], check=True)
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "config", "user.name", "test")
    # overlay the tools under test (they may be uncommitted in the real repo), committed in the clone
    for src in [*TOOLS.glob("*.py"), *TOOLS.glob("*.sh"), REPO / ".codex_state/gen_migration_order.py"]:
        dst = work / src.relative_to(REPO)
        dst.write_bytes(src.read_bytes())
        dst.chmod(src.stat().st_mode)
    git(work, "add", "-A")
    if git(work, "status", "--porcelain"):
        git(work, "commit", "-q", "-m", "test: overlay tools under test")
        git(work, "push", "-q")
    (work / ".codex_state" / "necessary_modules.txt").write_text("puppetlabs-stdlib\n")
    lab.world["ssh"].insert(0, {"match": "bash -s", "stdout": INVENTORY})
    env = {"P8_GREEN_DIR": str(tmp_path / "green"), "P8_COMPOSITE_CMD": "true", "P8_PUPPETFILE_CMD": "true"}

    class Clone:
        root, bare = work, origin

        def run(self, *args, **extra):
            return lab.run(["bash", str(work / ".codex_state/tools/record_green.sh"), CLS, *args],
                           env={**env, **extra}, cwd=work)

        def stamp(self):
            return lab.run(["python3", str(work / ".codex_state/tools/records.py"), "stamp", "--run1-events", "3",
                            "--", CLS], env=env, cwd=work)

        def add_header(self):
            path = work / f"manifests/{CLS}.pp"
            path.write_text(HEADER + path.read_text())

    return Clone()


def tracker_line(root, cls=CLS):
    return next(l for l in (root / ".codex_state/migrated_classes.txt").read_text().splitlines()
                if l.split()[0] == cls or l.split()[:2] == ["Done", cls])


def test_happy_path_records_commits_regenerates_and_pushes(clone):
    assert clone.stamp().returncode == 0
    clone.add_header()
    proc = clone.run()
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert tracker_line(clone.root) == f"{CLS} Done [from: release-0.9.10]"
    subjects = git(clone.root, "log", "--format=%s", "-2").splitlines()
    assert subjects == [f"P8: regenerate migration order after {CLS}", f"P8: migrate puppet_infrastructure::{CLS}"]
    files = git(clone.root, "show", "--name-only", "--format=", "HEAD~1").split()
    assert sorted(files) == [".codex_state/migrated_classes.txt", f"manifests/{CLS}.pp"]
    assert git(clone.bare, "rev-parse", "main") == git(clone.root, "rev-parse", "HEAD")
    assert git(clone.root, "status", "--porcelain") == ""


def test_defect_marker(clone):
    clone.stamp()
    clone.add_header()
    proc = clone.run("--defect", "exec guarded by its post-condition", "--no-push")
    assert proc.returncode == 0, proc.stderr
    assert tracker_line(clone.root) == \
        f"{CLS} Done [from: release-0.9.10; upstream defect fixed: exec guarded by its post-condition]"


def test_no_stamp_is_refused(clone):
    clone.add_header()
    head = git(clone.root, "rev-parse", "HEAD")
    proc = clone.run("--no-push")
    assert proc.returncode == 1 and "NO GREEN STAMP" in proc.stderr
    assert git(clone.root, "rev-parse", "HEAD") == head


def test_code_changed_after_green_is_refused_but_header_is_not_a_code_change(clone):
    clone.stamp()
    clone.add_header()  # comment lines only: stamp still valid
    path = clone.root / f"manifests/{CLS}.pp"
    path.write_text(path.read_text().replace("{", "{\n  $p8_extra = 1", 1))
    proc = clone.run("--no-push")
    assert proc.returncode == 1 and "STALE GREEN STAMP" in proc.stderr
    assert tracker_line(clone.root) == CLS


def test_missing_header_is_refused(clone):
    clone.stamp()
    proc = clone.run("--no-push")
    assert proc.returncode == 1 and "NO HEADER" in proc.stderr


def test_unrelated_dirty_file_is_refused(clone):
    clone.stamp()
    clone.add_header()
    (clone.root / "manifests/backup.pp").write_text("# x\n" + (clone.root / "manifests/backup.pp").read_text())
    proc = clone.run("--no-push")
    assert proc.returncode == 1 and "manifests/backup.pp" in proc.stderr


def test_composite_diff_refuses_with_exit_4_and_commits_nothing(clone):
    clone.stamp()
    clone.add_header()
    head = git(clone.root, "rev-parse", "HEAD")
    proc = clone.run("--no-push", P8_COMPOSITE_CMD="false")
    assert proc.returncode == 4
    assert git(clone.root, "rev-parse", "HEAD") == head
    assert tracker_line(clone.root) == CLS


def test_header_modules_feed_necessary_modules(clone):
    clone.stamp()
    path = clone.root / f"manifests/{CLS}.pp"
    path.write_text("# Puppet 8 migration: release-0.9.10 manifest validated unchanged.\n"
                    "# Module dependency: puppetlabs-firewall 8.3.0.\n" + path.read_text())
    proc = clone.run("--no-push")
    assert proc.returncode == 0, proc.stderr
    assert (clone.root / ".codex_state/necessary_modules.txt").read_text().splitlines() == \
        ["puppetlabs-stdlib", "puppetlabs-firewall"]


def test_harness_green_writes_the_stamp(lab, tmp_path):
    lab.world["ssh"].insert(0, {"match": r"agent -t", "outputs": [
        {"rc": 2, "stdout": "Notice: /Stage[main]/X/File[/a]/ensure: created\n"}, {"rc": 0, "stdout": ""}]})
    lab.world["ssh"].insert(0, {"match": r"python3 - puppet_infrastructure::dns_client",
                                "stdout": "COVERAGE puppet_infrastructure::dns_client: 1 concrete resources (+0 defined-type instances)\n"})
    green = tmp_path / "green"
    proc = lab.run([str(TOOLS / "test_class.sh"), "--revert-first", "dns_client"], env={"P8_GREEN_DIR": str(green)})
    assert proc.returncode == 0, proc.stderr
    stamp = json.loads((green / "dns_client.json").read_text())
    assert stamp["revert_first"] is True and stamp["run1_events"] == 1
    assert stamp["coverage"][0].startswith("COVERAGE puppet_infrastructure::dns_client: 1 concrete")
    check = lab.run(["python3", str(TOOLS / "records.py"), "verify-stamp", "dns_client"], env={"P8_GREEN_DIR": str(green)})
    assert check.returncode == 0, check.stderr


def test_tracker_text_rewrites_historical_order_to_canonical(tmp_path):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("records_under_test", TOOLS / "records.py")
    records = importlib.util.module_from_spec(spec)
    sys.modules["records_under_test"] = records
    spec.loader.exec_module(records)
    text = "a\nDone firewall\nb Done [from: x]\n"
    assert records.tracker_text(text, "firewall", "release-0.9.10", "") == \
        "a\nfirewall Done [from: release-0.9.10]\nb Done [from: x]\n"
    with pytest.raises(SystemExit):
        records.tracker_text(text, "missing", "release-0.9.10", "")
    assert records.code_lines("m.pp", b"# h\n\nclass x {\n  # c\n  a => 1,\n}\n") == b"class x {\n  a => 1,\n}"


def test_fix_mode_commits_comment_and_tracker_only_as_a_record_commit(clone, lab):
    done = "backup"
    env = {"P8_GREEN_DIR": str(clone.root.parent / "green")}
    lab.run(["python3", str(clone.root / ".codex_state/tools/records.py"), "stamp", "--", done], env=env)
    path = clone.root / f"manifests/{done}.pp"
    path.write_text(path.read_text().replace("# Puppet 8 migration:", "# Puppet 8 migration (records fix):", 1))
    proc = lab.run(["bash", str(clone.root / ".codex_state/tools/record_green.sh"), done, "--fix", "header wording",
                    "--no-push"], env={**env, "P8_COMPOSITE_CMD": "true", "P8_PUPPETFILE_CMD": "true"}, cwd=clone.root)
    assert proc.returncode == 0, proc.stderr
    assert git(clone.root, "log", "--format=%s", "-2").splitlines()[1] == f"P8: record {done}: header wording"


def test_fix_mode_refuses_a_code_change(clone, lab):
    done = "backup"
    env = {"P8_GREEN_DIR": str(clone.root.parent / "green")}
    path = clone.root / f"manifests/{done}.pp"
    path.write_text(path.read_text().replace("{", "{\n  $p8_extra = 1", 1))
    lab.run(["python3", str(clone.root / ".codex_state/tools/records.py"), "stamp", "--", done], env=env)
    proc = lab.run(["bash", str(clone.root / ".codex_state/tools/record_green.sh"), done, "--fix", "x", "--no-push"],
                   env={**env, "P8_COMPOSITE_CMD": "true", "P8_PUPPETFILE_CMD": "true"}, cwd=clone.root)
    assert proc.returncode == 1 and "may not change code" in proc.stderr


def test_fix_mode_refuses_a_class_that_is_not_recorded(clone):
    clone.stamp()
    clone.add_header()
    proc = clone.run("--fix", "x", "--no-push")
    assert proc.returncode == 1 and "not Done" in proc.stderr


def test_orientation_reads_the_params_file_the_harness_reads(tmp_path):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location("orientation_under_test", TOOLS / "orientation.py")
    orientation = importlib.util.module_from_spec(spec)
    sys.modules["orientation_under_test"] = orientation
    spec.loader.exec_module(orientation)
    (tmp_path / "puppet_infrastructure::dns_client.json").write_text('{"nameservers": ["192.0.2.53"]}')
    line = orientation.params_line("dns_client", tmp_path)
    assert line.endswith("puppet_infrastructure::dns_client.json keys: nameservers")
    assert "192.0.2.53" not in line  # keys only, never values
    assert orientation.params_line("backup", tmp_path).startswith("none")


def test_header_naming_a_module_without_a_version_is_refused(clone):
    # real case 2026-10-27: "puppetlabs-firewall 8 attribute renames" failed the reviewer's header_modules
    clone.stamp()
    path = clone.root / f"manifests/{CLS}.pp"
    path.write_text("# Puppet 8 migration: release-0.9.10 manifest; puppetlabs-firewall 8 attribute renames only.\n"
                    "# Module dependency: puppetlabs-firewall 8.3.0.\n" + path.read_text())
    proc = clone.run("--no-push")
    assert proc.returncode == 1 and "puppetlabs-firewall without a version" in proc.stderr


def test_record_event_and_metrics_close_commit(clone, lab):
    import json
    clone.stamp()
    clone.add_header()
    assert clone.run("--no-push").returncode == 0
    events = [json.loads(l) for l in (lab.root / "metrics" / "events.jsonl").read_text().splitlines()]
    assert events[-1]["kind"] == "record" and len(events[-1]["data"]["commits"]) == 2
    runs = clone.root / ".codex_state/runs/metrics.jsonl"
    proc = lab.run(["python3", str(clone.root / ".codex_state/tools/metrics.py"), "close", CLS, "--outcome", "GREEN",
                    "--path", "unchanged-validated"], env={"P8_RUNS_FILE": str(runs)}, cwd=clone.root)
    assert proc.returncode == 0, proc.stderr
    assert git(clone.root, "log", "--format=%s", "-1").strip() == f"P8: record metrics after {CLS}"
    assert git(clone.root, "show", "--name-only", "--format=", "HEAD").split() == [".codex_state/runs/metrics.jsonl"]
    record = json.loads(runs.read_text().splitlines()[-1])
    assert record["commits"] and record["path"] == "unchanged-validated"
    assert git(clone.bare, "rev-parse", "main") == git(clone.root, "rev-parse", "HEAD")


def test_puppetfile_export_out_of_date_is_refused(clone):
    clone.stamp()
    clone.add_header()
    head = git(clone.root, "rev-parse", "HEAD")
    proc = clone.run("--no-push", P8_PUPPETFILE_CMD="false")
    assert proc.returncode == 1 and "differs from .codex_state/lab/Puppetfile" in proc.stderr
    assert git(clone.root, "rev-parse", "HEAD") == head


def test_updated_puppetfile_export_rides_with_the_class_commit(clone):
    clone.stamp()
    clone.add_header()
    export = clone.root / ".codex_state/lab/Puppetfile"
    export.write_text(export.read_text() + "mod 'puppet-example', '1.2.3'\n")
    assert clone.run("--no-push").returncode == 0
    files = git(clone.root, "show", "--name-only", "--format=", "HEAD~1").split()
    assert ".codex_state/lab/Puppetfile" in files
