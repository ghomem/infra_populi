"""Gate v2 (step 1.1): run 2 must exit 0, exec/removed events fail, agent runs time out."""

from conftest import TOOLS

SCRIPT = str(TOOLS / "test_class.sh")
AGENT = r"puppet8node sudo /opt/puppetlabs/bin/puppet agent -t"
EXEC_EVENT = "Notice: /Stage[main]/Main/Node[puppet8node]/Exec[p8test unguarded exec]/returns: executed successfully\n"
PLUGINSYNC = "\x1b[mNotice: /File[/opt/puppetlabs/puppet/cache/lib/facter/apt_updates.rb]/ensure: defined content as '{sha256}f8'\x1b[0m\n"
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


def test_revert_first_restores_before_deploy_and_counts_run1_events(lab):
    agent_runs(lab, {"rc": 2, "stdout": EXEC_EVENT + EXEC_EVENT + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert proc.returncode == 0, proc.stderr
    calls = lab.calls()
    restore = calls.index(["VBoxManage", "snapshot", "ubuntu24-puppet8-Node", "restore", "P8NODE_BASELINE_GREEN_v2"])
    first_rsync = next(i for i, c in enumerate(calls) if c[0] == "rsync")
    assert restore < first_rsync
    assert "RUN1_EVENTS: 2 catalog, 0 pluginsync (rc 2; node reverted first)" in proc.stdout


def test_revert_first_with_no_run1_events_warns(lab):
    agent_runs(lab, {"rc": 0, "stdout": APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert proc.returncode == 0
    assert "applied nothing" in proc.stderr


def test_failed_revert_stops_before_deploy(lab):
    lab.world["vms"]["ubuntu24-puppet8-Node"]["state"] = "restoring"
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert proc.returncode == 1 and "Node revert failed" in proc.stderr
    assert lab.calls("rsync") == []


def test_revert_first_rejects_render_only(lab):
    proc = lab.run([SCRIPT, "--revert-first", "--render-only", "puppet_infrastructure::dns_client"])
    assert proc.returncode == 1


def test_pluginsync_is_not_counted_as_class_events(lab):
    # Real shape from puppet_backup on 2026-10-26: 116 pluginsync lines, 9 catalog events.
    agent_runs(lab, {"rc": 2, "stdout": PLUGINSYNC * 3 + APPLIED}, {"rc": 0, "stdout": APPLIED})
    proc = lab.run([SCRIPT, "--revert-first", "--fixture", "guarded_exec"])
    assert "RUN1_EVENTS: 0 catalog, 3 pluginsync" in proc.stdout
    assert "applied nothing" in proc.stderr
