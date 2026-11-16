"""lab_vm.sh (HQ 2026-11-16 item 3): guarded operations on p8lab-* VMs only; a clone's source is never modified;
no start below 4 GB free; no delete. Every refusal path."""

import json

import pytest

from conftest import TOOLS

pytestmark = pytest.mark.slow

SCRIPT = str(TOOLS / "lab_vm.sh")
MASTER, NODE = "Ubuntu24-puppet8-Master", "ubuntu24-puppet8-Node"


@pytest.fixture
def vms(lab, tmp_path):
    lab.world["vms"].update({
        "RHEL9": {"state": "poweroff", "memory": 4096, "snapshots": [{"name": "clean", "uuid": "u-c"}],
                  "config": {"ostype": "RedHat_64"}},
        "kubuntu-desktop": {"state": "running", "memory": 4096, "snapshots": [{"name": "fresh", "uuid": "u-f"}]},
        "p8lab-rhel9": {"state": "poweroff", "memory": 4096, "snapshots": [{"name": "P8LAB_BASE", "uuid": "u-b"}]},
        "p8lab-busy": {"state": "running", "memory": 2048, "snapshots": []},
    })
    meminfo = tmp_path / "meminfo"

    class V:
        def run(self, *args, free_mb=16384):
            meminfo.write_text(f"MemTotal: 32000000 kB\nMemAvailable: {free_mb * 1024} kB\n")
            return lab.run([SCRIPT, *args], env={"P8_MEMINFO": str(meminfo), "ACPI_TIMEOUT_SECONDS": "6"})

        def mutating(self):
            return [c for c in lab.calls("VBoxManage") if c[1] not in ("showvminfo", "list")
                    and not (c[1] == "snapshot" and c[3] == "list")]
    return V()


def refused(proc, text):
    assert proc.returncode == 1 and "LAB_VM REFUSED" in proc.stderr and text in proc.stderr, proc.stderr
    return True


# ---- clone
def test_clone_from_a_powered_off_source_leaves_the_source_unchanged(vms, lab):
    proc = vms.run("clone", "RHEL9", "p8lab-rhel9b")
    assert proc.returncode == 0 and "source unchanged" in proc.stdout, proc.stderr
    assert "p8lab-rhel9b" in lab.state()["vms"] and lab.state()["vms"]["RHEL9"]["state"] == "poweroff"
    assert [c[1] for c in vms.mutating()] == ["clonevm"]


def test_clone_from_a_named_snapshot_of_a_running_source(vms, lab):
    proc = vms.run("clone", "kubuntu-desktop", "p8lab-kubuntu", "--snapshot", "fresh")
    assert proc.returncode == 0, proc.stderr
    clone = vms.mutating()[0]
    assert clone[1:3] == ["clonevm", "kubuntu-desktop"] and "--snapshot" in clone and "fresh" in clone


@pytest.mark.parametrize("args, text", [
    (("clone", "RHEL9", "rhel9-copy"), "the clone must be named p8lab-*"),
    (("clone", MASTER, "p8lab-master"), "the master is never a clone source"),
    (("clone", "nope", "p8lab-x"), "no source VM named 'nope'"),
    (("clone", "RHEL9", "p8lab-rhel9"), "already exists"),
    (("clone", "kubuntu-desktop", "p8lab-k"), "clone a powered-off source or one of its snapshots"),
    (("clone", "RHEL9", "p8lab-x", "--snapshot", "missing"), "has no snapshot 'missing'"),
])
def test_clone_refusals_change_nothing(vms, args, text):
    assert refused(vms.run(*args), text)
    assert vms.mutating() == []


# ---- every verb is p8lab-* only
@pytest.mark.parametrize("args", [
    ("modify", NODE, "--memory", "4096"), ("modify", MASTER, "--memory", "4096"), ("start", "RHEL9"),
    ("stop", NODE), ("stop", MASTER, "--hard"), ("snapshot", NODE, "take", "X"), ("snapshot", MASTER, "restore", "X"),
    ("modify", "kubuntu-desktop", "--cpus", "2"),
])
def test_non_lab_vms_are_refused_for_every_verb(vms, args):
    assert refused(vms.run(*args), "acts on p8lab-* VMs only")
    assert vms.mutating() == []


def test_modify_only_powered_off_and_names_stay_p8lab(vms):
    assert refused(vms.run("modify", "p8lab-busy", "--memory", "4096"), "modify a powered-off VM only")
    assert refused(vms.run("modify", "p8lab-rhel9", "--name", "rhel"), "--name must stay p8lab-*")
    assert vms.mutating() == []
    assert vms.run("modify", "p8lab-rhel9", "--nic1", "nat").returncode == 0
    assert vms.mutating()[0][1:3] == ["modifyvm", "p8lab-rhel9"]


def test_start_keeps_four_gigabytes_free(vms):
    assert refused(vms.run("start", "p8lab-rhel9", free_mb=8000), "would leave 3904 MB free")  # 8000 - 4096
    assert vms.mutating() == []
    proc = vms.run("start", "p8lab-rhel9", free_mb=8192)
    assert proc.returncode == 0 and "4096 MB left free" in proc.stdout
    assert vms.mutating()[0][1:3] == ["startvm", "p8lab-rhel9"]


def test_stop_acpi_then_hard(vms, lab):
    lab.world["acpi_works"] = False
    assert refused(vms.run("stop", "p8lab-busy"), "did not power off within")
    proc = vms.run("stop", "p8lab-busy", "--hard")
    assert proc.returncode == 0 and lab.state()["vms"]["p8lab-busy"]["state"] == "poweroff"


def test_snapshots_offline_only_and_no_delete(vms, lab):
    assert refused(vms.run("snapshot", "p8lab-busy", "take", "S1"), "offline only")
    assert refused(vms.run("snapshot", "p8lab-rhel9", "take", "P8LAB_BASE"), "already has a snapshot")
    assert refused(vms.run("snapshot", "p8lab-rhel9", "restore", "nope"), "has no snapshot 'nope'")
    assert refused(vms.run("snapshot", "p8lab-rhel9", "delete", "P8LAB_BASE"), "deleting a snapshot stays Salatiel's")
    assert refused(vms.run("snapshot", "p8lab-rhel9", "take", "bad name;rm"), "must match")
    assert vms.mutating() == []
    assert vms.run("snapshot", "p8lab-rhel9", "take", "P8LAB_BASE_v2", "--description", "d").returncode == 0
    assert vms.run("snapshot", "p8lab-rhel9", "restore", "P8LAB_BASE").returncode == 0


def test_there_is_no_delete(vms):
    for verb in ("delete", "unregistervm"):
        assert refused(vms.run(verb, "p8lab-rhel9"), "deleting a VM stays Salatiel's")
    assert vms.mutating() == []


def test_settings_allow_the_script_and_deny_raw_mutating_vboxmanage():
    settings = json.loads((TOOLS.parents[1] / ".claude" / "settings.json").read_text())["permissions"]
    assert "Bash(.codex_state/tools/lab_vm.sh *)" in settings["allow"]
    for verb in ("clonevm *", "createvm *", "startvm *", "controlvm *", "modifyvm *", "unregistervm *",
                 "snapshot * take*", "snapshot * restore*", "snapshot * delete*"):
        assert f"Bash(VBoxManage {verb})" in settings["deny"], verb
    assert not any(a.startswith("Bash(VBoxManage") and a.split()[1] not in ("list", "showvminfo", "snapshot")
                   for a in settings["allow"])
