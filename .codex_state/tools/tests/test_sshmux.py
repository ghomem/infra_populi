"""SSH ControlMaster for the harness, the reviewer (via the harness) and revert_node.sh (HQ 2026-11-10 ruling 2)."""

import subprocess

from conftest import TOOLS

CM = "ControlMaster=auto"
NODE = "ubuntu24-puppet8-Node"


def test_harness_ssh_calls_are_multiplexed(lab):
    lab.world["ssh"].insert(0, {"match": r"agent -t", "outputs": [{"rc": 2, "stdout": ""}, {"rc": 0, "stdout": ""}]})
    proc = lab.run([str(TOOLS / "test_class.sh"), "--fixture", "guarded_exec"])
    assert proc.returncode == 0, proc.stderr
    calls = lab.calls("ssh")
    assert calls and all(CM in " ".join(c) for c in calls)
    assert all(f"ControlPath={lab.root}/ssh-cm/%C" in " ".join(c) for c in calls)
    assert (lab.root / "ssh-cm").is_dir()


def test_revert_closes_the_node_master_before_the_hard_poweroff(lab):
    proc = lab.run([str(TOOLS / "revert_node.sh")])
    assert proc.returncode == 0, proc.stderr
    calls = lab.calls()
    exit_i = next(i for i, c in enumerate(calls) if c[0] == "ssh" and "-O" in c and "exit" in c and "puppet8node" in c)
    off_i = calls.index(["VBoxManage", "controlvm", NODE, "poweroff"])
    assert exit_i < off_i
    assert all(CM in " ".join(c) for c in lab.calls("ssh"))


def test_shim_skips_itself_and_fails_cleanly_without_ssh(tmp_path):
    shim = str(TOOLS / "sshmux" / "ssh")
    env = {"PATH": f"{TOOLS / 'sshmux'}:/usr/bin:/bin", "P8_SSH_CONTROL_DIR": str(tmp_path / "cm"), "HOME": str(tmp_path)}
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "ssh").write_text("#!/bin/sh\necho \"REAL $*\"\n")
    (fake / "ssh").chmod(0o755)
    out = subprocess.run([shim, "host", "true"], env={**env, "PATH": f"{TOOLS / 'sshmux'}:{fake}:/usr/bin:/bin"},
                         capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.startswith("REAL -o ControlMaster=auto") and out.stdout.rstrip().endswith("host true")
    import shutil
    tools = tmp_path / "tools"  # everything the shim needs except an ssh
    tools.mkdir()
    for name in ("bash", "env", "readlink", "dirname", "mkdir", "chmod"):
        (tools / name).symlink_to(shutil.which(name))
    none = subprocess.run([shim, "host"], env={**env, "PATH": f"{TOOLS / 'sshmux'}:{tools}"}, capture_output=True, text=True)
    assert none.returncode == 255 and "no ssh binary" in none.stderr
