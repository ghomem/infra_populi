"""lab_exec.sh and hooks/lab_ssh_guard.py (HQ 2026-11-20, after batch 16, item 3): a command run by hand on a lab
machine goes through the wrapper, which refuses while another run holds the lab lock; the hook refuses direct
ssh/scp/sftp/rsync to a lab host."""

import datetime as dt
import json
import subprocess
import sys
import threading

import pytest

from conftest import TOOLS

EXEC = str(TOOLS / "lab_exec.sh")
GUARD = TOOLS / "hooks" / "lab_ssh_guard.py"


@pytest.fixture
def holder(lab):
    """A live process holding the lab lock, as an engine run does."""
    procs = []

    def start():
        proc = subprocess.Popen(["bash", "-c", "while :; do command -p sleep 0.1; done"])
        procs.append(proc)
        threading.Thread(target=proc.wait, daemon=True).start()
        now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        (lab.root / "lab.lock").write_text(f"{proc.pid} {now} phase3.py run p8test reviewer\n")
        return proc
    yield start
    for proc in procs:
        proc.kill()


def ssh_calls(lab):
    return [c for c in lab.calls("ssh") if "date -u +%s.%N" not in c[-1]]


def test_a_command_runs_holding_the_lock_and_its_status_comes_back(lab):
    lab.world["ssh"][:0] = [{"match": r"puppet8node uptime$", "stdout": "up 3 min\n", "rc": 3}]
    proc = lab.run([EXEC, "puppet8node", "uptime"])
    assert proc.returncode == 3 and proc.stdout == "up 3 min\n"
    assert ssh_calls(lab)[-1] == ["ssh", "-T", "puppet8node", "uptime"]
    assert not (lab.root / "lab.lock").exists(), "the lock is released after the command"


def test_stdin_is_passed_through(lab):
    lab.world["read_stdin"] = True
    lab.world["ssh"][:0] = [{"match": r"sudo bash -s", "stdout": "ok\n"}]
    proc = subprocess.run([EXEC, "p8lab-kubuntu", "sudo bash -s"], input="echo p8test-heredoc\n", text=True,
                          capture_output=True, env=lab_env(lab), timeout=60)
    assert proc.returncode == 0, proc.stderr
    sent = [json.loads(line) for line in (lab.root / "calls.jsonl.stdin").read_text().splitlines()]
    assert sent[-1][2] == "echo p8test-heredoc\n"


def lab_env(lab):
    lab.save()
    import os
    env = dict(os.environ, PATH=f"{lab.bin}:{os.environ['PATH']}", FAKE_WORLD=str(lab.world_path),
               FAKE_CALLS=str(lab.calls_path), P8_LAB_LOCK=str(lab.root / "lab.lock"), P8_NO_SLEEP_GUARD="1")
    return env


def test_refused_while_another_run_holds_the_lab(lab, holder):
    run = holder()
    proc = lab.run([EXEC, "puppet8node", "uptime"])
    assert proc.returncode == 1
    assert proc.stderr.startswith("LAB_EXEC REFUSED:") and f"{run.pid} " in proc.stderr
    assert not ssh_calls(lab), "nothing reached the lab"
    assert (lab.root / "lab.lock").read_text().startswith(f"{run.pid} "), "the holder's lock is untouched"


def test_inside_an_engine_run_it_runs_without_taking_the_lock(lab, holder):
    run = holder()  # the engine run itself holds the lock; its children carry P8_LAB_LOCKED=1
    proc = lab.run([EXEC, "puppet8master", "true"], env={"P8_LAB_LOCKED": "1"})
    assert proc.returncode == 0, proc.stderr
    assert ssh_calls(lab)[-1] == ["ssh", "-T", "puppet8master", "true"]
    assert (lab.root / "lab.lock").read_text().startswith(f"{run.pid} ")


@pytest.mark.parametrize("host", ["github.com", "puppet.example.com", "192.168.56.20"])
def test_only_lab_hosts(lab, host):
    proc = lab.run([EXEC, host, "true"])
    assert proc.returncode == 2 and "is not a lab host" in proc.stderr
    assert not ssh_calls(lab)


def guard(command, tool="Bash"):
    event = {"tool_name": tool, "tool_input": {"command": command}}
    return subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event), text=True, capture_output=True)


@pytest.mark.parametrize("command", [
    "ssh puppet8node uptime",
    "ssh -T puppet8master 'sudo ls' </dev/null 2>/dev/null",
    "cd ~/work/infra_populi && timeout 60 ssh -T p8lab-kubuntu 'sudo bash -s' <<'EOF'\nls\nEOF",
    "scp file puppet8master:/tmp/",
    "rsync -a dir/ puppet8node-rsync:/tmp/x",
    "git status; ssh -o ConnectTimeout=5 192.168.56.10 true",
])
def test_the_hook_refuses_direct_access_to_a_lab_host(command):
    proc = guard(command)
    assert proc.returncode == 2
    assert "LAB ACCESS REFUSED" in proc.stderr and "lab_exec.sh" in proc.stderr


@pytest.mark.parametrize("command", [
    ".codex_state/tools/lab_exec.sh puppet8node uptime",
    ".codex_state/tools/lab_exec.sh p8lab-kubuntu 'sudo bash -s' </dev/null <<'EOF'\nls\nEOF",
    ".codex_state/tools/revert_node.sh --node kubuntu",
    "python3 .codex_state/tools/phase3.py run puppet_backup",
    "git push -q origin main",
    "ssh -T git@github.com",
    "grep -n puppet8node .codex_state/lab/nodes.yml",
])
def test_the_hook_lets_other_commands_through(command):
    assert guard(command).returncode == 0


def test_the_hook_ignores_other_tools_and_bad_input():
    assert guard("ssh puppet8node uptime", tool="Read").returncode == 0
    assert subprocess.run([sys.executable, str(GUARD)], input="not json", text=True).returncode == 0
