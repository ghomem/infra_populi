"""snapshot_master.sh (HQ VM-operations ruling): take-only, offline via ACPI, refuses on every unsafe state."""

import json
import subprocess

import pytest

from conftest import TOOLS

REPO = TOOLS.parents[1]
MASTER = "Ubuntu24-puppet8-Master"
NODE = "ubuntu24-puppet8-Node"
MODULES = "/etc/puppetlabs/code/environments/production/modules\n├── puppetlabs-stdlib (v9.7.0)\n└── saz-sudo (v9.0.2)\n"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout


@pytest.fixture
def clone(tmp_path, lab):
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(REPO), str(work)], check=True)
    git(work, "config", "user.email", "t@example.invalid")
    git(work, "config", "user.name", "t")
    for src in [*TOOLS.glob("*.py"), *TOOLS.glob("*.sh")]:
        dst = work / src.relative_to(REPO)
        dst.write_bytes(src.read_bytes())
        dst.chmod(src.stat().st_mode)
    git(work, "add", "-A")
    if git(work, "status", "--porcelain"):
        git(work, "commit", "-q", "-m", "test: overlay tools")
    lab.world["ssh"][:0] = [
        {"match": r"puppet module list", "stdout": MODULES},
        {"match": r"systemctl is-active puppetserver; curl", "stdout": "active\nrunning\n"},
        {"match": r"puppet8master true$", "stdout": ""},
    ]
    lab.world["vms"][MASTER]["snapshots"] = [{"name": "P8MASTER_BASELINE_GREEN_v3", "uuid": "uuid-v3"}]
    record = tmp_path / "master_snapshots.jsonl"

    class Clone:
        root = work
        rec = record

        def run(self, *args, **env):
            return lab.run(["bash", str(work / ".codex_state/tools/snapshot_master.sh"), *args],
                           env={"P8_PUPPETFILE_CMD": "true", "P8_SNAPSHOT_RECORD": str(record),
                                "ACPI_TIMEOUT_SECONDS": "15", "BOOT_TIMEOUT_SECONDS": "15", **env}, cwd=work)
    return Clone()


def vbox_verbs(lab, vm):
    return [c[1:3] if c[1] in ("controlvm", "snapshot") else c[1:2] for c in lab.calls("VBoxManage") if vm in c]


def assert_nothing_done_to_the_master(lab):
    for call in lab.calls("VBoxManage"):
        if MASTER in call:
            assert call[1] in ("showvminfo",) or call[1:3] == ["snapshot", MASTER] and call[3] == "list", call


def test_happy_path_takes_offline_restarts_verifies_and_records(clone, lab):
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4")
    assert proc.returncode == 0, proc.stderr
    calls = lab.calls("VBoxManage")
    acpi = calls.index(["VBoxManage", "controlvm", MASTER, "acpipowerbutton"])
    take = next(i for i, c in enumerate(calls) if c[1:4] == ["snapshot", MASTER, "take"])
    start = calls.index(["VBoxManage", "startvm", MASTER, "--type", "headless"])
    assert acpi < take < start
    assert not any(c[1] == "controlvm" and c[3] == "poweroff" for c in calls)  # never a hard poweroff
    assert not any(c[1] == "snapshot" and c[3] in ("restore", "delete", "restorecurrent", "edit") for c in calls)
    assert not any(NODE in c for c in calls)  # never touches the node
    desc = lab.state()["vms"][MASTER]["last_description"]
    assert "repo " in desc and "baseline release-0.9.10 (cf477c6)" in desc and "Puppetfile sha256" in desc \
        and "module list sha256" in desc and "(2 modules)" in desc
    (rec,) = [json.loads(l) for l in clone.rec.read_text().splitlines()]
    assert rec["name"] == "P8MASTER_BASELINE_GREEN_v4" and rec["uuid"] == "uuid-2"
    assert "8140 running" in proc.stdout


