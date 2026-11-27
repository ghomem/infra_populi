"""Lab clocks agree with the laptop's (HQ 2026-11-17 batch-8 ruling 4): a laptop suspend left the master 2 h 26 min
behind; the lab lock refuses a run while the master is off, and the revert and the harness while the node is."""

import pytest

from conftest import TOOLS

CHECK = str(TOOLS / "clock_check.py")
LOCK = str(TOOLS / "lab_lock.sh")


def skewed(lab, host_re, seconds):
    lab.world["ssh"].insert(0, {"match": host_re + r".*date -u \+%s\.%N", "clock": seconds})


def test_a_clock_within_the_limit_passes_and_prints_the_skew(lab):
    skewed(lab, "puppet8master", 1.0)
    proc = lab.run([CHECK, "puppet8master"])
    assert proc.returncode == 0 and proc.stdout.startswith("CLOCK puppet8master +")


@pytest.mark.parametrize("seconds", [-8760.0, 30.0, -6.5])
def test_a_clock_beyond_the_limit_is_refused_in_either_direction(lab, seconds):
    skewed(lab, "puppet8master", seconds)
    proc = lab.run([CHECK, "puppet8master"])
    assert proc.returncode == 1 and "CLOCK_SKEW puppet8master" in proc.stderr and "limit 5s" in proc.stderr


def test_the_limit_is_configurable(lab):
    skewed(lab, "puppet8master", 3.0)
    assert lab.run([CHECK, "--max-skew", "1", "puppet8master"]).returncode == 1
    assert lab.run([CHECK, "puppet8master"], env={"P8_CLOCK_MAX_SKEW": "1"}).returncode == 1
    assert lab.run([CHECK, "puppet8master"]).returncode == 0


@pytest.mark.parametrize("rule", [{"rc": 255, "stdout": ""}, {"rc": 0, "stdout": "Tue Nov 17\n"}])
def test_an_unreadable_clock_is_refused(lab, rule):
    lab.world["ssh"].insert(0, {"match": r"date -u", **rule})
    proc = lab.run([CHECK, "puppet8master"])
    assert proc.returncode == 1 and "CLOCK_UNREADABLE puppet8master" in proc.stderr


def test_every_host_is_checked(lab):
    skewed(lab, "p8lab-gnome", -100.0)
    proc = lab.run([CHECK, "puppet8master", "p8lab-gnome"])
    assert proc.returncode == 1 and "CLOCK puppet8master" in proc.stdout and "CLOCK_SKEW p8lab-gnome" in proc.stderr


@pytest.mark.slow
def test_the_lab_lock_refuses_while_the_master_is_off_and_takes_nothing(lab):
    skewed(lab, "puppet8master", -8760.0)
    proc = lab.run([LOCK, "take", "4242", "a run"])
    assert proc.returncode == 1 and "CLOCK_SKEW puppet8master" in proc.stderr and "not taking the lab lock" in proc.stderr
    assert lab.run([LOCK, "holder"]).stdout == ""
    assert not (lab.root / "lab.lock").exists()
    assert lab.calls("ssh", clock=True) == [["ssh", "puppet8master", "date -u +%s.%N"]]


@pytest.mark.slow
def test_a_harness_refuses_before_touching_the_master_while_its_clock_is_off(lab):
    skewed(lab, "puppet8master", 600.0)
    proc = lab.run([str(TOOLS / "test_class.sh"), "--compile-only", "infra_populi::dns_client"])
    assert proc.returncode == 1 and "CLOCK_SKEW puppet8master" in proc.stderr
    # the master is not touched: at most its state is read (lab_lock.sh, 2026-11-19: a stopped master has no clock)
    assert lab.calls("rsync") == [] and [c for c in lab.calls("VBoxManage") if c[1] != "showvminfo"] == []


@pytest.mark.slow
def test_a_revert_fails_when_the_restored_node_is_off(lab):
    skewed(lab, "puppet8node", -120.0)
    proc = lab.run([str(TOOLS / "revert_node.sh")])
    assert proc.returncode == 1 and "CLOCK_SKEW puppet8node" in proc.stderr and "clock is off" in proc.stderr
    assert "SUCCESS" not in proc.stdout


@pytest.mark.slow
def test_a_harness_without_a_revert_refuses_to_run_the_agent_on_a_node_that_is_off(lab):
    skewed(lab, "puppet8node", 45.0)
    proc = lab.run([str(TOOLS / "test_class.sh"), "--fixture", "guarded_exec"])
    assert proc.returncode == 1 and "CLOCK_SKEW puppet8node" in proc.stderr
    assert not [c for c in lab.calls("ssh") if "agent -t" in " ".join(c)]
