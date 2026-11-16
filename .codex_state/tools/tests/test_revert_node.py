import json

from conftest import TOOLS
import pytest

pytestmark = pytest.mark.slow  # excluded from the per-commit fast subset (HQ 2026-11-11 ruling 3)

SCRIPT = str(TOOLS / "revert_node.sh")
NODE, MASTER = "ubuntu24-puppet8-Node", "Ubuntu24-puppet8-Master"


def master_actions(lab):
    """Every VBoxManage call that names the master, except state reads."""
    return [c for c in lab.calls("VBoxManage") if MASTER in c and c[1] != "showvminfo"]


def test_running_node_is_hard_powered_off_and_restored_to_v2(lab):
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    vbox = lab.calls("VBoxManage")
    assert ["VBoxManage", "controlvm", NODE, "poweroff"] in vbox
    assert not any("acpipowerbutton" in c for c in vbox)
    assert ["VBoxManage", "snapshot", NODE, "restore", "P8NODE_BASELINE_GREEN_v3"] in vbox
    assert vbox.index(["VBoxManage", "controlvm", NODE, "poweroff"]) < \
        vbox.index(["VBoxManage", "snapshot", NODE, "restore", "P8NODE_BASELINE_GREEN_v3"])
    last = proc.stdout.strip().splitlines()[-1]
    assert last.startswith("REVERT_METRICS ")
    metrics = json.loads(last.split(" ", 1)[1])
    assert metrics["snapshot"] == "P8NODE_BASELINE_GREEN_v3"
    assert {"total_s", "poweroff_s", "restore_s", "boot_to_ssh_s", "apt_update_s"} <= metrics.keys()
    ssh = [" ".join(c) for c in lab.calls("ssh")]
    apt = next(i for i, c in enumerate(ssh) if "apt-get -q update" in c)
    assert apt > next(i for i, c in enumerate(ssh) if c.endswith("puppet8node hostname"))
    assert master_actions(lab) == []


def test_stopped_master_is_only_ever_started(lab):
    lab.world["vms"][MASTER]["state"] = "poweroff"
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    assert master_actions(lab) == [["VBoxManage", "startvm", MASTER, "--type", "headless"]]


def test_powered_off_node_is_not_powered_off_again(lab):
    lab.world["vms"][NODE]["state"] = "poweroff"
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    assert not any(c[1] == "controlvm" for c in lab.calls("VBoxManage"))


def test_unknown_node_state_refuses_to_act(lab):
    lab.world["vms"][NODE]["state"] = "restoring"
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1
    assert "refusing to act" in proc.stderr
    assert not any(c[1] in ("controlvm", "snapshot") for c in lab.calls("VBoxManage"))


def test_restore_to_wrong_snapshot_fails_before_boot(lab):
    lab.world["vms"][NODE]["snapshot"] = "P8NODE_BASELINE_GREEN"
    lab.world["restore_ignores_name"] = True
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1
    assert "expected 'P8NODE_BASELINE_GREEN_v3'" in proc.stderr
    assert ["VBoxManage", "startvm", NODE, "--type", "headless"] not in lab.calls("VBoxManage")


def test_wrong_hostname_fails(lab):
    lab.world["ssh"][1]["stdout"] = "someothernode\n"
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1
    assert "hostname verification failed" in proc.stderr


def test_failed_apt_update_fails_the_revert(lab):
    lab.world["ssh"].insert(0, {"match": r"apt-get -q update", "rc": 100})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1
    assert "apt-get update failed" in proc.stderr


def test_every_revert_marks_the_node_state_token_and_node_state_touches_no_vm(lab):
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    record = json.loads((lab.root / "node_revert.json").read_text())
    assert record["snapshot"] == "P8NODE_BASELINE_GREEN_v3" and record["last_run"] == "absent"
    assert "REVERT_NODE_STATE boot " + record["boot_id"] in proc.stdout
    token_read = next(i for i, c in enumerate(lab.calls()) if c[0] == "ssh" and "random/boot_id" in " ".join(c))
    assert token_read > max(i for i, c in enumerate(lab.calls()) if c[0] == "ssh" and "/dev/tcp/" in " ".join(c))
    before = len(lab.calls("VBoxManage"))
    state = lab.run([SCRIPT, "--node-state"])
    assert state.returncode == 0 and state.stdout.splitlines()[0] == record["boot_id"]
    assert len(lab.calls("VBoxManage")) == before


def test_unreadable_node_state_token_fails_the_revert(lab):
    lab.world["ssh"].insert(0, {"match": r"random/boot_id", "stdout": ""})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and "state token" in proc.stderr
    assert not (lab.root / "node_revert.json").exists()


# Lab-network plan step 9: v3 carries the host-only config; every revert proves the path after the restore.
def ssh_lines(lab):
    return [" ".join(c[1:]) for c in lab.calls("ssh")]


def test_every_revert_proves_the_host_only_path_before_anything_else(lab):
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    lines = ssh_lines(lab)
    first = lambda pat: next(i for i, l in enumerate(lines) if pat in l)  # noqa: E731
    path = first("SSH_CONNECTION")
    assert "-S none" in lines[path] and "puppet8node echo" in lines[path]
    assert path < first("ip -br addr show enp0s8") < first("getent hosts") < first("puppet8node hostname") \
        < first("apt-get -q update") < first("/dev/tcp/") < first("random/boot_id")
    assert not any("-wifi" in l or "netplan" in l for l in lines)  # no overlay any more: v3 carries it
    assert master_actions(lab) == [] and "host-only path" in proc.stdout


@pytest.mark.parametrize("rule, message", [
    ({"match": r"SSH_CONNECTION", "stdout": "192.168.77.203 51234 192.168.77.185 22\n"},
     "Path check failed: SSH_CONNECTION '192.168.77.203 51234 192.168.77.185 22'"),
    ({"match": r"ip -br addr show enp0s8", "stdout": "enp0s8           DOWN\n"},
     "enp0s8 does not hold 192.168.56.20/24 (wrong snapshot?)"),
    ({"match": r"getent hosts", "stdout": "192.168.77.166   puppet8master.example.com\n"},
     "resolves puppet8master.example.com to '192.168.77.166', expected 192.168.56.10"),
])
def test_a_wrong_path_after_the_restore_fails_closed_and_records_no_revert(lab, rule, message):
    lab.world["ssh"].insert(0, rule)
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and message in proc.stderr
    assert not (lab.root / "node_revert.json").exists()  # no state token: the harness will call the node stale


def test_node_inventory_reads_the_snapshot_name_from_revert_node():
    import importlib.util
    spec = importlib.util.spec_from_file_location("node_inventory_t", TOOLS / "node_inventory.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.SNAPSHOT == "P8NODE_BASELINE_GREEN_v3"
