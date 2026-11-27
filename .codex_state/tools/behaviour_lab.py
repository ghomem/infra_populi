#!/usr/bin/env python3
"""The lab's hooks for the public behaviour runner (HQ review of design note F, rulings 3 and 7).

  behaviour_lab.py run [--local] [--resume] [--out <dir>] [--variant <name>]... <class>... | --all
      holds the lab lock and runs spec/behaviour/run with the lab's machines: a fresh node is a reverted one
      (revert_node.sh), the server is the master, the params are the suite's fixtures and the local ones, and the
      class is applied
        - by default with the gate-v2 harness (test_class.sh), after checking that the harness renders exactly the
          manifest the runner built (the engine's path of record);
        - with --local by `puppet apply` on the node, the module from this repository and its dependencies and Hiera
          data from the master copied onto the node first (ruling 3's measurement).
      Records go to .codex_state/checks/public/<mode>/<class>/ (default --out). --all: every set that is not deferred.
      --resume: skips a class whose latest record there is not ENVIRONMENT_FAILED (a slow uplink makes reverts fail
      now and then; the measurement is run again until each set has a real outcome).
  behaviour_lab.py provider fresh <kind> | boot <dest> | release <dest>      (the runner's provider hook)
  behaviour_lab.py harness <class> <dest> <kind> <manifest>                  (the runner's apply hook)

The engine's behaviour runs (phase3.py run, HQ review of the behaviour suite ruling 2) are this same command mode,
started by phase3.py under its own lab lock (runner_command). P8_PHASE3_REVERT, P8_PHASE3_HARNESS and P8_PHASE3_LABVM
replace revert_node.sh, the harness and lab_vm.sh (the engine's tests).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SUITE = REPO / "spec" / "behaviour"
sys.path.insert(0, str(TOOLS))

import manifest_compare as mc  # noqa: E402
import nodes  # noqa: E402

HARNESS = mc.HARNESS
MASTER = "puppet8master"
SERVER = "puppet8master.example.com@192.168.56.10"
LOCALDIR = "/opt/puppet-infrastructure"
def params_dir() -> Path:
    return Path(os.environ.get("P8_PARAMS_DIR") or Path.home() / ".config" / "infra_populi" / "params")
MODULES_ON_NODE = "/var/tmp/behaviour-modules"
HIERA_ON_NODE = "/var/tmp/behaviour-hiera"
# On the master: the environment the harness deploys into (r10k's moduledir and the environment's Hiera).
MASTER_ENV = "/etc/puppetlabs/code/environments/production"


def env() -> dict:
    e = dict(os.environ)
    e["PATH"] = f"{TOOLS / 'sshmux'}:{e['PATH']}"
    e["P8_LAB_LOCKED"] = "1"
    return e


def ssh(dest: str, script: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", "-o", "BatchMode=yes", dest, "sudo -n bash -s"], input=script, text=True,
                          capture_output=True, env=env(), **kw)


def kinds() -> dict:
    return nodes.load()["nodes"]


def revert_tool() -> str:
    return os.environ.get("P8_PHASE3_REVERT") or str(TOOLS / "revert_node.sh")


def harness_tool() -> str:
    return os.environ.get("P8_PHASE3_HARNESS") or HARNESS


def labvm_tool() -> str:
    return os.environ.get("P8_PHASE3_LABVM") or str(TOOLS / "lab_vm.sh")


def kind_of(dest: str) -> str | None:
    return next((k for k, n in kinds().items() if n["alias"] == dest), None)


def boot_of(kind: str) -> str | None:
    """The node's kernel boot ID as the engine reads it (revert_node.sh --node-state, first line), or None."""
    p = subprocess.run([revert_tool(), "--node", kind, "--node-state"], capture_output=True, text=True, env=env())
    words = p.stdout.split()
    return words[0] if p.returncode == 0 and words else None


def revert_mirror(stdout: str) -> str | None:
    """The apt mirror a revert used, from its REVERT_METRICS line ("primary", or "fallback <url>"); None if absent."""
    for line in reversed(stdout.splitlines()):
        if line.startswith("REVERT_METRICS "):
            try:
                return json.loads(line.split(" ", 1)[1]).get("apt_mirror")
            except ValueError:
                return None
    return None


# ------------------------------------------------------------------ provider

