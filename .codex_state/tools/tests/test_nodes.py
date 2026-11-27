"""nodes.py (HQ 2026-11-16 item 2): the lab node inventory — validation and node selection."""

import copy
import subprocess
import sys

import pytest
import yaml

from conftest import PLANNED_KIND, TOOLS, planned_inventory, with_planned_kind

SCRIPT = str(TOOLS / "nodes.py")
REAL = yaml.safe_load((TOOLS.parent / "lab" / "nodes.yml").read_text())


def run(tmp_path, data, *args, **env):
    path = tmp_path / "nodes.yml"
    path.write_text(yaml.safe_dump(data))
    import os
    e = {k: v for k, v in os.environ.items() if k != "P8_NODE"}
    e.update({"P8_NODES": str(path), **env})
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=e)


def test_the_tracked_inventory_is_valid():
    proc = subprocess.run([sys.executable, SCRIPT, "validate"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert REAL["default"] == "ubuntu" and REAL["nodes"]["ubuntu"]["vm"] == "ubuntu24-puppet8-Node"


def test_the_domain_controller_kind_is_planned_with_its_capability():
    # HQ batch-7 ruling 6: p8lab-dc (Samba AD DC) for openvpn_domain, after the desktops and the second Ubuntu node
    dc = REAL["nodes"]["dc"]
    assert dc["vm"] == "p8lab-dc" and dc["status"] == "active" and "ad-dc" in dc["capabilities"]



def test_the_master_role_kind_is_active_with_its_capability():
    # HQ 2026-11-18 ruling C2: the master-role node that lifts the hashman notes, brought up on 2026-11-18
    kind = REAL["nodes"]["puppetserver"]
    assert kind["status"] == "active" and kind["capabilities"] == ["server", "puppet-server"]
    assert kind["baseline_snapshot"] == "P8LAB_PUPPETSERVER_BASELINE_v2" and kind["hostonly_ip"] == "192.168.56.26"

@pytest.mark.parametrize("caps", [["ad-dc", "domain-controller"], []])
def test_capabilities_outside_the_known_set_are_refused(tmp_path, caps):
    data = copy.deepcopy(REAL)
    data["nodes"]["dc"]["capabilities"] = caps
    proc = run(tmp_path, data, "validate")
    assert proc.returncode != 0 and "capabilities must be a non-empty subset" in proc.stdout + proc.stderr


@pytest.mark.parametrize("mutate, message", [
    (lambda d: d["nodes"]["rhel9"].update(hostonly_ip="192.168.56.20"), "hostonly_ip '192.168.56.20' is also node"),
    (lambda d: d["nodes"]["rhel9"].update(hostonly_ip="192.168.56.10"), "must be a free address on vboxnet0"),
    (lambda d: d["nodes"]["rhel9"].update(hostonly_ip="10.0.2.15"), "must be a free address on vboxnet0"),
    (lambda d: d["nodes"]["rhel9"].update(vm="rhel9-clone"), "must be named p8lab-*"),
    (lambda d: d["nodes"]["rhel9"].update(vm="Ubuntu24-puppet8-Master"), "the master VM is never a node"),
    (lambda d: with_planned_kind(d)["nodes"][PLANNED_KIND].update(status="active"),
     "an active node needs its baseline_snapshot"),
    (lambda d: d["nodes"]["rhel9"].update(os_family="Suse"), "os_family must be Debian|RedHat"),
    (lambda d: d["nodes"]["rhel9"].update(capabilities=["telepathy"]), "capabilities must be a non-empty subset"),
    (lambda d: d["nodes"]["rhel9"].pop("certname"), "missing certname"),
    (lambda d: with_planned_kind(d).update(default=PLANNED_KIND), "the default node must be active"),
    (lambda d: d["nodes"]["gnome"].update(alias="p8lab-kubuntu"), "alias 'p8lab-kubuntu' is also node"),
    (lambda d: d.pop("paravirt_provider"), "paravirt_provider None must name the lab's provider"),
    (lambda d: d.update(paravirt_provider="default"), "paravirt_provider 'default' must name the lab's provider"),
])
def test_invalid_inventories_are_refused(tmp_path, mutate, message):
    data = copy.deepcopy(REAL)
    mutate(data)
    proc = run(tmp_path, data, "validate")
    assert proc.returncode == 2 and message in proc.stderr, proc.stderr


def active(data, kind, snap="P8LAB_X_BASELINE_v1"):
    data["nodes"][kind].update(status="active", baseline_snapshot=snap)
    return data


def test_selection_order_explicit_then_env_then_default(tmp_path):
    data = active(copy.deepcopy(REAL), "rhel9")
    assert run(tmp_path, data, "get", "alias").stdout.strip() == "puppet8node"
    assert run(tmp_path, data, "get", "alias", P8_NODE="rhel9").stdout.strip() == "p8lab-rhel9"
    assert run(tmp_path, data, "get", "--node", "rhel9", "alias").stdout.strip() == "p8lab-rhel9"
    assert run(tmp_path, data, "get", "--node", "nope", "alias").returncode != 0


def test_a_planned_node_is_refused_unless_bring_up_asks(tmp_path):
    data = with_planned_kind(copy.deepcopy(REAL))
    proc = run(tmp_path, data, "env", "--node", PLANNED_KIND)
    assert proc.returncode != 0 and "is planned" in proc.stderr
    proc = run(tmp_path, data, "env", "--node", PLANNED_KIND, "--allow-planned")
    assert proc.returncode == 0 and "NODE_VM=p8lab-future" in proc.stdout and "NODE_SNAPSHOT=''" in proc.stdout


def test_env_is_shell_safe_and_complete(tmp_path):
    proc = run(tmp_path, REAL, "env")
    env = dict(line.split("=", 1) for line in proc.stdout.splitlines())
    assert set(env) == {"NODE_KIND", "NODE_VM", "NODE_ALIAS", "NODE_CERTNAME", "NODE_HOSTNAME", "NODE_HOSTONLY_IP",
                        "NODE_SNAPSHOT", "NODE_OS_FAMILY", "NODE_PARAVIRT"}
    out = subprocess.run(["bash", "-c", proc.stdout + 'echo "$NODE_VM|$NODE_SNAPSHOT|$NODE_OS_FAMILY"'],
                         capture_output=True, text=True).stdout
    assert out.strip() == "ubuntu24-puppet8-Node|P8NODE_BASELINE_GREEN_v5|Debian"


def test_the_lab_paravirt_provider_is_hyperv(tmp_path):
    # HQ 2026-11-24: hyperv is the lab's paravirtualization provider; the shell tools read it from here
    assert REAL["paravirt_provider"] == "hyperv"
    assert run(tmp_path, REAL, "provider").stdout == "hyperv\n"
    assert "NODE_PARAVIRT=hyperv" in run(tmp_path, REAL, "env").stdout.splitlines()


def test_an_invalid_inventory_stops_every_command_but_validate(tmp_path):
    data = copy.deepcopy(REAL)
    data["nodes"]["rhel9"]["vm"] = "Ubuntu24-puppet8-Master"
    proc = run(tmp_path, data, "env")
    assert proc.returncode != 0 and "nodes.yml is invalid" in proc.stderr


def test_services_are_listed_and_validated(tmp_path):
    # HQ review of the behaviour suite (2026-11-27) ruling 6: the lab's apt cache, never a class's node
    import subprocess
    import sys
    import yaml
    real = yaml.safe_load((TOOLS.parent / "lab" / "nodes.yml").read_text())
    p = subprocess.run([sys.executable, str(TOOLS / "nodes.py"), "service", "apt_cache"], capture_output=True, text=True)
    assert p.stdout.split() == [real["services"]["apt_cache"]["hostonly_ip"], "3142"]
    for bad, why in [({"vm": "cache"}, "is not a p8lab-* VM"), ({"hostonly_ip": "192.168.56.20"}, "is a node's"),
                     ({"extra": 1}, "takes vm, alias, hostname, hostonly_ip and port")]:
        data = yaml.safe_load(yaml.safe_dump(real))
        data["services"]["apt_cache"].update(bad)
        path = tmp_path / "nodes.yml"
        path.write_text(yaml.safe_dump(data))
        v = subprocess.run([sys.executable, str(TOOLS / "nodes.py"), "validate"], capture_output=True, text=True,
                           env={**__import__("os").environ, "P8_NODES": str(path)})
        assert v.returncode == 2 and why in v.stderr, v.stderr
