"""Running a set: fresh nodes, the clean phase, the apply, the applied phase, the variants.

A run (README.md, "Running a set"):
  1. takes a fresh node of the set's kind (and a fresh peer when the set has one);
  2. CLEAN phase: every probe on the untouched node; each negative control must fail, each invariant must pass, else
     the set is INVALID (it does not tell the class's work from what a fresh node already has);
  3. applies the class (twice: the second run must change nothing but the set's expected_run2_events);
  4. APPLIED phase: read-only checks first, with their mismatch controls; then the mutating checks in file order, each
     action followed by its read-only effect (and, where the set says so, a re-apply on the node or an agent run on
     the peer); a failed check is a FINDING;
  5. each variant: the same on a fresh node of its kind with its own params fixture and its own checks.
The record is JSON plus JUnit. Exit 0 all pass, 1 findings, 2 invalid set, 3 apply or environment failure, 4 skipped.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import hashlib
import ipaddress
import json
import re
import shlex
import subprocess
import time
from pathlib import Path

import yaml

from . import manifest as mf
from . import probes, render, results, setfile
from .gate import ERROR, EVENT, agent_result, gate, verdict  # noqa: F401  (one gate for every caller)

SUITE = setfile.SUITE
MODULE = setfile.MODULE
HELPERS = (SUITE / "probe_helpers.sh").read_text(encoding="utf-8") if (SUITE / "probe_helpers.sh").is_file() else ""
PROBE_TIMEOUT = 120
PEER_SETUP_TIMEOUT = 1200
AGENT_TIMEOUT = 960
MARKER = "/var/lib/behaviour-suite/used"
EXECUTED = setfile.EXECUTED
SESSION_LOGIN = """set -e
u={user}
id "$u" >/dev/null
install -d -m 0755 /etc/sddm.conf.d
printf '[Autologin]\\nUser=%s\\nSession=plasma\\nRelogin=false\\n' "$u" > /etc/sddm.conf.d/zz-p8test-autologin.conf
systemctl restart sddm
for i in $(seq 120); do
  if who | awk '{{print $1}}' | grep -qx "$u" && pgrep -u "$u" -x plasmashell >/dev/null; then echo SESSION_UP; exit 0; fi
  sleep 1
done
echo SESSION_DOWN
"""
# After each run, the resources Puppet's own last-run report marks changed: a change shows even when its log line does
# not (a resource whose loglevel is below notice).
CHANGED = ("/opt/puppetlabs/puppet/bin/ruby -rpuppet -e 'Puppet.initialize_settings; "
           "r = YAML.unsafe_load_file(Puppet[:lastrunreport]); "
           "r.resource_statuses.each { |k, st| puts \"CHANGED #{k}\" if st.changed }' 2>/dev/null\n")
AGENT = "timeout 900 /opt/puppetlabs/bin/puppet agent -t --detailed-exitcodes 2>&1; echo \"AGENT_RC=$?\"\n" + CHANGED
PEER_AGENT = """set -e
d=/etc/p8test-agent/{certname}
install -d -m 0755 "$d" /var/lib/p8test-agent/{certname} /run/p8test-agent/{certname} /var/log/p8test-agent/{certname}
printf '[main]\\ncertname = %s\\nserver = %s\\nssldir = %s/ssl\\nvardir = %s\\nrundir = %s\\nlogdir = %s\\n' \\
  {certname} {server} "$d" /var/lib/p8test-agent/{certname} /run/p8test-agent/{certname} /var/log/p8test-agent/{certname} \\
  > "$d/puppet.conf"