def copy_modules(dest: str) -> None:
    """The node gets the master's modules, this repository's module in place of the deployed one, and the master's
    Hiera data under a hiera.yaml of its own (local apply has no server to ask)."""
    steps = [
        # the master's plain alias forces a terminal (RequestTTY force), which mangles a binary stream: its -rsync
        # alias does not
        (["ssh", "-o", "BatchMode=yes", f"{MASTER}-rsync", f"sudo -n tar -C {MASTER_ENV} -cf - modules data hiera.yaml"],
         ["ssh", "-o", "BatchMode=yes", dest, f"sudo -n bash -c 'rm -rf {MODULES_ON_NODE} {HIERA_ON_NODE}; "
          f"install -d {MODULES_ON_NODE} {HIERA_ON_NODE}; tar -C {HIERA_ON_NODE} -xf - && "
          f"mv {HIERA_ON_NODE}/modules/* {MODULES_ON_NODE}/ && rmdir {HIERA_ON_NODE}/modules'"]),
    ]
    files = subprocess.run(["git", "-C", str(REPO), "ls-files", "manifests", "templates", "files", "lib", "functions",
                            "types", "metadata.json"], capture_output=True, text=True, check=True).stdout.split()
    steps.append((["tar", "-C", str(REPO), "-cf", "-", *files],
                  ["ssh", "-o", "BatchMode=yes", dest, f"sudo -n bash -c 'rm -rf {MODULES_ON_NODE}/puppet_infrastructure; "
                   f"install -d {MODULES_ON_NODE}/puppet_infrastructure; "
                   f"tar -C {MODULES_ON_NODE}/puppet_infrastructure -xf -'"]))
    for src, dst in steps:
        a = subprocess.Popen(src, stdout=subprocess.PIPE, env=env())
        b = subprocess.run(dst, stdin=a.stdout, capture_output=True, text=True, env=env())
        a.stdout.close()
        if a.wait() != 0 or b.returncode != 0:
            raise SystemExit(f"copying modules to {dest} failed: {b.stderr.strip()[-300:]}")
    fix = ssh(dest, f"""set -e
cd {HIERA_ON_NODE}
sed -i 's#^\\(\\s*datadir:\\).*#\\1 {HIERA_ON_NODE}/data#' hiera.yaml
grep -q 'datadir: {HIERA_ON_NODE}/data' hiera.yaml || printf '  datadir: {HIERA_ON_NODE}/data\\n' >> hiera.yaml
""")
    if fix.returncode != 0:
        raise SystemExit(f"Hiera on {dest}: {fix.stderr.strip()[-300:]}")


def provider(argv: list[str]) -> int:
    action, arg = argv[0], argv[1]
    if action == "fresh":
        node = kinds()[arg]
        if node.get("status", "active") != "active":
            print(f"node kind {arg} is {node.get('status')}", file=sys.stderr)
            return 1
        rv = subprocess.run([revert_tool(), "--node", arg], capture_output=True, text=True, env=env())
        if rv.returncode != 0:  # the reason alone: the runner records the provider's message as the run's problem
            err = [l for l in (rv.stderr or rv.stdout).splitlines() if l.strip()][-1:] or ["(no output)"]
            print(f"node revert failed: {err[0]}", file=sys.stderr)
            return 1
        sys.stderr.write(rv.stdout[-2000:] + rv.stderr[-1000:])
        if os.environ.get("BEHAVIOUR_LAB_LOCAL") == "1":
            copy_modules(node["alias"])
        print(json.dumps({"dest": node["alias"], "addr": node["hostonly_ip"], "boot": boot_of(arg),
                          "snapshot": node.get("baseline_snapshot"), "apt_mirror": revert_mirror(rv.stdout)}))
        return 0
    if action == "boot":
        kind = kind_of(arg)
        boot = boot_of(kind) if kind else None
        print(boot or "")
        return 0 if boot else 1
    # release: a p8lab-* machine is stopped (only the nodes a run needs stay powered on, HQ 2026-11-17 ruling 5); the
    # default node stays up for the next run, which reverts it anyway
    vm = next((n["vm"] for n in kinds().values() if n["alias"] == arg), "")
    if vm.startswith("p8lab-"):
        subprocess.run([labvm_tool(), "stop", vm], capture_output=True, text=True)
    return 0


# ------------------------------------------------------------------ apply hook

