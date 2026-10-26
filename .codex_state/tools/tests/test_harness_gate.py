"""Gate v2 (step 1.1): run 2 must exit 0, exec/removed events fail, agent runs time out."""

from conftest import TOOLS

SCRIPT = str(TOOLS / "test_class.sh")
AGENT = r"puppet8node sudo /opt/puppetlabs/bin/puppet agent -t"
EXEC_EVENT = "Notice: /Stage[main]/Main/Node[puppet8node]/Exec[p8test unguarded exec]/returns: executed successfully\n"
APPLIED = "Notice: Applied catalog in 1.02 seconds\n"


def agent_runs(lab, *runs):
    lab.world["ssh"].insert(0, {"match": AGENT, "outputs": list(runs)})


def harness(lab, **env):
    return lab.run([SCRIPT, "--fixture", "unguarded_exec"], env={k: str(v) for k, v in env.items()})


def test_unguarded_exec_is_red(lab):
    agent_runs(lab, {"rc": 2, "stdout": EXEC_EVENT + APPLIED}, {"rc": 2, "stdout": EXEC_EVENT + APPLIED})
    proc = harness(lab)
    assert proc.returncode == 1
    assert "not idempotent" in proc.stderr and "executed successfully" in proc.stderr
    assert "GREEN" not in proc.stdout


def test_run2_exit_2_without_matching_text_is_red(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 2, "stdout": "Warning: something\n" + APPLIED})
    proc = harness(lab)
    assert proc.returncode == 1
    assert "Run 2 exited 2" in proc.stderr


def test_removed_on_run2_is_red_even_with_exit_0(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED},
               {"rc": 0, "stdout": "Notice: /Firewall[999 drop]/ensure: removed\n" + APPLIED})
    assert harness(lab).returncode == 1


def test_clean_run2_is_green(lab):
    agent_runs(lab, {"rc": 2, "stdout": EXEC_EVENT + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = harness(lab)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip().endswith("GREEN: run 2 exited 0 with no change events (gate v2).")


def test_run1_failure_is_reported_with_exit_code(lab):
    agent_runs(lab, {"rc": 4, "stdout": "Error: boom\n"})
    proc = harness(lab)
    assert proc.returncode == 1
    assert "Agent run 1 failed (exit 4)" in proc.stderr


def test_hung_agent_run_times_out(lab):
    agent_runs(lab, {"rc": 0, "sleep": 5, "stdout": APPLIED})
    proc = harness(lab, AGENT_TIMEOUT_SECONDS=1)
    assert proc.returncode == 1
    assert "Agent run 1 timed out after 1s" in proc.stderr


def test_exactly_two_agent_runs(lab):
    agent_runs(lab, {"rc": 2, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED})
    assert harness(lab).returncode == 0
    agent_calls = [c for c in lab.calls("ssh") if "agent -t" in " ".join(c)]
    assert len(agent_calls) == 2


def test_fixture_name_is_validated(lab):
    proc = lab.run([SCRIPT, "--fixture", "../etc/passwd"])
    assert proc.returncode == 1 and "Invalid fixture name" in proc.stderr
