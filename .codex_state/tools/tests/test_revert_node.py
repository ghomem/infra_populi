import json

from conftest import PLANNED_KIND, TOOLS, planned_inventory
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
    assert ["VBoxManage", "snapshot", NODE, "restore", "P8NODE_BASELINE_GREEN_v4"] in vbox
    assert vbox.index(["VBoxManage", "controlvm", NODE, "poweroff"]) < \
        vbox.index(["VBoxManage", "snapshot", NODE, "restore", "P8NODE_BASELINE_GREEN_v4"])
    last = proc.stdout.strip().splitlines()[-1]
    assert last.startswith("REVERT_METRICS ")
    metrics = json.loads(last.split(" ", 1)[1])
    assert metrics["snapshot"] == "P8NODE_BASELINE_GREEN_v4"
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
    assert "expected 'P8NODE_BASELINE_GREEN_v4'" in proc.stderr
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
    assert record["snapshot"] == "P8NODE_BASELINE_GREEN_v4" and record["last_run"] == "absent"
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
    assert path < first("ip -br addr") < first("getent hosts") < first("puppet8node hostname") \
        < first("apt-get -q update") < first("/dev/tcp/") < first("random/boot_id")
    assert not any("-wifi" in l or "netplan" in l for l in lines)  # no overlay any more: v3 carries it
    assert master_actions(lab) == [] and "host-only path" in proc.stdout


@pytest.mark.parametrize("rule, message", [
    ({"match": r"SSH_CONNECTION", "stdout": "192.168.77.203 51234 192.168.77.185 22\n"},
     "Path check failed: SSH_CONNECTION '192.168.77.203 51234 192.168.77.185 22'"),
    ({"match": r"ip -br addr", "stdout": "enp0s8           DOWN\n"},
     "does not hold 192.168.56.20/24 on any interface (wrong snapshot?)"),
    ({"match": r"getent hosts", "stdout": "192.168.77.166   puppet8master.example.com\n"},
     "resolves puppet8master.example.com to '192.168.77.166', expected 192.168.56.10"),
])
def test_a_wrong_path_after_the_restore_fails_closed_and_records_no_revert(lab, rule, message):
    lab.world["ssh"].insert(0, rule)
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and message in proc.stderr
    assert not (lab.root / "node_revert.json").exists()  # no state token: the harness will call the node stale