def harness(argv: list[str]) -> int:
    cls, _dest, kind, manifest = argv
    variant = os.environ.get("BEHAVIOUR_VARIANT", "")
    params = os.environ.get("BEHAVIOUR_PARAMS", "")
    checks = Path(os.environ.get("BEHAVIOUR_LAB_CHECKS") or SUITE / "checks")
    data = __import__("yaml").safe_load((checks / f"{cls}.yml").read_text())
    v = next((x for x in data.get("variants") or [] if x["name"] == variant), {}) if variant else {}
    mc.HARNESS = harness_tool()
    rc, text = mc.harness(cls, kind if variant else None, params or None)
    if rc != 0:
        print(f"the harness did not render: {text[-500:]}")
        return 1
    theirs, ours = mc.code(text), mc.public_code(Path(manifest).read_text())
    if theirs != ours:
        print(f"MANIFEST DIFFERS: the harness renders {len(theirs)} lines, the runner built {len(ours)}")
        return 1
    e = env()
    e["P8_METRICS_DIR"] = str(REPO / ".codex_state" / "logs" / "phase3-metrics")
    if params:
        e["P8_PARAMS_VARIANT"] = params
        if v.get("no_resources"):
            e["P8_VARIANT_NO_RESOURCES"] = "1"
    p = subprocess.run([harness_tool(), *(["--node", kind] if variant else []), f"puppet_infrastructure::{cls}"],
                       capture_output=True, text=True, env=e)
    print(p.stdout[-4000:])
    print("\n".join(l for l in p.stdout.splitlines() if l.startswith(("GREEN:", "NODE_FRESH:"))))
    print(p.stderr[-2000:], file=sys.stderr)
    return p.returncode


# ------------------------------------------------------------------ run

def runner_command(out: Path, local: bool = False, checks: Path | None = None) -> tuple[list[str], dict]:
    """The public runner's command line and environment for the lab (the caller holds the lab lock)."""
    me = str(Path(__file__).resolve())
    e = env()
    cmd = [sys.executable, str(SUITE / "run"), "--provider", f"{sys.executable} {me} provider",
           "--server", SERVER, "--localdir", LOCALDIR, "--params", str(params_dir()), "--out", str(out),
           "--ssh", "ssh -o BatchMode=yes"]
    if checks:
        cmd += ["--checks", str(checks)]
    cmd += [f"--other={k}={n['alias']}@{n['hostonly_ip']}" for k, n in kinds().items()]
    if local:
        e["BEHAVIOUR_LAB_LOCAL"] = "1"
        cmd += ["--apply", "local", "--modulepath", MODULES_ON_NODE, "--hiera-config", f"{HIERA_ON_NODE}/hiera.yaml"]
    else:
        cmd += ["--apply", "command", "--apply-command", f"{sys.executable} {me} harness"]
    return cmd, e


def run(argv: list[str]) -> int:
    local, resume = "--local" in argv, "--resume" in argv
    argv = [a for a in argv if a not in ("--local", "--resume")]
    out = REPO / ".codex_state" / "checks" / "public" / ("local" if local else "harness")
    if "--out" in argv:
        i = argv.index("--out")
        out = Path(argv[i + 1])
        del argv[i:i + 2]
    if "--all" in argv:
        argv.remove("--all")
        argv += [p.stem for p in sorted((SUITE / "checks").glob("*.yml"))
                 if "deferred" not in __import__("yaml").safe_load(p.read_text())]
    if resume:
        def done(cls: str) -> bool:
            files = sorted((out / cls).glob("*.json"))
            return bool(files) and json.loads(files[-1].read_text()).get("outcome") != "ENVIRONMENT_FAILED"
        argv = [a for a in argv if a.startswith("-") or not done(a)]
        if not [a for a in argv if not a.startswith("-")]:
            print("nothing left to run")
            return 0
    lock = subprocess.run([str(TOOLS / "lab_lock.sh"), "take", str(os.getpid()), f"behaviour_lab.py run {' '.join(argv)}"],
                          capture_output=True, text=True)
    if lock.returncode != 0:
        print(f"the lab is busy: {lock.stderr.strip()}", file=sys.stderr)
        return 3
    try:
        cmd, e = runner_command(out, local)
        return subprocess.run(cmd + argv, env=e).returncode
    finally:
        subprocess.run([str(TOOLS / "lab_lock.sh"), "release", str(os.getpid())], capture_output=True)


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("run", "provider", "harness"):
        print(__doc__)
        return 2
    return {"run": run, "provider": provider, "harness": harness}[argv[0]](argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