grep -qE '^{ip_re}[[:space:]]+{server}$' /etc/hosts || echo '{ip} {server}' >> /etc/hosts
set +e
timeout 900 /opt/puppetlabs/bin/puppet agent -t --confdir "$d" --detailed-exitcodes --waitforcert 0 2>&1
echo "AGENT_RC=$?"
"""


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ------------------------------------------------------------------ machines

@dataclasses.dataclass
class Machine:
    kind: str
    dest: str           # the ssh destination
    addr: str           # the address the other machines reach it at
    boot: str | None = None
    name: str | None = None
    info: dict = dataclasses.field(default_factory=dict)  # what a provider reports about the machine, recorded as is


class Shell:
    """Scripts as root on a machine: `ssh <dest> sudo -n bash -s`, the probe helpers first."""

    def __init__(self, ssh: list[str], env: dict | None = None):
        self.ssh, self.env = ssh, env

    def run(self, m: Machine, script: str, timeout: int = PROBE_TIMEOUT, prefix: str = "",
            root: bool = True) -> tuple[int, str, str]:
        cmd = [*self.ssh, m.dest, "sudo -n bash -s" if root else "bash -s"]
        try:
            p = subprocess.run(cmd, input=(HELPERS if root else "") + prefix + script, capture_output=True, text=True,
                               timeout=timeout, env=self.env)
            return p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"probe timed out after {timeout}s"


class Provider:
    """Fresh machines. With a provider command: `<cmd> fresh <kind>` prints {"dest", "addr"[, "boot"]} as JSON,
    `<cmd> boot <dest>` prints the machine's boot id, `<cmd> release <dest>` lets it go; any other key of the JSON
    (the machine's baseline, the mirror it used) is recorded with the machine as the provider gave it. Without one, the machines
    given on the command line, each used once: the runner marks a machine it used and refuses a marked one."""

    def __init__(self, shell: Shell, command: list[str] | None = None, given: dict | None = None):
        self.shell, self.command, self.given = shell, command, {k: list(v) for k, v in (given or {}).items()}

    def fresh(self, kind: str) -> Machine:
        if self.command:
            p = subprocess.run([*self.command, "fresh", kind], capture_output=True, text=True, env=self.shell.env)
            if p.returncode != 0:
                raise RuntimeError(f"the provider gave no fresh {kind} node: {(p.stderr or p.stdout).strip()[-300:]}")
            got = json.loads(p.stdout.strip().splitlines()[-1])
            m = Machine(kind, got["dest"], got["addr"], got.get("boot"),
                        info={k: v for k, v in got.items() if k not in ("dest", "addr", "boot")})
        else:
            if not self.given.get(kind):
                raise RuntimeError(f"no {kind} node: give one with --node {kind}=<ssh destination>@<address>")
            m = self.given[kind].pop(0)
            rc, out, _ = self.shell.run(m, f"test -e {MARKER} && echo USED; install -d -m 0755 {Path(MARKER).parent}; "
                                        f"date -u +%FT%TZ > {MARKER}")
            if rc != 0 or "USED" in out:
                raise RuntimeError(f"{m.dest} is not fresh: a run already used it ({MARKER}); give a fresh node")
        m.boot = m.boot or self.boot(m)
        rc, out, _ = self.shell.run(m, "hostname -s")
        m.name = out.strip() if rc == 0 else None
        return m

    def boot(self, m: Machine) -> str | None:
        if self.command:
            p = subprocess.run([*self.command, "boot", m.dest], capture_output=True, text=True, env=self.shell.env)
            return p.stdout.strip() or None if p.returncode == 0 else None
        rc, out, _ = self.shell.run(m, "cat /proc/sys/kernel/random/boot_id")
        return out.strip() if rc == 0 else None

    def release(self, m: Machine) -> None:
        if self.command:
            subprocess.run([*self.command, "release", m.dest], capture_output=True, text=True, env=self.shell.env)


# ------------------------------------------------------------------ applying the class

LOCAL = """set +e
d=/var/tmp/behaviour-suite
install -d -m 0700 "$d"
printf '%s' '{b64}' | base64 -d > "$d/site.pp"
timeout 900 /opt/puppetlabs/bin/puppet apply --detailed-exitcodes --modulepath {modulepath} {hiera} "$d/site.pp" 2>&1
echo "AGENT_RC=$?"
""" + CHANGED.replace("{", "{{").replace("}", "}}")


class Applier:
    """How the class reaches the node; each mode applies twice and holds the gate (run 2 changes nothing but the set's
    expected_run2_events).
      agent    the node's agent against a Puppet server that serves the module; `--classify <cmd>` is called as
               `<cmd> <node name> <manifest file>` to make the server give the node that manifest (without it, the
               server is taken to classify the node already)
      local    `puppet apply` of the manifest on the node, with the module and its dependencies already under
               --modulepath on the node (and Hiera data under --hiera-config, when the classes look keys up)
      command  `<cmd> <class> <node dest> <node kind> <manifest file>`: exit 0 and a `GREEN:` line when the class
               applied cleanly twice (`NODE_FRESH: yes` when it checked the node was the fresh one); a variant run sets
               BEHAVIOUR_VARIANT (its name) and BEHAVIOUR_PARAMS (its params fixture, if any) in the command's
               environment
    """

    def __init__(self, mode: str, shell: Shell, command: list[str] | None = None, modulepath: str = "",
                 hiera_config: str = ""):
        self.mode, self.shell, self.command = mode, shell, command
        self.modulepath, self.hiera_config = modulepath, hiera_config
        self.manifest = ""

    def once(self, node: Machine) -> dict:
        if self.mode == "local":
            import base64  # noqa: PLC0415
            script = LOCAL.format(b64=base64.b64encode(self.manifest.encode()).decode(),
                                  modulepath=shlex.quote(self.modulepath),
                                  hiera=f"--hiera_config {shlex.quote(self.hiera_config)}" if self.hiera_config else "")
            return agent_result(*self.shell.run(node, script, timeout=AGENT_TIMEOUT))
        return agent_result(*self.shell.run(node, AGENT, timeout=AGENT_TIMEOUT))

    def again(self, node: Machine) -> dict:
        """One more run on the node (a desktop session, or a correction the set waits for)."""
        return self.once(node)

    def apply(self, cls: str, node: Machine, manifest: str, expected: list[str], variant: str = "",
              params: str = "") -> dict:
        import tempfile  # noqa: PLC0415
        self.manifest = manifest
        with tempfile.NamedTemporaryFile("w", suffix=".pp", delete=False) as f:
            f.write(manifest)
        if self.mode == "command":
            import os  # noqa: PLC0415
            env = {**(self.shell.env or os.environ), "BEHAVIOUR_VARIANT": variant, "BEHAVIOUR_PARAMS": params}
            p = subprocess.run([*self.command, cls, node.dest, node.kind, f.name], capture_output=True, text=True,
                               env=env)
            return {"rc": p.returncode, "green": p.returncode == 0 and "GREEN:" in p.stdout,
                    "node_fresh": "NODE_FRESH: yes" in p.stdout, "tail": (p.stdout + p.stderr)[-1500:]}
        if self.mode == "agent" and self.command:
            p = subprocess.run([*self.command, node.name or node.dest, f.name], capture_output=True, text=True,
                               env=self.shell.env)
            if p.returncode != 0:
                return {"rc": p.returncode, "green": False, "node_fresh": True,
                        "tail": f"classify hook failed: {(p.stdout + p.stderr)[-1400:]}"}
        first, second = self.once(node), self.once(node)
        v = verdict(first, second, expected)
        return {"rc": second["rc"], "green": v["green"], "gate": v["reason"], "node_fresh": True,
                "runs": [first, second], "tail": second["tail"]}


# ------------------------------------------------------------------ the run

class Run:
    def __init__(self, path: Path, provider: Provider, applier: Applier, shell: Shell, server: dict, localdir: str,
                 others: dict | None = None, params_dirs: list[Path] | None = None):
        self.path, self.cls = path, path.stem
        self.provider, self.applier, self.shell = provider, applier, shell
        self.server, self.localdir, self.others = server, localdir, others or {}
        self.data, self.raw = setfile.load(path)
        self.params_dirs = [*(params_dirs or []), SUITE / "fixtures" / "params"]
        self.kinds = setfile.kinds()
        self.peer_files: dict[str, str] = {}

    # values ---------------------------------------------------------
    def values(self, node: Machine, peer: Machine | None, base_peer: Machine | None) -> dict:
        v = {"NODE_NAME": node.name or "", "NODE_ADDR": node.addr, "LOCALDIR": self.localdir,
             "NODE_NETWORK": str(ipaddress.IPv4Network(f"{node.addr}/24", strict=False).network_address),
             "SERVER_NAME": self.server.get("name", ""), "SERVER_HOST": self.server.get("name", "").split(".")[0],
             "SERVER_ADDR": self.server.get("addr", "")}
        rc, out, _ = self.shell.run(node, 'echo "${SSH_CLIENT%% *}"', root=False)
        v["CONTROLLER_ADDR"] = out.strip() if rc == 0 else ""
        rc, out, _ = self.shell.run(node, "/opt/puppetlabs/bin/facter networking.ip 2>/dev/null")
        v["NODE_PRIMARY_ADDR"] = out.strip() if rc == 0 else ""
        p = peer or base_peer
        v["PEER_NAME"] = p.name if p else "peer.invalid"
        v["PEER_ADDR"] = p.addr if p else "198.51.100.1"  # a variant run without the base run's peer: unreachable
        for kind, m in self.others.items():
            v[f"NODE:{kind}"], v[f"ADDR:{kind}"] = m.name or m.dest.rsplit("@", 1)[-1], m.addr  # its host name
        v.update(setfile.throwaway_values())  # {{FIXTURE_B64:<name>}}: the suite's throwaway test material
        for m in (node, p):  # the run's own machines answer for their kinds too
            if m is not None:
                v[f"NODE:{m.kind}"], v[f"ADDR:{m.kind}"] = m.name or "", m.addr
        return v

    def rendered(self, check: dict, values: dict) -> dict:
        missing = render.needed(check, only=EXECUTED) - set(values)
        if missing:
            raise KeyError(f"check {check.get('id')}: no value for {sorted(missing)} (give the machine with --other)")
        return render.render_obj(check, values, only=EXECUTED)

    # one probe ------------------------------------------------------
    def on(self, check: dict, script: str, node: Machine, peer: Machine | None, values: dict,
           timeout: int = PROBE_TIMEOUT) -> tuple[int, str, str]:
        if check.get("host") == "peer":
            pre = "".join(f"mkdir -p /run/p8test-from-node && printf '%s' '{b64}' | base64 -d "
                          f"> /run/p8test-from-node/{Path(path).name}\n" for path, b64 in self.peer_files.items())
            return self.shell.run(peer, script, timeout, prefix=pre)
        # a set with a peer hands its address to node scripts as $PEER_ADDR (variant runs too: the base run's peer)
        return self.shell.run(node, script, timeout,
                              prefix=f"PEER_ADDR={values['PEER_ADDR']}\n" if self.data.get("peer") else "")

    def fetch_files(self, node: Machine) -> None:
        self.peer_files = {}
        for path in (self.data.get("peer") or {}).get("files") or []:
            rc, out, _ = self.shell.run(node, f"base64 -w0 {shlex.quote(path)} 2>/dev/null; true")
            self.peer_files[path] = out.strip() if rc == 0 else ""

    def probe(self, check: dict, node, peer, values, act: bool = False) -> dict:
        action = None
        if "mutates" in check and act:
            arc, aout, aerr = self.on(check, check["probe"], node, peer, values, check.get("timeout", PROBE_TIMEOUT))
            action = {"mutates": check["mutates"], "rc": arc, "stdout": aout[-1000:], "stderr": aerr[-500:]}
        rc, out, err = self.on(check, check["effect"] if "mutates" in check else check["probe"], node, peer, values)
        row = {"id": check["id"], "control": check["control"], "rc": rc, "passed": probes.meets(check, rc, out),
               "stdout": out[-2000:], "stderr": err[-1000:]}
        if check.get("host") == "peer":
            row["host"] = "peer"
        if "mutates" in check:
            row["mutating"], row["action"] = True, action
        return row

    def mismatch(self, check: dict, row: dict, node, peer, values) -> None:
        mm = check.get("mismatch")
        if not mm:
            return
        if not row["passed"]:
            row["mismatch"] = {"varies": mm["varies"], "not_run": "the check itself failed"}
            return
        rc, out, err = self.on(check, mm["probe"], node, peer, values)
        row["mismatch"] = {"varies": mm["varies"], "rc": rc, "passed": probes.meets(check, rc, out),
                           "stdout": out[-1000:], "stderr": err[-500:]}

    # one run (base or variant) -------------------------------------
    def one(self, checks: list[dict], kind: str, params: str | None, record: dict, with_peer: bool,
            base_peer: Machine | None, say) -> Machine | None:
        """Returns the peer it used (so a variant can name its address)."""
        expected = (self.data.get("apply") or {}).get("expected_run2_events") or []
        node = self.provider.fresh(kind)
        record["nodes"] = {"node": {"kind": kind, "dest": node.dest, "boot_id": node.boot, **node.info}}
        peer = None
        if with_peer and self.data.get("peer"):
            peer = self.provider.fresh(self.data["peer"]["kind"])
            record["nodes"]["peer"] = {"kind": peer.kind, "dest": peer.dest, "boot_id": peer.boot, **peer.info}
        try:
            values = self.values(node, peer, base_peer)
            record["values"] = values
            setup = (self.data.get("peer") or {}).get("setup")
            if peer and setup:  # the peer is prepared before the clean phase (a service the class uses, e.g. a registry)
                say("==> Preparing the peer (peer.setup)")
                rc, out, err = self.shell.run(peer, render.render(setup, values), timeout=PEER_SETUP_TIMEOUT)
                record["peer_setup"] = {"rc": rc, "tail": (out + err)[-1500:]}
                if rc != 0:
                    raise RuntimeError(f"peer setup failed (rc {rc}): {(out + err).strip()[-300:]}")
            checks = [self.rendered(c, values) for c in checks]
            if peer:
                self.fetch_files(node)
            say("==> CLEAN phase: negative controls must fail, invariants must pass (mutating checks: effect only)")
            for c in checks:
                r = self.probe(c, node, peer, values)
                r["ok"] = (not r["passed"]) if c["control"] == "negative" else r["passed"]
                record["clean"].append(r)
                say(f"  {'ok ' if r['ok'] else 'BAD'} {c['id']} ({c['control']}: "
                    f"{'passed' if r['passed'] else 'failed'} on the clean node)")
            bad = [r["id"] for r in record["clean"] if not r["ok"]]
            if bad:
                record["valid"] = False
                record["problems"].append(f"controls did not hold on the clean node: {', '.join(bad)}")
                record["outcome"] = "INVALID_SET"
                return peer
            say(f"==> Applying {self.cls}")
            mine = next((v for v in self.data.get("variants") or [] if v.get("name") == record.get("name")), {})
            text = mf.build(self.data, kind, self.kinds, self.params_dirs, SUITE / "fixtures",
                            variant=params, render=lambda t: render.render(t, values),
                            variant_fixture=mine.get("node_fixture"))
            record["manifest_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            record["apply"] = self.applier.apply(self.cls, node, text, expected, record.get("name") or "",
                                                 params or "")
            if not record["apply"]["green"]:
                record["outcome"] = "APPLY_FAILED"
                return peer
            if "name" not in record and self.data.get("session"):  # the base run (a variant's record carries its name)
                if not self.session(node, record, expected, say):
                    return peer
            if peer:
                self.fetch_files(node)
            self.applied(checks, node, peer, values, record, say)
            return peer
        finally:
            for role, m in (("node", node), ("peer", peer)):
                if m is not None:
                    entry = record["nodes"][role]
                    entry["boot_id_at_end"] = self.provider.boot(m)
                    entry["fresh"] = bool(entry["boot_id"]) and entry["boot_id_at_end"] == entry["boot_id"] and \
                        (role != "node" or bool((record.get("apply") or {}).get("node_fresh", True)))
            for m in (peer, node):  # a run keeps only the machines it uses
                if m is not None:
                    self.provider.release(m)

    def session(self, node: Machine, record: dict, expected: list[str], say) -> bool:
        user = self.data["session"]["user"]
        say(f"==> Logging {user} in to Plasma, then two agent runs with the session up")
        rc, out, err = self.shell.run(node, SESSION_LOGIN.format(user=user), timeout=180)
        record["session"] = {"user": user, "up": "SESSION_UP" in out, "runs": []}
        if not record["session"]["up"]:
            record["problems"].append(f"the {user} session did not come up: {(out + err).strip()[-300:]}")
            record["outcome"] = "ENVIRONMENT_FAILED"
            return False
        runs = [self.applier.again(node), self.applier.again(node)]
        record["session"]["runs"] = runs
        v = verdict(runs[0], runs[1], expected)
        if not v["green"]:
            record["problems"].append(f"with {user} logged in the class did not apply cleanly and idempotently: "
                                      f"{v['reason']}")
            record["outcome"] = "APPLY_FAILED"
            return False
        return True

    def applied(self, checks, node, peer, values, record, say) -> None:
        say("==> APPLIED phase: every check must pass (read-only first; mutating only if all of those pass)")
        readonly = [c for c in checks if "mutates" not in c]
        mutating = [c for c in checks if "mutates" in c]
        for c in readonly:
            r = self.probe(c, node, peer, values)
            self.mismatch(c, r, node, peer, values)
            record["applied"].append(r)
            mm = r.get("mismatch") or {}
            note = "" if not mm else "; mismatch " + ("not run" if mm.get("not_run") else
                                                      "PASSED: does not discriminate" if mm["passed"] else
                                                      "failed as required")
            say(f"  {'pass' if r['passed'] else 'FAIL'} {c['id']}{note}")
        weak = [r["id"] for r in record["applied"] if (r.get("mismatch") or {}).get("passed")]
        gate_ids = [r["id"] for r in record["applied"] if not r["passed"]]
        na = (self.data.get("node_agent") or {}).get("after")
        anchors = na if isinstance(na, list) else [na]
        pa = self.data.get("peer_agent") or {}
        for c in mutating:
            if weak or gate_ids:
                reason = "not run: the set is invalid" if weak else f"not run: read-only checks failed ({', '.join(gate_ids)})"
                record["applied"].append({"id": c["id"], "control": c["control"], "mutating": True, "passed": False,
                                          "not_run": reason, "rc": None, "stdout": "", "stderr": ""})
                say(f"  SKIP {c['id']} (mutating; {reason})")
                continue
            if c.get("host") == "peer" and peer:
                self.fetch_files(node)
            r = self.probe(c, node, peer, values, act=True)
            record["applied"].append(r)
            say(f"  {'pass' if r['passed'] else 'FAIL'} {c['id']} (mutating; action rc {r['action']['rc']}, judged on "
                "the effect)")
            if c["id"] in anchors:
                run = self.applier.again(node)
                if isinstance(na, list):
                    record.setdefault("node_agent", {})[c["id"]] = run
                else:
                    record["node_agent"] = run
                say(f"  node agent run: rc {run['rc']}, {len(run['events'])} changed")
            if pa.get("after") == c["id"] and peer:
                script = PEER_AGENT.format(certname=pa["certname"], server=node.name, ip=node.addr,
                                           ip_re=node.addr.replace(".", "\\."))
                run = agent_result(*self.shell.run(peer, script, timeout=AGENT_TIMEOUT))
                run.update(certname=pa["certname"], server=node.name)
                record["peer_agent"] = run
                say(f"  peer agent run as {pa['certname']} against {node.name}: rc {run['rc']}, "
                    f"{len(run['events'])} changed")
        if weak:
            record["valid"] = False
            record["problems"].append(f"mismatch controls passed (checks do not discriminate): {', '.join(weak)}")
            record["outcome"] = "INVALID_SET"
            return
        record["not_run"] = [r["id"] for r in record["applied"] if r.get("not_run")]
        record["findings"] = [r["id"] for r in record["applied"] if not r["passed"] and not r.get("not_run")]
        record["outcome"] = "FINDINGS" if record["findings"] or record["not_run"] else "ALL_PASS"

    # the whole set ---------------------------------------------------
    def run(self, label: str, variants: list[str] | None, say=print) -> dict:
        t0 = time.monotonic()
        problems = setfile.validate(self.path)
        record = {"class": self.cls, "role": label, "at": now(), "set_sha256": hashlib.sha256(self.raw).hexdigest(),
                  "valid": not problems, "problems": problems, "clean": [], "apply": None, "applied": [],
                  "findings": [], "not_run": [], "outcome": None}
        if problems:
            record["outcome"] = "INVALID_SET"
        elif "deferred" in self.data:
            record["outcome"] = "SKIPPED"
            record["problems"].append(f"deferred: needs {self.data['deferred'].get('needs')}")
        elif self.applier.mode == "local" and (self.data.get("apply") or {}).get("requires") == ["server"]:
            record["outcome"] = "SKIPPED"
            record["problems"].append("this set needs a Puppet server (apply.requires); local apply cannot run it")
        else:
            kind = self.data["apply"]["node"]
            base = [c for c in self.data["checks"] if "variant" not in c]
            try:
                base_peer = self.one(base, kind, None, record, "base" in setfile.peer_runs(self.data), None, say)
            except (RuntimeError, KeyError, FileNotFoundError) as err:
                record["problems"].append(str(err))
                record["outcome"] = "ENVIRONMENT_FAILED"
                base_peer = None
            chosen = [v for v in self.data.get("variants") or [] if variants is None or v["name"] in variants]
            if chosen and record["outcome"] not in ("ENVIRONMENT_FAILED",):
                record["variants"] = {}
                for v in chosen:
                    say(f"==> VARIANT {v['name']}: node {v.get('node', kind)}" +
                        (f", params {v['params']}" if "params" in v else ""))
                    sub = {"name": v["name"], "node": v.get("node", kind), "params": v.get("params"), "clean": [],
                           "apply": None, "applied": [], "findings": [], "not_run": [], "problems": [], "valid": True,
                           "outcome": None}
                    mine = [c for c in self.data["checks"] if c.get("variant") == v["name"]]
                    try:
                        self.one(mine, v.get("node", kind), v.get("params"), sub, v["name"] in setfile.peer_runs(self.data),
                                 base_peer, say)
                    except (RuntimeError, KeyError, FileNotFoundError) as err:
                        sub["problems"].append(str(err))
                        sub["outcome"] = "ENVIRONMENT_FAILED"
                    record["variants"][v["name"]] = sub
                    say(f"==> VARIANT {v['name']}: {sub['outcome']}")
            record["outcome"] = results.combined([record["outcome"]] + [v["outcome"] for v in
                                                                        (record.get("variants") or {}).values()])
        record["duration_s"] = round(time.monotonic() - t0, 1)
        return record


def load_others(spec: list[str]) -> dict:
    out = {}
    for item in spec:
        kind, _, rest = item.partition("=")
        dest, _, addr = rest.partition("@")
        out[kind] = Machine(kind, dest, addr)
    return out


def yaml_dump(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False)
