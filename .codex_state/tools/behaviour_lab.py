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
PARAMS = Path(os.environ.get("P8_PARAMS_DIR") or Path.home() / ".config" / "infra_populi" / "params")
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
        rv = subprocess.run([str(TOOLS / "revert_node.sh"), "--node", arg], capture_output=True, text=True, env=env())
        sys.stderr.write(rv.stdout[-2000:] + rv.stderr[-1000:])
        if rv.returncode != 0:
            print(f"revert of {arg} failed", file=sys.stderr)
            return 1
        if os.environ.get("BEHAVIOUR_LAB_LOCAL") == "1":
            copy_modules(node["alias"])
        boot = ssh(node["alias"], "cat /proc/sys/kernel/random/boot_id").stdout.strip()
        print(json.dumps({"dest": node["alias"], "addr": node["hostonly_ip"], "boot": boot or None}))
        return 0
    if action == "boot":
        p = ssh(arg, "cat /proc/sys/kernel/random/boot_id")
        print(p.stdout.strip())
        return p.returncode
    # release: a p8lab-* machine is stopped (only the nodes a run needs stay powered on, HQ 2026-11-17 ruling 5); the
    # default node stays up for the next run, which reverts it anyway
    vm = next((n["vm"] for n in kinds().values() if n["alias"] == arg), "")
    if vm.startswith("p8lab-"):
        subprocess.run([str(TOOLS / "lab_vm.sh"), "stop", vm], capture_output=True, text=True)
    return 0


# ------------------------------------------------------------------ apply hook

def harness(argv: list[str]) -> int:
    cls, _dest, kind, manifest = argv
    variant = os.environ.get("BEHAVIOUR_VARIANT", "")
    params = os.environ.get("BEHAVIOUR_PARAMS", "")
    data = __import__("yaml").safe_load((SUITE / "checks" / f"{cls}.yml").read_text())
    v = next((x for x in data.get("variants") or [] if x["name"] == variant), {}) if variant else {}
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
    p = subprocess.run([HARNESS, *(["--node", kind] if variant else []), f"puppet_infrastructure::{cls}"],
                       capture_output=True, text=True, env=e)
    print(p.stdout[-4000:])
    print("\n".join(l for l in p.stdout.splitlines() if l.startswith(("GREEN:", "NODE_FRESH:"))))
    print(p.stderr[-2000:], file=sys.stderr)
    return p.returncode


# ------------------------------------------------------------------ run

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
    me = str(Path(__file__).resolve())
    lock = subprocess.run([str(TOOLS / "lab_lock.sh"), "take", str(os.getpid()), f"behaviour_lab.py run {' '.join(argv)}"],
                          capture_output=True, text=True)
    if lock.returncode != 0:
        print(f"the lab is busy: {lock.stderr.strip()}", file=sys.stderr)
        return 3
    try:
        e = env()
        cmd = [sys.executable, str(SUITE / "run"), "--provider", f"{sys.executable} {me} provider",
               "--server", SERVER, "--localdir", LOCALDIR, "--params", str(PARAMS), "--out", str(out),
               "--ssh", "ssh -o BatchMode=yes"]
        cmd += [f"--other={k}={n['alias']}@{n['hostonly_ip']}" for k, n in kinds().items()]
        if local:
            e["BEHAVIOUR_LAB_LOCAL"] = "1"
            cmd += ["--apply", "local", "--modulepath", MODULES_ON_NODE, "--hiera-config",
                    f"{HIERA_ON_NODE}/hiera.yaml"]
        else:
            cmd += ["--apply", "command", "--apply-command", f"{sys.executable} {me} harness"]
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