@pytest.mark.parametrize("name", ["v4", "P8MASTER_", "P8MASTER_a-b", "P8NODE_BASELINE_GREEN_v3", "P8MASTER_X; rm"])
def test_bad_name_is_refused(clone, lab, name):
    proc = clone.run(name)
    assert proc.returncode == 1 and "must match" in proc.stderr
    assert_nothing_done_to_the_master(lab)


def test_existing_name_is_refused(clone, lab):
    proc = clone.run("P8MASTER_BASELINE_GREEN_v3")
    assert proc.returncode == 1 and "already exists" in proc.stderr
    assert_nothing_done_to_the_master(lab)


@pytest.mark.parametrize("busy", ["4242 bash .codex_state/tools/test_class.sh --revert-first backup",
                                  "4243 timeout --kill-after=30 1800 codex exec -c sandbox",
                                  "4244 python3 .codex_state/tools/review_class.py check backup --fresh"])
def test_refuses_during_a_harness_codex_or_reviewer_run(clone, lab, busy):
    lab.world["busy"] = busy
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4")
    assert proc.returncode == 1 and "engine run is in progress" in proc.stderr
    assert_nothing_done_to_the_master(lab)


def test_master_not_running_is_refused(clone, lab):
    lab.world["vms"][MASTER]["state"] = "poweroff"
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4")
    assert proc.returncode == 1 and "expected running" in proc.stderr
    assert_nothing_done_to_the_master(lab)


def test_puppetfile_drift_is_refused_before_shutdown(clone, lab):
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4", P8_PUPPETFILE_CMD="false")
    assert proc.returncode == 1 and "Puppetfile differs" in proc.stderr
    assert_nothing_done_to_the_master(lab)


def test_dirty_worktree_is_refused(clone, lab):
    (clone.root / "manifests" / "backup.pp").write_text("# dirty\n")
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4")
    assert proc.returncode == 1 and "worktree not clean" in proc.stderr
    assert_nothing_done_to_the_master(lab)


def test_acpi_timeout_never_forces_and_takes_no_snapshot(clone, lab):
    lab.world["acpi_works"] = False
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4")
    assert proc.returncode == 1 and "NOT forcing it" in proc.stderr
    calls = lab.calls("VBoxManage")
    assert ["VBoxManage", "controlvm", MASTER, "acpipowerbutton"] in calls
    assert not any(c[1] == "controlvm" and c[3] == "poweroff" for c in calls)
    assert not any(c[1:4] == ["snapshot", MASTER, "take"] for c in calls)
    assert lab.state()["vms"][MASTER]["state"] == "running"  # left as it was
    assert not clone.rec.exists()


def test_dry_run_describes_and_touches_nothing(clone, lab):
    proc = clone.run("P8MASTER_BASELINE_GREEN_v4", "--dry-run")
    assert proc.returncode == 0 and "DESCRIPTION: infra_populi lab master" in proc.stdout
    assert_nothing_done_to_the_master(lab)


def test_settings_allow_read_only_vboxmanage_and_keep_destructive_verbs_denied():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text())["permissions"]
    allow, deny = settings["allow"], settings["deny"]
    assert "Bash(VBoxManage *)" not in allow  # no blanket VBoxManage
    for entry in ("Bash(.codex_state/tools/snapshot_master.sh *)", "Bash(VBoxManage list *)",
                  "Bash(VBoxManage showvminfo *)", f"Bash(VBoxManage snapshot {NODE} list*)",
                  f"Bash(VBoxManage snapshot {MASTER} list*)"):
        assert entry in allow, entry
    for vm in (MASTER, NODE):
        for verb in ("restore", "restorecurrent", "delete", "edit"):
            assert f"Bash(VBoxManage snapshot {vm} {verb}*)" in deny, (vm, verb)
    for entry in ("Bash(VBoxManage unregistervm *)", "Bash(VBoxManage modifyvm *)",
                  f"Bash(VBoxManage controlvm {MASTER} poweroff*)", f"Bash(VBoxManage snapshot {MASTER} take*)"):
        assert entry in deny, entry
