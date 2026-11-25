"""lab_power.sh (HQ 2026-11-20 item 3): `down` stops a run cleanly, powers the nodes off, shuts the master down through
ACPI only (refusing on timeout), releases the sleep guard; `up` starts the master, waits until it is healthy, reverts
the node."""

import datetime as dt
import json
import subprocess
import threading

import pytest

from conftest import TOOLS

POWER = str(TOOLS / "lab_power.sh")
GUARD = str(TOOLS / "lab_sleep_guard.sh")
NODE, MASTER, RHEL = "ubuntu24-puppet8-Node", "Ubuntu24-puppet8-Master", "p8lab-rhel9"
FAST = {"P8_LAB_POWER_POLL": "0.1", "ACPI_TIMEOUT_SECONDS": "1", "BOOT_TIMEOUT_SECONDS": "1",
        "RUN_STOP_TIMEOUT_SECONDS": "1"}


def power(lab, mode, **env):
    return lab.run([POWER, mode], env={**FAST, **env})


def vbox(lab, vm):
    return [c[1:3] for c in lab.calls("VBoxManage") if vm in c and c[1] in ("controlvm", "startvm", "snapshot")]


@pytest.fixture
def three_running(lab):
    lab.world["vms"][RHEL] = {"state": "running", "snapshot": "P8LAB_RHEL9_BASELINE"}
    return lab


@pytest.fixture
def holder(lab):
    """A live process holding the lab lock, as an engine run does."""
    procs = []

    def start(ignore_term=False):
        trap = 'trap "" TERM; ' if ignore_term else ""
        proc = subprocess.Popen(["bash", "-c", f"{trap}while :; do command -p sleep 0.1; done"])
        procs.append(proc)
        if not ignore_term:  # reaped at once, as a real run's parent would (no zombie for kill -0 to see)
            threading.Thread(target=proc.wait, daemon=True).start()
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (lab.root / "lab.lock").write_text(f"{proc.pid} {now} phase3.py run test\n")
        return proc
    yield start
    for proc in procs:
        proc.kill()
        proc.wait()


def test_down_powers_the_nodes_off_and_the_master_through_acpi_only(three_running):
    lab = three_running
    proc = power(lab, "down")
    assert proc.returncode == 0, proc.stderr
    assert "LAB DOWN: master poweroff (ACPI); 2 other VM(s) powered off" in proc.stdout
    vms = lab.state()["vms"]
    assert {vm: vms[vm]["state"] for vm in (MASTER, NODE, RHEL)} == dict.fromkeys((MASTER, NODE, RHEL), "poweroff")
    assert [c[1:] for c in lab.calls("VBoxManage") if MASTER in c and c[1] == "controlvm"] == \
        [["controlvm", MASTER, "acpipowerbutton"]]
    assert ["controlvm", NODE] in vbox(lab, NODE) and ["controlvm", RHEL] in vbox(lab, RHEL)
    assert not (lab.root / "lab.lock").exists()


def test_down_never_forces_a_master_that_ignores_acpi(three_running):
    lab = three_running
    lab.world["acpi_works"] = False
    proc = power(lab, "down")
    assert proc.returncode == 1
    assert "did not power off within 1s after ACPI; NOT forcing it" in proc.stderr
    assert lab.state()["vms"][MASTER]["state"] == "running"
    assert not [c for c in lab.calls("VBoxManage") if MASTER in c and c[1:3] == ["controlvm", MASTER]
                and c[3] == "poweroff"]
    assert not (lab.root / "lab.lock").exists()


def test_down_releases_the_sleep_guard(lab):
    on = {"P8_NO_SLEEP_GUARD": ""}
    assert lab.run([GUARD, "ensure"], env=on).returncode == 0
    assert lab.run([GUARD, "status"], env=on).stdout.startswith("held ")
    proc = power(lab, "down", **on)
    assert proc.returncode == 0, proc.stderr
    assert lab.run([GUARD, "status"], env=on).stdout.strip() == "none"


def test_down_stops_the_run_holding_the_lab_first(lab, holder):
    run = holder()
    proc = power(lab, "down")
    assert proc.returncode == 0, proc.stderr
    assert f"Stopping the run that holds the lab lock: {run.pid} " in proc.stdout
    assert run.wait(timeout=5) == -15
    assert lab.state()["vms"][MASTER]["state"] == "poweroff"


def test_down_refuses_and_touches_nothing_when_the_run_does_not_stop(lab, holder):
    run = holder(ignore_term=True)
    proc = power(lab, "down")
    assert proc.returncode == 1
    assert f"the run {run.pid} did not stop within 1s; nothing powered off" in proc.stderr
    assert run.poll() is None
    assert not vbox(lab, MASTER) and not vbox(lab, NODE)


def healthy_master(lab):
    lab.world["ssh"][:0] = [{"match": r"systemctl is-active puppetserver; curl", "stdout": "active\nrunning"}]


def test_up_starts_the_master_waits_for_health_and_reverts_the_node(lab):
    for vm in (MASTER, NODE):
        lab.world["vms"][vm]["state"] = "poweroff"
    healthy_master(lab)
    proc = power(lab, "up")
    assert proc.returncode == 0, proc.stderr
    assert "LAB UP: master healthy" in proc.stdout
    assert ["startvm", MASTER] in vbox(lab, MASTER)
    assert ["snapshot", NODE] in vbox(lab, NODE)
    assert lab.state()["vms"][NODE]["snapshot"] == "P8NODE_BASELINE_GREEN_v5"
    assert not (lab.root / "lab.lock").exists()


def test_up_refuses_a_master_off_the_lab_paravirt_provider(lab):
    # HQ 2026-11-24: the master's provider is Salatiel's to set; lab up only refuses, starting and reverting nothing
    lab.world["vms"][MASTER].update(state="poweroff", config={"effparavirtprovider": "kvm"})
    proc = power(lab, "up")
    assert proc.returncode == 1 and "runs on paravirt provider 'kvm', not the lab's 'hyperv'" in proc.stderr
    assert vbox(lab, MASTER) == [] and vbox(lab, NODE) == []


def test_up_refuses_an_unhealthy_master_and_reverts_nothing(lab):
    lab.world["vms"][MASTER]["state"] = "poweroff"
    lab.world["ssh"][:0] = [{"match": r"systemctl is-active puppetserver; curl", "stdout": "activating\n"}]
    proc = power(lab, "up")
    assert proc.returncode == 1
    assert "not healthy after 1s: 'activating'" in proc.stderr
    assert not vbox(lab, NODE)


def test_up_refuses_while_another_run_holds_the_lab(lab, holder):
    run = holder()
    healthy_master(lab)
    proc = power(lab, "up")
    assert proc.returncode == 1 and "could not take the lab lock" in proc.stderr
    assert run.poll() is None and not vbox(lab, MASTER)
    assert json.dumps(lab.state()["vms"][MASTER]["state"]) == '"running"'


def test_usage(lab):
    proc = power(lab, "sideways")
    assert proc.returncode == 2 and "lab_power.sh down" in proc.stderr