def test_node_inventory_cache_is_keyed_by_the_nodes_baseline_snapshot(monkeypatch):
    import importlib.util
    monkeypatch.delenv("P8_NODE_INVENTORY", raising=False)
    spec = importlib.util.spec_from_file_location("node_inventory_t", TOOLS / "node_inventory.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.cache_path().name == "P8NODE_BASELINE_GREEN_v4.paths.gz"  # the default node, from nodes.yml


# 2026-11-16: no IPv4 default route, or apt fetch failures, fail the revert (it reported SUCCESS on a node with no
# internet: no DHCPv4 lease on NIC1, and apt-get update exits 0 on fetch failures).
def test_no_ipv4_default_route_fails_the_revert_before_apt(lab):
    lab.world["ssh"].insert(0, {"match": r"ip -4 route show default", "stdout": ""})
    proc = lab.run([SCRIPT], env={"ROUTE_TIMEOUT_SECONDS": "0"})
    assert proc.returncode == 1 and "no IPv4 default route" in proc.stderr
    assert not any("apt-get" in " ".join(c) for c in lab.calls("ssh"))
    assert not (lab.root / "node_revert.json").exists()



# lab-network-nat.md step 5: NIC1 is VirtualBox NAT; a bridged NIC1 (home LAN) or a missing NAT address fails the
# revert before apt and records no state token.
@pytest.mark.parametrize("rule, message", [
    ({"match": r"ip -4 route show default", "stdout": "default via 192.168.77.1 dev enp0s3 proto dhcp\n"},
     "expected via 10.0.2.2"),
    ({"match": r"ip -4 -br addr", "stdout": "enp0s3           UP             10.0.2.16/24\n"},
     "interface enp0s3 does not hold 10.0.2.15/24"),
    ({"match": r"ip -4 -br addr",
      "stdout": "enp0s3           UP             10.0.2.15/24\nenp0s9           UP             192.168.77.185/24\n"},
     "holds an address on the home LAN"),
])
def test_nic1_must_be_nat_or_the_revert_fails_before_apt(lab, rule, message):
    lab.world["ssh"].insert(0, rule)
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and message in proc.stderr
    assert not any("apt-get" in " ".join(c) for c in lab.calls("ssh"))
    assert not (lab.root / "node_revert.json").exists()


def test_the_nat_asserts_pass_on_the_default_stub_and_follow_the_route_interface(lab):
    lab.world["ssh"][:0] = [
        {"match": r"ip -4 route show default", "stdout": "default via 10.0.2.2 dev ens3 proto dhcp\n"},
        {"match": r"ip -4 -br addr", "stdout": "ens3             UP             10.0.2.15/24\n"
                                                "enp0s8           UP             192.168.56.20/24\n"},
    ]
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr


# HQ NAT review F: REVERT_METRICS carries the bytes NIC1 received since the restore's boot, read on the default-route
# interface; an unreadable counter is null and never fails the revert.
@pytest.mark.parametrize("stdout, value", [("123456789\n", "123456789"), ("", "null")])
def test_revert_metrics_carry_nic1_bytes_from_the_route_interface(lab, stdout, value):
    lab.world["ssh"].insert(0, {"match": r"statistics/rx_bytes", "stdout": stdout})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    assert f'"nic1_rx_bytes":{value},' in proc.stdout.strip().splitlines()[-1]
    assert any("cat /sys/class/net/enp0s3/statistics/rx_bytes" in " ".join(c) for c in lab.calls("ssh"))

@pytest.mark.parametrize("line", ["W: Failed to fetch http://archive.ubuntu.com/ubuntu/dists/noble/InRelease",
                                  "Err:1 http://archive.ubuntu.com noble InRelease\n  Temporary failure resolving 'archive.ubuntu.com'",
                                  "E: Some index files failed to download."])
def test_apt_fetch_failures_fail_the_revert_even_with_exit_0(lab, line):
    lab.world["ssh"].insert(0, {"match": r"apt-get -q update", "stdout": f"Hit:1 x\n{line}\n", "rc": 0})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and "apt-get update reported fetch failures" in proc.stderr
    assert not (lab.root / "node_revert.json").exists()


# HQ 2026-11-16 item 2: the node comes from the lab inventory (nodes.yml); RedHat nodes are registration-checked.
def rhel_inventory(tmp_path):
    import yaml
    data = yaml.safe_load((TOOLS.parent / "lab" / "nodes.yml").read_text())
    data["nodes"]["rhel9"].update(status="active", baseline_snapshot="P8LAB_RHEL9_BASELINE_v1")
    path = tmp_path / "nodes.yml"
    path.write_text(yaml.safe_dump(data))
    return str(path)


def rhel_lab(lab):
    lab.world["vms"]["p8lab-rhel9"] = {"state": "running", "snapshot": "P8LAB_RHEL9_BASELINE_v1"}
    lab.world["ssh"][:0] = [
        {"match": r"SSH_CONNECTION", "stdout": "192.168.56.1 51234 192.168.56.21 22\n"},
        {"match": r"ip -br addr", "stdout": "enp0s8           UP             192.168.56.21/24\n"},
        {"match": r"p8lab-rhel9 hostname$", "stdout": "p8lab-rhel9\n"},
        {"match": r"repo-override --list", "stdout": "This system does not have any content overrides applied to it.\n"},
    ]


def test_the_node_kind_selects_vm_snapshot_and_alias_and_redhat_checks_registration(lab, tmp_path):
    rhel_lab(lab)
    proc = lab.run([SCRIPT, "--node", "rhel9"], env={"P8_NODES": rhel_inventory(tmp_path)})
    assert proc.returncode == 0, proc.stderr
    assert ["VBoxManage", "snapshot", "p8lab-rhel9", "restore", "P8LAB_RHEL9_BASELINE_v1"] in lab.calls("VBoxManage")
    assert not any(NODE in c for c in lab.calls("VBoxManage"))  # the Ubuntu node is untouched
    ssh = [" ".join(c[1:]) for c in lab.calls("ssh")]
    assert any("p8lab-rhel9 sudo -n subscription-manager identity" in l for l in ssh)
    assert any("dnf -q makecache" in l for l in ssh) and not any("apt-get" in l for l in ssh)
    assert '"node":"rhel9"' in proc.stdout.strip().splitlines()[-1]
    assert json.loads(proc.stdout.strip().splitlines()[-1].split(" ", 1)[1])["apt_mirror"] is None
    assert master_actions(lab) == []


def test_an_unregistered_rhel_node_fails_the_revert(lab, tmp_path):
    rhel_lab(lab)
    lab.world["ssh"].insert(0, {"match": r"subscription-manager identity", "rc": 1, "stdout": ""})
    proc = lab.run([SCRIPT, "--node", "rhel9"], env={"P8_NODES": rhel_inventory(tmp_path)})
    assert proc.returncode == 1 and "is not registered" in proc.stderr
    assert not (lab.root / "node_revert.json").exists()


def test_a_planned_or_unknown_node_acts_on_no_vm(lab, tmp_path):
    for kind in (PLANNED_KIND, "nope"):
        proc = lab.run([SCRIPT, "--node", kind], env={"P8_NODES": planned_inventory(tmp_path)})
        assert proc.returncode == 1 and "No usable node in the lab inventory" in proc.stderr
    assert lab.calls("VBoxManage") == []


# HQ 2026-11-16 item 5: an enabled repository is a content override kept on the subscription server; it survived a
# snapshot restore on p8lab-rhel9, so every RedHat revert clears the overrides and asserts none remain, before dnf.
def test_a_redhat_revert_clears_content_overrides_before_dnf(lab, tmp_path):
    rhel_lab(lab)
    proc = lab.run([SCRIPT, "--node", "rhel9"], env={"P8_NODES": rhel_inventory(tmp_path)})
    assert proc.returncode == 0, proc.stderr
    lines = [" ".join(c[1:]) for c in lab.calls("ssh")]
    first = lambda pat: next(i for i, l in enumerate(lines) if pat in l)  # noqa: E731
    assert first("subscription-manager identity") < first("repo-override --remove-all") \
        < first("repo-override --list") < first("dnf -q makecache")


@pytest.mark.parametrize("rule, message", [
    ({"match": r"repo-override --remove-all", "rc": 1, "stdout": ""}, "Could not clear the content overrides"),
    ({"match": r"repo-override --list", "stdout": "Repository: codeready-builder-for-rhel-9-x86_64-rpms\n  enabled: 1\n"},
     "still has content overrides after clearing: Repository: codeready-builder"),
])
def test_content_overrides_that_cannot_be_cleared_fail_the_revert(lab, tmp_path, rule, message):
    rhel_lab(lab)
    lab.world["ssh"].insert(0, rule)
    proc = lab.run([SCRIPT, "--node", "rhel9"], env={"P8_NODES": rhel_inventory(tmp_path)})
    assert proc.returncode == 1 and message in proc.stderr
    assert not any("dnf" in " ".join(c) for c in lab.calls("ssh"))


def test_power_off_stops_the_node_without_restoring_or_starting_it(lab):
    # 2026-11-17: p8lab-dc, cloned from the node, takes the node's static host-only address on its first boot
    proc = lab.run([SCRIPT, "--power-off"])
    assert proc.returncode == 0 and "POWERED_OFF node ubuntu (ubuntu24-puppet8-Node)" in proc.stdout, proc.stderr
    ops = [c[1:3] for c in lab.calls("VBoxManage") if c[1] in ("controlvm", "snapshot", "startvm")]
    assert ops == [["controlvm", "ubuntu24-puppet8-Node"]]
    assert lab.state()["vms"]["ubuntu24-puppet8-Node"]["state"] == "poweroff"
    assert lab.state()["vms"]["Ubuntu24-puppet8-Master"]["state"] == "running"
    assert not (lab.root / "node_revert.json").exists()  # no revert recorded


def test_power_off_is_refused_while_another_run_holds_the_lock(lab):
    import subprocess
    holder = subprocess.Popen(["sleep", "60"])
    try:
        assert lab.run([str(TOOLS / "lab_lock.sh"), "take", str(holder.pid), "a run"]).returncode == 0
        proc = lab.run([SCRIPT, "--power-off"])
        assert proc.returncode == 1 and lab.calls("VBoxManage") == []
    finally:
        holder.kill()


# HQ batch-14 ruling 7: a fallback mirror only when the primary Ubuntu archive fails, for that run only (a bind mount
# from /run over the sources file, never an edit of the file on disk), recorded in REVERT_METRICS' apt_mirror.
def metrics(proc):
    return json.loads(proc.stdout.strip().splitlines()[-1].split(" ", 1)[1])


def ssh_lines(lab):
    return [" ".join(c[1:]) for c in lab.calls("ssh")]


def test_the_primary_archive_is_used_and_recorded_when_it_works(lab):
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    assert metrics(proc)["apt_mirror"] == "primary"
    assert not any("p8-fallback-mirror" in l for l in ssh_lines(lab))


@pytest.mark.parametrize("first", [{"rc": 100},
                                   {"rc": 0, "stdout": "Err:1 http://ao.archive.ubuntu.com/ubuntu noble InRelease\n"
                                                       "  Could not connect to ao.archive.ubuntu.com:80\n"
                                                       "W: Failed to fetch http://ao.archive.ubuntu.com/ubuntu/dists/noble/InRelease\n"}])
def test_a_failed_primary_archive_falls_back_for_this_run_and_records_it(lab, first):
    lab.world["ssh"].insert(0, {"match": r"apt-get -q update", "outputs": [first, {"rc": 0, "stdout": "Hit:1 x\n"}]})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 0, proc.stderr
    assert metrics(proc)["apt_mirror"] == "fallback http://mirrors.edge.kernel.org/ubuntu/"
    ssh = ssh_lines(lab)
    apt = [i for i, l in enumerate(ssh) if "apt-get -q update" in l]
    switch = [i for i, l in enumerate(ssh) if "p8-fallback-mirror" in l]
    assert len(apt) == 2 and len(switch) == 1 and apt[0] < switch[0] < apt[1]
    # tmpfs copy bind-mounted over the file; the file on disk is never edited in place
    assert "mount --bind /run/p8-fallback-mirror/ubuntu.sources" in ssh[switch[0]]
    assert not any("sed -i" in l for l in ssh)
    assert (lab.root / "node_revert.json").exists()


def test_a_failure_naming_only_another_repository_does_not_fall_back(lab):
    lab.world["ssh"].insert(0, {"match": r"apt-get -q update", "rc": 0,
                                "stdout": "Hit:1 x\nW: Failed to fetch https://apt.voxpupuli.org/dists/noble/InRelease\n"})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and "apt-get update reported fetch failures" in proc.stderr
    assert not any("p8-fallback-mirror" in l for l in ssh_lines(lab))


def test_both_the_primary_and_the_fallback_failing_fails_the_revert_naming_both(lab):
    lab.world["ssh"].insert(0, {"match": r"apt-get -q update", "rc": 100})
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1
    assert "The primary archive failed" in proc.stderr and "so did the fallback mirror" in proc.stderr
    assert not (lab.root / "node_revert.json").exists()


def test_a_fallback_that_cannot_be_switched_fails_the_revert(lab):
    lab.world["ssh"][:0] = [{"match": r"p8-fallback-mirror", "rc": 1},
                            {"match": r"apt-get -q update", "outputs": [{"rc": 100}, {"rc": 0}]}]
    proc = lab.run([SCRIPT])
    assert proc.returncode == 1 and "could not be switched to the fallback mirror" in proc.stderr
    assert sum("apt-get -q update" in l for l in ssh_lines(lab)) == 1

