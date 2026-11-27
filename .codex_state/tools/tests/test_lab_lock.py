"""lab_lock.sh (2026-11-16, batch 4): one lab run at a time — a concurrent compile-only rewrote the master's node file
in the middle of a reviewer's apply."""

import os
import subprocess

import pytest

from conftest import TOOLS

pytestmark = pytest.mark.slow  # stub-lab harness runs

LOCK = str(TOOLS / "lab_lock.sh")


def lock(lab, *args):
    return lab.run([LOCK, *args])


@pytest.fixture
def held(lab):
    """The lock held by a live process other than the tool under test (a sleeping child)."""
    holder = subprocess.Popen(["sleep", "60"])
    assert lock(lab, "take", str(holder.pid), "reviewer harness").returncode == 0
    yield holder
    holder.kill()


def test_take_holder_release(lab):
    me = str(os.getpid())
    assert lock(lab, "take", me, "test run").returncode == 0
    assert lock(lab, "holder").stdout.startswith(f"{me} ")
    assert lock(lab, "take", me, "again").returncode == 0  # re-entrant for the same owner
    assert lock(lab, "release", me).returncode == 0
    assert lock(lab, "holder").stdout == ""


def test_a_live_holder_refuses_others_and_a_dead_one_is_replaced(lab, held):
    proc = lock(lab, "take", str(os.getpid()), "intruder")
    assert proc.returncode == 1 and f"{held.pid} " in proc.stderr and "reviewer harness" in proc.stderr
    held.kill()
    held.wait()
    assert lock(lab, "take", str(os.getpid()), "after the holder died").returncode == 0


def test_release_by_another_owner_does_nothing(lab, held):
    lock(lab, "release", str(os.getpid()))
    assert lock(lab, "holder").stdout.startswith(f"{held.pid} ")


@pytest.mark.parametrize("argv", [["--compile-only", "infra_populi::dns_client"],
                                  ["--revert-first", "infra_populi::dns_client"]])
def test_the_harness_refuses_while_another_run_holds_the_lock(lab, held, argv):
    proc = lab.run([str(TOOLS / "test_class.sh"), *argv])
    assert proc.returncode == 1 and "another lab run holds the lab lock" in proc.stderr
    assert lab.calls("ssh") == [] and lab.calls("rsync") == [] and lab.calls("VBoxManage") == []


def test_revert_refuses_while_another_run_holds_the_lock(lab, held):
    proc = lab.run([str(TOOLS / "revert_node.sh")])
    assert proc.returncode == 1 and "not reverting the node under it" in proc.stderr
    assert lab.calls("VBoxManage") == []


def test_a_revert_first_harness_holds_one_lock_for_its_revert_and_releases_it(lab):
    lab.world["ssh"].insert(0, {"match": r"agent -t", "outputs": [{"rc": 2, "stdout": ""}, {"rc": 0, "stdout": ""}]})
    proc = lab.run([str(TOOLS / "test_class.sh"), "--revert-first", "--fixture", "guarded_exec"])
    assert "another lab run holds" not in proc.stderr  # the nested revert did not deadlock on its parent's lock
    assert ["VBoxManage", "snapshot", "ubuntu24-puppet8-Node", "restore", "P8NODE_BASELINE_GREEN_v6"] in lab.calls()
    assert lock(lab, "holder").stdout == ""  # released at exit


def test_render_only_needs_no_lock(lab, held):
    proc = lab.run([str(TOOLS / "test_class.sh"), "--render-only", "infra_populi::dns_client"])
    assert "another lab run holds" not in proc.stderr


# 2026-11-19: a powered-off master has no clock to read; the lock let no revert start it until take skipped it.
def test_take_skips_the_clock_of_a_master_that_is_not_running(lab):
    lab.world["vms"]["Ubuntu24-puppet8-Master"]["state"] = "poweroff"
    lab.world["ssh"].insert(0, {"match": r"puppet8master date -u", "rc": 255})
    proc = lock(lab, "take", str(os.getpid()), "revert")
    assert proc.returncode == 0, proc.stderr
    assert "the master VM is poweroff" in proc.stderr
    assert [c for c in lab.calls("VBoxManage") if c[1] != "showvminfo"] == []  # read, never acted on


def test_take_still_checks_a_running_masters_clock(lab):
    lab.world["ssh"].insert(0, {"match": r"puppet8master date -u", "clock": 300})
    proc = lock(lab, "take", str(os.getpid()), "revert")
    assert proc.returncode == 1 and "clocks disagree" in proc.stderr


# 2026-11-19: the first VBoxManage call after a crash starts a VBoxSVC that outlives it; one started under the mutex
# inherited its descriptor and held it, and the next release waited forever. Commands under the mutex get it closed.
def test_commands_run_under_the_mutex_do_not_inherit_its_descriptor(lab, tmp_path):
    lab.world["vms"]["Ubuntu24-puppet8-Master"]["state"] = "poweroff"
    lab.world["ssh"].insert(0, {"match": r"puppet8master date -u", "rc": 255})
    shim, log = tmp_path / "shim", tmp_path / "fd.log"
    shim.mkdir()
    vbox = shim / "VBoxManage"
    vbox.write_text(f'#!/bin/sh\n[ -e /proc/$$/fd/8 ] && echo fd8-open >> {log} || echo fd8-closed >> {log}\n'
                    f'exec "{lab.bin / "VBoxManage"}" "$@"\n')
    vbox.chmod(0o755)
    proc = lab.run([LOCK, "take", str(os.getpid()), "revert"], env={"PATH": f"{shim}:{lab.bin}:{os.environ['PATH']}"})
    assert proc.returncode == 0, proc.stderr
    assert log.read_text() == "fd8-closed\n"
