"""Shared fixture: a fake lab (stub VBoxManage/ssh/scp/rsync/sleep) for testing the shell tools.

The stubs read and update one JSON "world" file and append every invocation to calls.jsonl, so a
test can both script the lab's answers and assert on exactly what a tool asked the lab to do.
No test ever touches a real VM, the master or the node.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]

STUB = r'''#!/usr/bin/env python3
import json, os, re, sys
sys.dont_write_bytecode = True
name = os.path.basename(sys.argv[0])
world_path = os.environ["FAKE_WORLD"]
with open(world_path) as f:
    world = json.load(f)
with open(os.environ["FAKE_CALLS"], "a") as f:
    f.write(json.dumps([name] + sys.argv[1:]) + "\n")
args = sys.argv[1:]

def save():
    with open(world_path, "w") as f:
        json.dump(world, f)

if name == "VBoxManage":
    vms = world["vms"]
    if args[:1] == ["showvminfo"]:
        vm = vms.get(args[1])
        if vm is None:
            sys.exit(1)
        print(f'VMState="{vm["state"]}"')
        print(f'CurrentSnapshotName="{vm.get("snapshot", "")}"')
    elif args[:1] == ["controlvm"] and args[2] == "poweroff":
        vms[args[1]]["state"] = "poweroff"; save()
    elif args[:1] == ["snapshot"] and args[2] == "restore":
        if not world.get("restore_ignores_name"):
            vms[args[1]]["snapshot"] = args[3]
        save()
    elif args[:1] == ["startvm"]:
        vms[args[1]]["state"] = "running"; save()
    sys.exit(0)

if name in ("ssh", "scp", "rsync"):
    line = " ".join(args)
    stdin = sys.stdin.read() if world.get("read_stdin") and not sys.stdin.isatty() else ""
    for rule in world.get(name, []):
        if re.search(rule["match"], line + "\n" + stdin, re.S):
            seq = rule.get("outputs")
            if seq:  # successive calls consume successive outputs
                idx = rule.setdefault("_i", 0)
                rule["_i"] = min(idx + 1, len(seq) - 1)
                save()
                out = seq[idx]
                if out.get("sleep"):
                    import time; time.sleep(out["sleep"])
                sys.stdout.write(out.get("stdout", ""))
                sys.exit(out.get("rc", 0))
            sys.stdout.write(rule.get("stdout", ""))
            sys.exit(rule.get("rc", 0))
    sys.exit(world.get(name + "_default_rc", 0))

sys.exit(0)  # sleep and anything else: instant success
'''


class FakeLab:
    def __init__(self, root: Path):
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir()
        self.world_path = root / "world.json"
        self.calls_path = root / "calls.jsonl"
        self.calls_path.write_text("")
        for name in ("VBoxManage", "ssh", "scp", "rsync", "sleep"):
            path = self.bin / name
            path.write_text(STUB)
            path.chmod(0o755)
        self.world = {
            "vms": {
                "ubuntu24-puppet8-Node": {"state": "running", "snapshot": "P8NODE_BASELINE_GREEN_v2"},
                "Ubuntu24-puppet8-Master": {"state": "running", "snapshot": "P8MASTER_BASELINE_GREEN"},
            },
            "ssh": [
                {"match": r"systemctl is-active puppetserver", "stdout": "active\n"},
                {"match": r"puppet8node hostname$", "stdout": "puppet8node\n"},
            ],
        }

    def save(self):
        self.world_path.write_text(json.dumps(self.world))

    def run(self, argv, **kw):
        self.save()
        env = dict(os.environ)
        env.update({
            "PATH": f"{self.bin}:{env['PATH']}",
            "FAKE_WORLD": str(self.world_path),
            "FAKE_CALLS": str(self.calls_path),
            "PYTHONDONTWRITEBYTECODE": "1",
            # never write GREEN stamps or metrics events into the real repo's logs from a stub run
            "P8_GREEN_DIR": str(self.root / "green"),
            "P8_METRICS_DIR": str(self.root / "metrics"),
        })
        env.update(kw.pop("env", {}))
        return subprocess.run(argv, capture_output=True, text=True, env=env, timeout=60,
                              stdin=subprocess.DEVNULL, **kw)

    def calls(self, name=None):
        out = [json.loads(line) for line in self.calls_path.read_text().splitlines() if line]
        return [c for c in out if name is None or c[0] == name]

    def state(self):
        return json.loads(self.world_path.read_text())


@pytest.fixture
def lab(tmp_path):
    return FakeLab(tmp_path)


sys.dont_write_bytecode = True


@pytest.fixture(autouse=True)
def isolated_logs(tmp_path, monkeypatch):
    """No test, in-process or subprocess, writes GREEN stamps or metrics events into the real repo's logs."""
    monkeypatch.setenv("P8_GREEN_DIR", str(tmp_path / "iso_green"))
    monkeypatch.setenv("P8_METRICS_DIR", str(tmp_path / "iso_metrics"))
    monkeypatch.setenv("P8_RUNS_FILE", str(tmp_path / "iso_runs" / "metrics.jsonl"))
