"""lab_idle_down.sh (HQ 2026-11-22 ruling 3): when the advisor's turn ends, the lab goes down once it has been idle (no
lock holder, no lab tool process) for the idle time; a new turn disarms it."""

import datetime as dt
import subprocess
import threading
import time

import pytest

from conftest import TOOLS

IDLE = str(TOOLS / "lab_idle_down.sh")
NODE, MASTER = "ubuntu24-puppet8-Node", "Ubuntu24-puppet8-Master"
TOKEN = "p8test-idle-lab-proc-token"


def env(lab, idle_s="1"):
    return {"P8_IDLE_DIR": str(lab.root / "idle"), "P8_IDLE_POLL": "0.2", "P8_IDLE_DOWN_S": idle_s,
            "P8_IDLE_LOG": str(lab.root / "idle.log"), "P8_LAB_PROC_PATTERN": TOKEN}


def wait_until(predicate, seconds=10.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(0.1)
    return predicate()


def vm_states(lab):
    return {vm: lab.state()["vms"][vm]["state"] for vm in (MASTER, NODE)}


def run(lab, argv, e):
    """lab.run after reloading the world: FakeLab.run saves its in-memory world first, which would otherwise undo VM
    state changes the watcher's lab_power.sh down made meanwhile (and leave down waiting on a master turned back on)."""
    lab.world = lab.state()
    return lab.run(argv, env=e)


def status(lab, e):
    return run(lab, [IDLE, "status"], e).stdout.strip()


@pytest.fixture
def disarmed_at_the_end(lab):
    yield
    e = env(lab)
    run(lab, [IDLE, "disarm"], e)
    assert wait_until(lambda: not (lab.root / "idle" / "idle_down.pid").exists(), seconds=30)


def test_an_idle_lab_goes_down_after_the_turn_ends(lab, disarmed_at_the_end):
    e = env(lab)
    assert lab.run([IDLE, "arm"], env=e).returncode == 0
    assert status(lab, e).startswith("armed ")
    assert wait_until(lambda: vm_states(lab) == {MASTER: "poweroff", NODE: "poweroff"}, seconds=20)
    assert wait_until(lambda: "LAB DOWN" in (lab.root / "idle.log").read_text(), seconds=20)
    assert "turn ended and the lab idle for 1s" in (lab.root / "idle.log").read_text()
    assert wait_until(lambda: status(lab, e) == "disarmed")


def test_a_lock_holder_keeps_the_lab_up(lab, disarmed_at_the_end):
    holder = subprocess.Popen(["bash", "-c", "while :; do command -p sleep 0.1; done"])
    threading.Thread(target=holder.wait, daemon=True).start()
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (lab.root / "lab.lock").write_text(f"{holder.pid} {now} phase3.py run p8test reviewer\n")
    try:
        e = env(lab)
        assert lab.run([IDLE, "arm"], env=e).returncode == 0
        time.sleep(2.5)  # more than twice the idle time
        assert vm_states(lab) == {MASTER: "running", NODE: "running"}
    finally:
        holder.kill()
    (lab.root / "lab.lock").unlink()
    assert wait_until(lambda: vm_states(lab) == {MASTER: "poweroff", NODE: "poweroff"}, seconds=20), \
        "once the run releases the lab and it stays idle, it goes down"


def test_a_lab_tool_process_keeps_the_lab_up(lab, disarmed_at_the_end):
    lab.world["busy"] = "4242 phase3.py run p8test"  # the fake pgrep reports a lab process while this is set
    e = env(lab)
    assert lab.run([IDLE, "arm"], env=e).returncode == 0
    time.sleep(2.5)
    assert vm_states(lab) == {MASTER: "running", NODE: "running"}
    lab.world = lab.state()
    lab.world["busy"] = ""
    lab.save()
    assert wait_until(lambda: vm_states(lab) == {MASTER: "poweroff", NODE: "poweroff"}, seconds=20)


def test_a_new_turn_disarms_before_the_idle_time(lab, disarmed_at_the_end):
    e = env(lab, idle_s="30")
    assert lab.run([IDLE, "arm"], env=e).returncode == 0
    assert lab.run([IDLE, "disarm"], env=e).returncode == 0
    assert wait_until(lambda: not (lab.root / "idle" / "idle_down.pid").exists())
    assert status(lab, e) == "disarmed"
    assert vm_states(lab) == {MASTER: "running", NODE: "running"}
    assert "disarmed: a new turn started" in (lab.root / "idle.log").read_text()


def test_nothing_runs_when_no_lab_vm_runs(lab, disarmed_at_the_end):
    lab.world["vms"][NODE]["state"] = lab.world["vms"][MASTER]["state"] = "poweroff"
    e = env(lab)
    assert lab.run([IDLE, "arm"], env=e).returncode == 0
    assert "no lab VM running: nothing to watch" in (lab.root / "idle.log").read_text()
    assert not (lab.root / "idle" / "idle_down.pid").exists() and status(lab, e) == "disarmed"
    assert not [c for c in lab.calls("VBoxManage") if c[1] == "controlvm"]


def test_arming_twice_starts_one_watcher(lab, disarmed_at_the_end):
    e = env(lab, idle_s="30")
    assert lab.run([IDLE, "arm"], env=e).returncode == 0
    first = (lab.root / "idle" / "idle_down.pid").read_text()
    assert lab.run([IDLE, "arm"], env=e).returncode == 0
    assert (lab.root / "idle" / "idle_down.pid").read_text() == first


def test_usage(lab):
    assert lab.run([IDLE, "bogus"], env=env(lab)).returncode == 2


def test_the_project_hooks_arm_at_turn_end_and_disarm_at_a_prompt():
    import json
    settings = json.loads((TOOLS.parents[1] / ".claude" / "settings.json").read_text())
    cmds = {event: [h["command"] for entry in settings["hooks"][event] for h in entry["hooks"]]
            for event in ("Stop", "UserPromptSubmit")}
    assert any(c.endswith("/.codex_state/tools/lab_idle_down.sh arm") for c in cmds["Stop"])
    assert any(c.endswith("/.codex_state/tools/lab_idle_down.sh disarm") for c in cmds["UserPromptSubmit"])
