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

