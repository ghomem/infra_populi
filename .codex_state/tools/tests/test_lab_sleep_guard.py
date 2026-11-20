"""lab_sleep_guard.sh (2026-11-19): sleep is blocked for as long as any lab VM runs, and released when the last one
stops (a laptop suspend between runs left both VMs in Guru Meditation on resume)."""

import json
import time

import pytest

from conftest import TOOLS

GUARD = str(TOOLS / "lab_sleep_guard.sh")
NODE, MASTER = "ubuntu24-puppet8-Node", "Ubuntu24-puppet8-Master"


def set_states(lab, **states):
    """Change VM states in the fake world. Every lab.run() writes lab.world first, so the in-memory world is changed
    (from the file, which the stubs may have updated) and saved."""
    lab.world = json.loads(lab.world_path.read_text())
    for vm, state in states.items():
        lab.world["vms"][vm]["state"] = state
    lab.save()


def wait_until(predicate, seconds=5.0):
    end = time.time() + seconds
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.1)
    return False


ON = {"P8_NO_SLEEP_GUARD": ""}  # the stub lab's default opts out of guards; these tests opt back in


def status(lab):
    return lab.run([GUARD, "status"], env=ON).stdout.strip()


@pytest.fixture
def stopped_at_the_end(lab):
    yield
    set_states(lab, **{NODE: "poweroff", MASTER: "poweroff"})
    assert wait_until(lambda: status(lab) == "none")


def test_hold_exits_and_clears_its_pid_when_no_lab_vm_runs(lab):
    lab.world["vms"][NODE]["state"] = lab.world["vms"][MASTER]["state"] = "poweroff"
    proc = lab.run([GUARD, "hold"], env=ON)
    assert proc.returncode == 0
    assert not (lab.root / "sleep_guard.pid").exists()


def test_ensure_holds_sleep_while_a_lab_vm_runs_and_releases_when_the_last_stops(lab, stopped_at_the_end):
    lab.world["vms"][MASTER]["state"] = "poweroff"  # the node alone runs
    assert lab.run([GUARD, "ensure"], env=ON).returncode == 0
    assert status(lab).startswith("held ")
    log = (lab.root / "inhibit.log").read_text()
    assert "--what=sleep" in log and "--mode=block" in log and log.rstrip().endswith("hold")
    set_states(lab, **{NODE: "poweroff"})
    assert wait_until(lambda: status(lab) == "none"), "the guard did not release when the last lab VM stopped"


def test_ensure_starts_no_second_guard(lab, stopped_at_the_end):
    assert lab.run([GUARD, "ensure"], env=ON).returncode == 0
    first = status(lab)
    assert lab.run([GUARD, "ensure"], env=ON).returncode == 0
    assert status(lab) == first
    assert (lab.root / "inhibit.log").read_text().count("--what=sleep") == 1


def test_a_revert_starts_the_guard(lab, stopped_at_the_end):
    proc = lab.run([str(TOOLS / "revert_node.sh")], env=ON)
    assert proc.returncode == 0, proc.stderr
    assert status(lab).startswith("held ")


def test_the_stub_lab_default_starts_no_guard(lab):
    assert lab.run([GUARD, "ensure"]).returncode == 0  # P8_NO_SLEEP_GUARD from the stub lab's defaults
    assert status(lab) == "none" and not (lab.root / "inhibit.log").exists()



# HQ 2026-11-20 travel addition 2: on battery below 25 % with lab VMs running, the guard brings the lab down.
def power_supply(lab, status, capacity):
    root = lab.root / "power_supply"
    for name, files in {"ADP1": {"type": "Mains", "online": "0" if status == "Discharging" else "1"},
                        "BAT0": {"type": "Battery", "status": status, "capacity": str(capacity)}}.items():
        (root / name).mkdir(parents=True, exist_ok=True)
        for key, value in files.items():
            (root / name / key).write_text(value + "\n")
    return {**ON, "P8_POWER_SUPPLY": str(root), "P8_BATTERY_LOG": str(lab.root / "battery.log"),
            "P8_LAB_POWER_POLL": "0.1", "ACPI_TIMEOUT_SECONDS": "5"}


def vm_states(lab):
    return {vm: lab.state()["vms"][vm]["state"] for vm in (MASTER, NODE)}


def test_on_battery_below_the_minimum_the_guard_brings_the_lab_down(lab, stopped_at_the_end):
    env = power_supply(lab, "Discharging", 20)
    assert lab.run([GUARD, "ensure"], env=env).returncode == 0
    assert wait_until(lambda: vm_states(lab) == {MASTER: "poweroff", NODE: "poweroff"}, seconds=15)
    assert wait_until(lambda: "LAB DOWN" in (lab.root / "battery.log").read_text(), seconds=10)
    log = (lab.root / "battery.log").read_text()
    assert "on battery at 20% (< 25%) with lab VMs running: lab_power.sh down" in log
    master_calls = [c[1:] for c in lab.calls("VBoxManage") if MASTER in c and c[1] == "controlvm"]
    assert master_calls == [["controlvm", MASTER, "acpipowerbutton"]]
    assert wait_until(lambda: status(lab) == "none")


@pytest.mark.parametrize("state, capacity", [("Not charging", 10), ("Full", 10), ("Discharging", 25),
                                             ("Discharging", 60)])
def test_the_guard_leaves_the_lab_up_on_mains_or_above_the_minimum(lab, stopped_at_the_end, state, capacity):
    env = power_supply(lab, state, capacity)
    assert lab.run([GUARD, "ensure"], env=env).returncode == 0
    time.sleep(1.0)  # five guard polls at 0.2 s
    assert vm_states(lab) == {MASTER: "running", NODE: "running"}
    assert not (lab.root / "battery.log").exists()
