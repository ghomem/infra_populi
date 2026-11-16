#!/usr/bin/env python3
"""Phase 3 check runner (HQ batch-3 acceptance B; ruling 11 of 2026-10-27): behaviour checks for a migrated class,
derived from the pinned baseline, probed on the node only, with negative controls that must fail on the clean node.

  phase3.py validate <class>     the check file alone (no node): schema, derived_from against the class's baseline,
                                 probe rules. Exit 0 valid, 2 invalid.
  phase3.py run <class> [--role author|reviewer]
                                 validate; revert the node; CLEAN phase (every probe on the reverted node: each
                                 `negative` control must FAIL, each `invariant` must PASS, else the set is INVALID);
                                 apply the class with the gate-v2 harness on that fresh node; APPLIED phase (every
                                 check must PASS; a failure is a FINDING). Writes JSON + JUnit XML to
                                 .codex_state/checks/results/<class>/<UTC>-<role>.{json,xml}.
                                 Exit 0 all pass, 1 findings, 2 invalid set, 3 apply/environment failure.
  phase3.py spot <class> [--n N] [--seed S]
                                 reviewer: N random derived_from references (default 3), each printed with the
                                 baseline lines read fresh from the upstream pin, beside the check's probe/expect.
  phase3.py state [<class> ...]  behaviour state per class (HQ 2026-11-16), DERIVED from the check, result and
                                 review files: pass | finding | deferred (<needs>) | none (no check file) |
                                 unreviewed | stale (check file changed after its review) | review-failed | invalid;
                                 with authoring minutes and the author-run / reviewer-run / review times. A finding
                                 without .codex_state/escalations/<class>.behaviour.md is flagged.
  phase3.py verdict <class> --derived ok|fail --evidence TEXT [--evidence ...]
                                 reviewer: compares its latest run with the latest author run (same validity, same
                                 per-check outcome on both phases) and persists .codex_state/checks/reviews/<class>/
                                 <UTC>.json. PASS = both runs valid + reproduced + derived ok.

A class that cannot be tested on this lab declares a DEFERRAL instead of checks (HQ 2026-11-16):
  class / baseline / authoring as below, plus
  deferred: {needs: second-node|browser|rhel|desktop, why: <one or two sentences>, lifted_by: <node kind>}
  derived_from: [<baseline references showing why, as for a check>]
The reviewer judges a deferral too (`--phase3`: `spot` prints the cited lines beside the reason, `verdict` records
it); it counts as `deferred` only once that review passed (HQ 2026-11-16 item 7b). `lifted_by` names a kind of
.codex_state/lab/nodes.yml with the needed capability (desktop/browser -> desktop, rhel -> a RedHat node,
second-node -> second-node). Any set may also list what it does NOT cover (item 7a):
  uncovered: [{what: <behaviour>, why: <why not here>, lifted_by: <node kind>}]

Check file .codex_state/checks/<class>.yml:
  class: <short name>             # = the file name
  baseline: release-0.9.10 (cf477c6)   # = `baseline.py for <class>`
  fixture: params | defaults      # what the harness applies: the class's params file, or no params file at all
  authoring: {minutes: N, notes: "..."}
  checks:
    - id: <slug>
      what: <one line>
      control: negative | invariant          # negative: must FAIL on the clean node (mandatory: >= 1 per set)
      why_invariant: <why it also holds before the class>   # required for invariant
      derived_from:                          # >= 1; each must resolve at the class's baseline commit
        - {path: manifests/x.pp, lines: "12-14", text: "<exact substring of those lines>"}
        - {path: files/x, sha256: <of the whole baseline file>}
      probe: <shell, run as root on the node via `ssh <node> sudo -n bash -s`>
      expect: {rc: 0, stdout: <regex, re.M>, stdout_not: <regex>}   # rc defaults to 0
      # opt-in MUTATING check (HQ 2026-11-10): `probe` is an action that changes the node; the evidence is its effect
      mutates: <what the action changes on the node, declared>
      effect: <read-only shell; `expect` is matched against ITS output, never the action's>
      # MISMATCH control (HQ 2026-11-16): the same probe with ONE value deliberately wrong; it must FAIL `expect` on the
      # applied node, or the check does not discriminate and the set is INVALID. Mandatory for a probe that hands a
      # name, user, key, cipher or vhost to a tool and takes the tool's verdict (TLS, logins, HTTP by host); optional
      # for direct state reads.
      mismatch: {varies: <which value is wrong and why the verdict must change>, probe: <read-only shell>}

Probe rules (validate): the node is the only host — no other host name or address, no ssh/scp/sftp/rsync except to
the node itself (127.0.0.1/localhost), never Puppet (agent/apply/resource); read-only — no service or package state
change, no rm/tee/redirect into a file. Mutating checks (HQ 2026-11-10): opt-in per check with `mutates` (declared
change) + a read-only `effect`; the action may change node state (host rules and the Puppet ban still apply); they are
negative controls whose EFFECT must be absent on the clean node (the action never runs there); after apply they run
only once every read-only check has passed, in file order, and pass on the effect. Never on the master: the runner's
only execution path is the node.
P8_PHASE3_DIR redirects checks/results/reviews; P8_PHASE3_HARNESS / P8_PHASE3_REVERT replace the harness and the
revert tool, P8_PARAMS_DIR the params directory (tests). Harness metrics events go to .codex_state/logs/phase3-metrics, never into Phase 1 records.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import baseline  # noqa: E402

NODE = "puppet8node"  # set per run to the class's lab node alias (nodes.yml; HQ 2026-11-16 item 2)
PROBE_TIMEOUT = 120
PARAMS_DIR = Path(os.environ.get("P8_PARAMS_DIR") or Path.home() / ".config" / "infra_populi" / "params")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{1,62}")
FORBIDDEN = [
    (re.compile(r"puppet8master|puppet8node|p8lab-[a-z0-9-]+|example\.com:8140|\b192\.168\.\d+\.\d+"),
     "names another lab host"),
    (re.compile(r"\b(scp|sftp|rsync)\s"), "copies to/from another host"),
    (re.compile(r"\bpuppet\s+(agent|apply|resource)\b|/opt/puppetlabs/bin/puppet\b"), "runs Puppet (changes the node)"),
    (re.compile(r"\bsystemctl\s+(start|stop|restart|reload|enable|disable|mask|unmask|kill)\b"), "changes a service"),
    (re.compile(r"\b(apt|apt-get|dpkg|dnf|yum|rpm)\s+(-\S+\s+)*(install|remove|purge|-i|-e)\b"), "changes packages"),
    (re.compile(r"(^|[\s;&|])(rm|tee|truncate|shred|useradd|userdel|groupadd|groupdel|chmod|chown)\s"),
     "changes files or accounts"),
    (re.compile(r"(?<![0-9&])>>?\s*(?!/dev/null\b|&)\S"), "redirects into a file"),
]
LOCAL_SSH = re.compile(r"(^|[\s;&|(])ssh\s")  # ssh as a command, not a path like /etc/ssh/
LOCAL_TARGET = re.compile(r"(\S+@)?(127\.0\.0\.1|localhost|::1)\b")


def phase3_dir() -> Path:
    return Path(os.environ.get("P8_PHASE3_DIR") or REPO / ".codex_state" / "checks")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def short(name: str) -> str:
    m = re.fullmatch(r"(?:puppet_infrastructure::)?([a-z][a-z0-9_]*)", name)
    if not m:
        raise SystemExit(f"ERROR: invalid class name {name!r}")
    return m.group(1)


def label(base: baseline.Baseline) -> str:
    return f"{base.name} ({base.commit[:7]})"


# ------------------------------------------------------------------ validate

def load_set(cls: str) -> tuple[dict, bytes]:
    path = phase3_dir() / f"{cls}.yml"
    if not path.is_file():
        raise SystemExit(f"ERROR: no check file {path}")
    raw = path.read_bytes()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as err:  # a malformed set is INVALID, not a crash (batch 4)
        raise SystemExit(f"INVALID {cls}: {path.name} is not valid YAML: {str(err).splitlines()[0]} "
                         f"({' '.join(str(err).split())[-80:]})") from None
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: {path} is not a YAML mapping")
    return data, raw


def parse_lines(spec: str, length: int) -> tuple[int, int] | None:
    m = re.fullmatch(r"(\d+)(?:-(\d+))?", str(spec))
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2) or m.group(1))
    return (a, b) if 1 <= a <= b <= length else None


def resolve_ref(ref: dict, base: baseline.Baseline) -> tuple[str | None, str]:
    """(problem or None, the baseline text the reference points at)."""
    path = ref.get("path") if isinstance(ref, dict) else None
    if not path or not isinstance(path, str):
        return "derived_from entry without a path", ""
    data = baseline.git_show(base.upstream, base.commit, path)
    if data is None:
        return f"{path} does not exist at {label(base)}", ""
    if "sha256" in ref:
        if hashlib.sha256(data).hexdigest() != ref["sha256"]:
            return f"{path}: sha256 differs from the file at {label(base)}", ""
        return None, f"<whole file, {len(data)} bytes, sha256 {ref['sha256'][:12]}>"
    lines = data.decode("utf-8", "replace").splitlines()
    span = parse_lines(ref.get("lines", ""), len(lines))
    if span is None:
        return f"{path}: lines {ref.get('lines')!r} not a range inside 1-{len(lines)}", ""
    text = "\n".join(lines[span[0] - 1:span[1]])
    needle = ref.get("text")
    if not needle or not isinstance(needle, str):
        return f"{path}:{ref.get('lines')}: `text` (an exact substring of those lines) is required", text
    if needle not in text:
        return f"{path}:{ref.get('lines')}: text {needle!r} is not in those lines at {label(base)}", text
    return None, text


# Probes that take a tool's verdict on a value they hand it (HQ 2026-11-16): a mismatch control is mandatory.
TOOL_VERDICT = [
    (re.compile(r"\bopenssl\s+s_client\b"), "openssl s_client (TLS verdict)"),
    (re.compile(r"\bcurl\b[^\n]*(-H\s*['\"]?Host:|--resolve\b)"), "curl by host (HTTP verdict for a vhost)"),
    (re.compile(r"(^|[\s;&|(])ssh\s[^\n]*(\S+@\S+|-o\s*(Ciphers|KexAlgorithms|MACs|HostKeyAlgorithms|"
                r"PubkeyAuthentication|PasswordAuthentication|PreferredAuthentications)=)"), "ssh login/negotiation"),
    (re.compile(r"\b(su|runuser)\s+-|\bsudo\s+-u\s"), "a login as another user"),
    (re.compile(r"\b(mysql|psql|smbclient|ldapsearch)\b[^\n]*\s-[uUD]\s*\S"), "a client login with a user"),
]


def tool_verdict(probe: str) -> str | None:
    return next((why for pat, why in TOOL_VERDICT if pat.search(probe)), None)


DEFER_NEEDS = ("second-node", "browser", "rhel", "desktop")
NEED_CAPABILITY = {"desktop": "desktop", "browser": "desktop", "second-node": "second-node", "rhel": "rhel-subscription"}


def lifting_problems(kind, need: str | None, where: str) -> list[str]:
    """A node kind that lifts a deferral or an uncovered note must exist and (for a need) have its capability."""
    import nodes  # noqa: PLC0415
    inventory = nodes.load()["nodes"]
    if kind not in inventory:
        return [f"{where}: lifted_by {kind!r} is not a node kind of nodes.yml ({', '.join(inventory)})"]
    if need and NEED_CAPABILITY[need] not in inventory[kind]["capabilities"]:
        return [f"{where}: node {kind} lacks the capability {NEED_CAPABILITY[need]!r} that `{need}` needs"]
    return []
HOST_RULES = 3  # FORBIDDEN[:3] keep probes on the node and away from Puppet; the rest keep them read-only


def probe_problems(probe: str, mutating: bool = False) -> list[str]:
    rules = FORBIDDEN[:HOST_RULES] if mutating else FORBIDDEN
    out = [f"probe {why}: {pat.pattern}" for pat, why in rules if pat.search(probe)]
    if LOCAL_SSH.search(probe) and not LOCAL_TARGET.search(probe):
        out.append("probe uses ssh to a host other than the node itself (127.0.0.1/localhost)")
    return out


def validate(cls: str) -> tuple[list[str], dict, bytes]:
    data, raw = load_set(cls)
    problems: list[str] = []
    base = baseline.for_class(cls)
    if data.get("class") != cls:
        problems.append(f"class {data.get('class')!r} != file name {cls!r}")
    if data.get("baseline") != label(base):
        problems.append(f"baseline {data.get('baseline')!r} != the class's baseline {label(base)!r}")
    minutes = (data.get("authoring") or {}).get("minutes")
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        problems.append("authoring.minutes (authoring time, minutes) is required")
    for i, u in enumerate(data.get("uncovered") or []):
        if not isinstance(u, dict) or set(u) != {"what", "why", "lifted_by"} or len(str(u.get("why", ""))) < 20:
            problems.append(f"uncovered[{i}] takes what, why (>= 20 characters) and lifted_by")
        else:
            problems += lifting_problems(u["lifted_by"], None, f"uncovered[{i}]")
    if "deferred" in data:
        d = data["deferred"]
        if not isinstance(d, dict) or d.get("needs") not in DEFER_NEEDS or len(str(d.get("why", "")).strip()) < 20:
            problems.append(f"deferred needs `needs` ({'|'.join(DEFER_NEEDS)}) and a `why` of at least 20 characters")
        if "checks" in data:
            problems.append("a deferred set has no checks")
        if isinstance(d, dict) and d.get("needs") in DEFER_NEEDS:
            problems += lifting_problems(d.get("lifted_by"), d["needs"], "deferred")
        refs = data.get("derived_from")
        if not isinstance(refs, list) or not refs:
            problems.append("a deferral cites the baseline lines that make it necessary (derived_from)")
        else:
            problems += [p for p, _ in (resolve_ref(r, base) for r in refs) if p]
        return problems, data, raw
    if data.get("fixture") not in ("params", "defaults"):
        problems.append("fixture must be `params` or `defaults`")
    params = PARAMS_DIR / f"puppet_infrastructure::{cls}.json"
    if data.get("fixture") == "params" and not params.is_file():
        problems.append(f"fixture: params but {params} is missing")
    if data.get("fixture") == "defaults" and params.is_file():
        problems.append(f"fixture: defaults but {params} exists (the harness would apply it)")
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        return problems + ["no checks"], data, raw
    ids = set()
    for i, c in enumerate(checks):
        where = f"check {c.get('id', i) if isinstance(c, dict) else i}"
        if not isinstance(c, dict):
            problems.append(f"{where}: not a mapping")
            continue
        if not SLUG.fullmatch(str(c.get("id", ""))) or c["id"] in ids:
            problems.append(f"{where}: id must be a unique slug")
        ids.add(c.get("id"))
        if not c.get("what"):
            problems.append(f"{where}: `what` is required")
        if c.get("control") not in ("negative", "invariant"):
            problems.append(f"{where}: control must be negative|invariant")
        if c.get("control") == "invariant" and not c.get("why_invariant"):
            problems.append(f"{where}: an invariant needs why_invariant")
        refs = c.get("derived_from")
        if not isinstance(refs, list) or not refs:
            problems.append(f"{where}: derived_from (baseline references) is required")
        else:
            problems += [f"{where}: {p}" for p, _ in (resolve_ref(r, base) for r in refs) if p]
        mutating = "mutates" in c
        if not isinstance(c.get("probe"), str) or not c["probe"].strip():
            problems.append(f"{where}: probe is required")
        else:
            problems += [f"{where}: {p}" for p in probe_problems(c["probe"], mutating)]
        if mutating:
            if not isinstance(c["mutates"], str) or len(c["mutates"].strip()) < 10:
                problems.append(f"{where}: mutates must declare what the action changes")
            if not isinstance(c.get("effect"), str) or not c["effect"].strip():
                problems.append(f"{where}: a mutating check needs a read-only `effect` probe (the evidence)")
            else:
                problems += [f"{where}: effect {p}" for p in probe_problems(c["effect"])]
            if c.get("control") != "negative":
                problems.append(f"{where}: a mutating check is a negative control (its effect must be absent "
                                "on the clean node)")
        elif "effect" in c:
            problems.append(f"{where}: `effect` without `mutates` (declare the change to opt in)")
        mm = c.get("mismatch")
        verdict_of = tool_verdict(c["probe"]) if isinstance(c.get("probe"), str) and not mutating else None
        if mm is None and verdict_of:
            problems.append(f"{where}: the probe takes a tool's verdict ({verdict_of}); a `mismatch` control is "
                            "mandatory (HQ 2026-11-16)")
        if mm is not None:
            if mutating:
                problems.append(f"{where}: a mutating check takes no mismatch control (its evidence is the effect)")
            elif not isinstance(mm, dict) or set(mm) != {"varies", "probe"}:
                problems.append(f"{where}: mismatch takes exactly `varies` and `probe`")
            else:
                if not isinstance(mm["varies"], str) or len(mm["varies"].strip()) < 10:
                    problems.append(f"{where}: mismatch.varies must say which value is wrong and why")
                if not isinstance(mm["probe"], str) or not mm["probe"].strip():
                    problems.append(f"{where}: mismatch.probe is required")
                else:
                    if mm["probe"].strip() == str(c.get("probe", "")).strip():
                        problems.append(f"{where}: mismatch.probe is identical to the probe")
                    problems += [f"{where}: mismatch {p}" for p in probe_problems(mm["probe"])]
        exp = c.get("expect") or {}
        if not isinstance(exp, dict) or not set(exp) <= {"rc", "stdout", "stdout_not"}:
            problems.append(f"{where}: expect takes rc, stdout, stdout_not")
        else:
            for key in ("stdout", "stdout_not"):
                if key in exp:
                    try:
                        re.compile(exp[key], re.M)
                    except (re.error, TypeError) as err:
                        problems.append(f"{where}: expect.{key} is not a regex ({err})")
    if not any(isinstance(c, dict) and c.get("control") == "negative" for c in checks):
        problems.append("no negative control: at least one check must fail on the clean node")
    return problems, data, raw


def cmd_validate(cls: str) -> int:
    problems, data, _ = validate(cls)
    for p in problems:
        print(f"INVALID {cls}: {p}", file=sys.stderr)
    if problems:
        return 2
    if "deferred" in data:
        print(f"VALID {cls}: DEFERRED (needs {data['deferred']['needs']}, lifted by {data['deferred']['lifted_by']}): "
              f"{data['deferred']['why']}")
        return 0
    neg = sum(1 for c in data["checks"] if c["control"] == "negative")
    mut = sum(1 for c in data["checks"] if "mutates" in c)
    mism = sum(1 for c in data["checks"] if "mismatch" in c)
    print(f"VALID {cls}: {len(data['checks'])} checks ({neg} negative controls, {mut} mutating, {mism} mismatch), "
          f"{sum(len(c['derived_from']) for c in data['checks'])} baseline references at {data['baseline']}")
    return 0


# ------------------------------------------------------------------ run

def node_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{TOOLS / 'sshmux'}:{env['PATH']}"  # one multiplexed connection, like the harness
    return env


def on_node(script: str) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(["ssh", "-o", "BatchMode=yes", NODE, "sudo -n bash -s"], input=script,
                              capture_output=True, text=True, timeout=PROBE_TIMEOUT, env=node_env())
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"probe timed out after {PROBE_TIMEOUT}s"


def meets(check: dict, rc: int, out: str) -> bool:
    exp = check.get("expect") or {}
    passed = rc == exp.get("rc", 0)
    if passed and "stdout" in exp:
        passed = re.search(exp["stdout"], out, re.M) is not None
    if passed and "stdout_not" in exp:
        passed = re.search(exp["stdout_not"], out, re.M) is None
    return passed


def run_mismatch(check: dict, row: dict) -> None:
    """After a passing check: the deliberately wrong variant must NOT meet the same expectation."""
    mm = check.get("mismatch")
    if not mm:
        return
    if not row["passed"]:
        row["mismatch"] = {"varies": mm["varies"], "not_run": "the check itself failed"}
        return
    rc, out, err = on_node(mm["probe"])
    row["mismatch"] = {"varies": mm["varies"], "rc": rc, "passed": meets(check, rc, out),
                       "stdout": out[-1000:], "stderr": err[-500:]}


def run_probe(check: dict, act: bool = False) -> dict:
    """Read-only checks run `probe`. A mutating check runs its `effect` only — preceded by the action when `act`."""
    action = None
    if "mutates" in check and act:
        arc, aout, aerr = on_node(check["probe"])
        action = {"mutates": check["mutates"], "rc": arc, "stdout": aout[-1000:], "stderr": aerr[-500:]}
    rc, out, err = on_node(check["effect"] if "mutates" in check else check["probe"])
    passed = meets(check, rc, out)
    row = {"id": check["id"], "control": check["control"], "rc": rc, "passed": passed,
           "stdout": out[-2000:], "stderr": err[-1000:]}
    if "mutates" in check:
        row["mutating"] = True
        row["action"] = action  # None in the clean phase: the action never runs before the class is applied
    return row


def git_head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def junit(cls: str, record: dict) -> bytes:
    suites = ET.Element("testsuites", name=f"phase3.{cls}")
    for phase, rows, rule in (("clean", record["clean"], "control"), ("applied", record["applied"], "pass")):
        suite = ET.SubElement(suites, "testsuite", name=f"phase3.{cls}.{phase}", tests=str(len(rows)))
        bad = 0
        for r in rows:
            case = ET.SubElement(suite, "testcase", classname=f"phase3.{cls}.{phase}", name=r["id"])
            if r.get("not_run"):
                ET.SubElement(case, "skipped", message=r["not_run"])
                continue
            if rule == "control":
                ok, msg = r["ok"], ("negative control passed on the clean node" if r["control"] == "negative"
                                    else "invariant failed on the clean node")
            else:
                ok, msg = r["passed"], "check failed after the class was applied (finding)"
            if not ok:
                bad += 1
                ET.SubElement(case, "failure", message=msg).text = f"rc {r['rc']}\n{r['stdout']}\n{r['stderr']}"
            mm = r.get("mismatch") if phase == "applied" else None
            if mm:
                mcase = ET.SubElement(suite, "testcase", classname=f"phase3.{cls}.applied", name=f"{r['id']}.mismatch")
                suite.set("tests", str(int(suite.get("tests")) + 1))
                if mm.get("not_run"):
                    ET.SubElement(mcase, "skipped", message=mm["not_run"])
                elif mm["passed"]:
                    bad += 1
                    ET.SubElement(mcase, "failure", message=f"mismatch control passed ({mm['varies']}): the check "
                                  "does not discriminate").text = f"rc {mm['rc']}\n{mm['stdout']}"
        suite.set("failures", str(bad))
        if phase == "applied" and not rows:
            ET.SubElement(suite, "testcase", classname=f"phase3.{cls}.applied", name="not-run").append(
                ET.Element("skipped", message=record["outcome"]))
    return ET.tostring(suites, encoding="utf-8", xml_declaration=True)


def write_outputs(cls: str, record: dict) -> Path:
    out = phase3_dir() / "results" / cls
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"{record['at']}-{record['role']}"
    stem.with_suffix(".json").write_text(json.dumps(record, indent=1) + "\n")
    stem.with_suffix(".xml").write_bytes(junit(cls, record))
    return stem


def cmd_run(cls: str, role: str) -> int:
    started = now()
    problems, data, raw = validate(cls)
    record = {"class": cls, "role": role, "at": started, "runner": git_head(), "baseline": data.get("baseline"),
              "check_file_sha256": hashlib.sha256(raw).hexdigest(), "valid": not problems, "problems": problems,
              "clean": [], "apply": None, "applied": [], "findings": [], "not_run": [], "outcome": None}

    t0 = time.monotonic()
    record["authoring_minutes"] = (data.get("authoring") or {}).get("minutes")

    def finish(outcome: str, rc: int) -> int:
        record["outcome"] = outcome
        record["duration_s"] = round(time.monotonic() - t0, 1)
        stem = write_outputs(cls, record)
        shown = stem.relative_to(REPO) if stem.is_relative_to(REPO) else stem
        print(f"PHASE3 {outcome} {cls}: {shown}.json (+ .xml)")
        return rc

    if problems:
        for p in problems:
            print(f"INVALID {cls}: {p}", file=sys.stderr)
        return finish("INVALID_SET", 2)
    if "deferred" in data:
        print(f"DEFERRED {cls}: needs {data['deferred']['needs']}; nothing to run", file=sys.stderr)
        return 2
    # One lab run at a time (lab_lock.sh), held across the revert, both probe phases and the apply.
    lock = subprocess.run([str(TOOLS / "lab_lock.sh"), "take", str(os.getpid()), f"phase3.py run {cls} {role}"],
                          capture_output=True, text=True)
    if lock.returncode != 0:
        record["problems"].append(f"another lab run holds the lab lock: {lock.stderr.strip()}")
        print(f"REFUSED: another lab run holds the lab lock ({lock.stderr.strip()})", file=sys.stderr)
        return finish("ENVIRONMENT_FAILED", 3)
    os.environ["P8_LAB_LOCKED"] = "1"
    global NODE
    import nodes  # noqa: PLC0415
    node = nodes.select(nodes.load(), cls=cls)
    NODE, record["node"] = node["alias"], node["kind"]
    try:
        return run_locked(cls, data, record, finish)
    finally:
        subprocess.run([str(TOOLS / "lab_lock.sh"), "release", str(os.getpid())], capture_output=True)


def run_locked(cls: str, data: dict, record: dict, finish) -> int:
    revert = os.environ.get("P8_PHASE3_REVERT") or str(TOOLS / "revert_node.sh")
    print("==> Reverting the node (clean phase runs on the baseline)")
    rv = subprocess.run([revert, "--node", record["node"]], env=node_env(), capture_output=True, text=True)
    print(rv.stdout, end="")
    print(rv.stderr, end="", file=sys.stderr)
    if rv.returncode != 0:
        err = [l for l in (rv.stderr or rv.stdout).splitlines() if l.strip()][-1:] or ["(no output)"]
        record["problems"].append(f"node revert failed: {err[0]}")
        return finish("ENVIRONMENT_FAILED", 3)
    print("==> CLEAN phase: negative controls must fail, invariants must pass (mutating checks: effect only)")
    for check in data["checks"]:
        r = run_probe(check)
        r["ok"] = (not r["passed"]) if check["control"] == "negative" else r["passed"]
        record["clean"].append(r)
        print(f"  {'ok ' if r['ok'] else 'BAD'} {check['id']} ({check['control']}: "
              f"{'passed' if r['passed'] else 'failed'} on the clean node)")
    bad = [r["id"] for r in record["clean"] if not r["ok"]]
    if bad:
        record["valid"] = False
        record["problems"].append(f"controls did not hold on the clean node: {', '.join(bad)}")
        return finish("INVALID_SET", 2)
    harness = os.environ.get("P8_PHASE3_HARNESS") or str(TOOLS / "test_class.sh")
    print(f"==> Applying {cls} with the gate-v2 harness on the fresh node")
    env = node_env()
    env["P8_METRICS_DIR"] = str(REPO / ".codex_state" / "logs" / "phase3-metrics")
    proc = subprocess.run([harness, f"puppet_infrastructure::{cls}"], capture_output=True, text=True, env=env)
    green = proc.returncode == 0 and "GREEN:" in proc.stdout
    record["apply"] = {"rc": proc.returncode, "green": green,
                       "node_fresh": "NODE_FRESH: yes" in proc.stdout,
                       "tail": (proc.stdout + proc.stderr)[-1500:]}
    if not green:
        return finish("APPLY_FAILED", 3)
    print("==> APPLIED phase: every check must pass (read-only first; mutating only if all of those pass)")
    readonly = [c for c in data["checks"] if "mutates" not in c]
    mutating = [c for c in data["checks"] if "mutates" in c]
    for check in readonly:
        r = run_probe(check)
        run_mismatch(check, r)
        record["applied"].append(r)
        mm = r.get("mismatch") or {}
        note = ""
        if mm:
            state = "not run" if mm.get("not_run") else "PASSED: does not discriminate" if mm["passed"] \
                else "failed as required"
            note = f"; mismatch {state}"
        print(f"  {'pass' if r['passed'] else 'FAIL'} {check['id']}{note}")
    weak = [r["id"] for r in record["applied"] if (r.get("mismatch") or {}).get("passed")]
    if weak:
        record["valid"] = False
        record["problems"].append(f"mismatch controls passed (checks do not discriminate): {', '.join(weak)}")
        for check in mutating:
            record["applied"].append({"id": check["id"], "control": check["control"], "mutating": True,
                                      "passed": False, "not_run": "not run: the set is invalid", "rc": None,
                                      "stdout": "", "stderr": ""})
        return finish("INVALID_SET", 2)
    gate = [r["id"] for r in record["applied"] if not r["passed"]]
    for check in mutating:
        if gate:
            reason = f"not run: read-only checks failed ({', '.join(gate)})"
            record["applied"].append({"id": check["id"], "control": check["control"], "mutating": True,
                                      "passed": False, "not_run": reason, "rc": None, "stdout": "", "stderr": ""})
            print(f"  SKIP {check['id']} (mutating; {reason})")
            continue
        r = run_probe(check, act=True)
        record["applied"].append(r)
        print(f"  {'pass' if r['passed'] else 'FAIL'} {check['id']} (mutating: {check['mutates']}; "
              f"action rc {r['action']['rc']}, judged on the effect)")
    record["not_run"] = [r["id"] for r in record["applied"] if r.get("not_run")]
    record["findings"] = [r["id"] for r in record["applied"] if not r["passed"] and not r.get("not_run")]
    if record["findings"] or record["not_run"]:
        return finish("FINDINGS", 1)
    return finish("ALL_PASS", 0)


# ------------------------------------------------------------------ reviewer: spot + verdict

def cmd_spot(cls: str, n: int, seed: int | None) -> int:
    problems, data, _ = validate(cls)
    if problems:
        print(f"INVALID {cls}: the set does not validate; spot-check nothing", file=sys.stderr)
        return 2
    base = baseline.for_class(cls)
    if "deferred" in data:
        d = data["deferred"]
        print(f"SPOT {cls}: DEFERRAL — needs {d['needs']}, lifted by node kind {d['lifted_by']}, baseline {label(base)}")
        print(f"stated reason: {d['why']}")
        for r in data["derived_from"]:
            _, text = resolve_ref(r, base)
            print(f"\nreference: {r['path']}" + (f":{r['lines']}" if "lines" in r else " (whole file)"))
            print("\n".join(f"  | {l}" for l in text.splitlines()))
        print("\nJudge: do these baseline lines make the behaviour impossible to observe on this lab's node, as stated,"
              " and would the named node kind lift it?")
        return 0
    refs = [(c, r) for c in data["checks"] for r in c["derived_from"]]
    seed = seed if seed is not None else random.SystemRandom().randrange(1 << 30)
    picked = random.Random(seed).sample(refs, min(n, len(refs)))
    print(f"SPOT {cls}: {len(picked)} of {len(refs)} references (seed {seed}), baseline {label(base)}")
    params = PARAMS_DIR / f"puppet_infrastructure::{cls}.json"
    print(f"fixture: {data['fixture']}" + (f" ({params})" if data["fixture"] == "params" else ""))
    for c, r in picked:
        _, text = resolve_ref(r, base)
        print(f"\n--- check {c['id']} ({c['control']}): {c['what']}")
        print(f"reference: {r['path']}" + (f":{r['lines']}" if "lines" in r else " (whole file)"))
        print("baseline lines (read now from the upstream pin):")
        print("\n".join(f"  | {l}" for l in text.splitlines()))
        if "mutates" in c:
            print(f"MUTATING — declared change: {c['mutates']}")
            print("action:\n" + "\n".join(f"  $ {l}" for l in c["probe"].strip().splitlines()))
            print("effect (evidence; expect applies here):\n" +
                  "\n".join(f"  $ {l}" for l in c["effect"].strip().splitlines()))
        else:
            print("probe:\n" + "\n".join(f"  $ {l}" for l in c["probe"].strip().splitlines()))
        if "mismatch" in c:
            print(f"MISMATCH control (must FAIL the same expect) — varies: {c['mismatch']['varies']}\n" +
                  "\n".join(f"  $ {l}" for l in c["mismatch"]["probe"].strip().splitlines()))
        print(f"expect: {json.dumps(c.get('expect') or {'rc': 0})}")
    print("\nJudge each: does the probe + expect test what these baseline lines declare, under the fixture?")
    return 0


def latest(cls: str, role: str) -> dict | None:
    files = sorted((phase3_dir() / "results" / cls).glob(f"*-{role}.json"))
    return json.loads(files[-1].read_text()) if files else None


def outcomes(record: dict) -> dict:
    return {"valid": record["valid"], "clean": {r["id"]: r["passed"] for r in record["clean"]},
            "applied": {r["id"]: r["passed"] for r in record["applied"]},
            "mismatch": {r["id"]: r["mismatch"].get("passed") for r in record["applied"] if r.get("mismatch")}}


def cmd_verdict(cls: str, derived: str, evidence: list[str]) -> int:
    if derived not in ("ok", "fail") or not evidence:
        raise SystemExit("ERROR: verdict needs --derived ok|fail and at least one --evidence")
    problems, data, raw = validate(cls)
    if "deferred" in data:  # no runs to reproduce: the reviewer judges the stated reason against the cited lines
        checks = {"deferral_valid": "fail" if problems else "ok", "derived_from": derived}
        verdict = "PASS" if all(v == "ok" for v in checks.values()) else "FAIL"
        record = {"class": cls, "at": now(), "verdict": verdict, "deferral": True, "checks": checks,
                  "evidence": evidence, "check_file_sha256": hashlib.sha256(raw).hexdigest(), "findings": [],
                  "review_s": None}
        out = phase3_dir() / "reviews" / cls
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{record['at']}.json"
        path.write_text(json.dumps(record, indent=1) + "\n")
        print(f"VERDICT {verdict}\nclass {cls}\ndeferral {data['deferred']['needs']} (lifted by "
              f"{data['deferred']['lifted_by']})\nchecks {json.dumps(checks)}")
        for e in evidence:
            print(f"evidence {e}")
        print(f"persisted {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")
        return 0 if verdict == "PASS" else 1
    mine, theirs = latest(cls, "reviewer"), latest(cls, "author")
    checks = {}
    checks["reviewer_run"] = "ok" if mine and mine["valid"] and mine["outcome"] in ("ALL_PASS", "FINDINGS") else "fail"
    checks["author_run"] = "ok" if theirs and theirs["valid"] and theirs["outcome"] in ("ALL_PASS", "FINDINGS") \
        else "fail"
    same = bool(mine and theirs) and outcomes(mine) == outcomes(theirs) \
        and mine["check_file_sha256"] == theirs["check_file_sha256"]
    checks["reproduced"] = "ok" if same else "fail"
    checks["derived_from"] = derived
    verdict = "PASS" if all(v == "ok" for v in checks.values()) else "FAIL"
    started = dt.datetime.strptime(mine["at"], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc) if mine else None
    review_s = round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 1) if started else None
    record = {"class": cls, "at": now(), "verdict": verdict, "checks": checks, "evidence": evidence,
              "review_s": review_s, "check_file_sha256": mine and mine["check_file_sha256"],
              "reviewer_result": mine and f"{mine['at']}-reviewer", "author_result": theirs and f"{theirs['at']}-author",
              "findings": (mine or {}).get("findings", [])}
    out = phase3_dir() / "reviews" / cls
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{record['at']}.json"
    path.write_text(json.dumps(record, indent=1) + "\n")
    print(f"VERDICT {verdict}\nclass {cls}\nchecks {json.dumps(checks)}\nfindings {record['findings']}")
    for e in evidence:
        print(f"evidence {e}")
    print(f"persisted {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")
    if verdict == "PASS" and record["findings"]:
        print(f"FINDINGS reproduced: write .codex_state/escalations/{cls}.behaviour.md with the evidence")
    return 0 if verdict == "PASS" else 1


# ------------------------------------------------------------------ behaviour state (derived)

def latest_review(cls: str) -> dict | None:
    files = sorted((phase3_dir() / "reviews" / cls).glob("*.json"))
    return json.loads(files[-1].read_text()) if files else None


def behaviour_state(cls: str) -> dict:
    """Derived (P2) from .codex_state/checks: the check file, the latest results and the latest phase-3 review."""
    row = {"class": cls, "state": "none", "detail": "", "authoring_min": None, "author_run_s": None,
           "reviewer_run_s": None, "review_s": None}
    if not (phase3_dir() / f"{cls}.yml").is_file():
        return row
    problems, data, raw = validate(cls)
    row["authoring_min"] = (data.get("authoring") or {}).get("minutes")
    if problems:
        return {**row, "state": "invalid", "detail": problems[0]}
    if "deferred" in data:
        review = latest_review(cls)
        d = data["deferred"]
        if not review or review.get("check_file_sha256") != hashlib.sha256(raw).hexdigest():
            return {**row, "state": "unreviewed", "detail": f"deferral ({d['needs']}) not yet judged by the reviewer"}
        if review["verdict"] != "PASS":
            return {**row, "state": "review-failed", "detail": "deferral rejected"}
        return {**row, "state": "deferred", "detail": f"{d['needs']}, lifted by {d['lifted_by']}"}
    author, reviewer, review = latest(cls, "author"), latest(cls, "reviewer"), latest_review(cls)
    row["author_run_s"] = (author or {}).get("duration_s")
    row["reviewer_run_s"] = (reviewer or {}).get("duration_s")
    row["review_s"] = (review or {}).get("review_s")
    if not review:
        return {**row, "state": "unreviewed", "detail": (author or {}).get("outcome") or "not run"}
    sha = hashlib.sha256(raw).hexdigest()
    reviewed_sha = review.get("check_file_sha256") or (reviewer or {}).get("check_file_sha256")
    if reviewed_sha != sha:
        return {**row, "state": "stale", "detail": "the check file changed after its review"}
    if review["verdict"] != "PASS":
        failed = ", ".join(k for k, v in review["checks"].items() if v != "ok")
        return {**row, "state": "review-failed", "detail": failed}
    if review.get("findings"):
        esc = REPO / ".codex_state" / "escalations" / f"{cls}.behaviour.md"
        detail = ", ".join(review["findings"]) + ("" if esc.is_file() else " — NO ESCALATION FILE")
        return {**row, "state": "finding", "detail": detail}
    return {**row, "state": "pass"}


def cmd_state(classes: list[str]) -> int:
    if not classes:
        classes = sorted(p.stem for p in phase3_dir().glob("*.yml"))
    rows = [behaviour_state(c) for c in classes]
    m = lambda v, unit: "–" if v is None else f"{v:g}{unit}"  # noqa: E731
    print("| class | behaviour | detail | authoring | author run | reviewer run | review |")
    print("|---|---|---|---:|---:|---:|---:|")
    for r in rows:
        print(f"| {r['class']} | {r['state']} | {r['detail']} | {m(r['authoring_min'], ' min')} | "
              f"{m(r['author_run_s'], ' s')} | {m(r['reviewer_run_s'], ' s')} | {m(r['review_s'], ' s')} |")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print("\n" + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())))
    return 0


def main(argv: list[str]) -> int:
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    if len(argv) == 2 and argv[0] == "validate":
        return cmd_validate(short(argv[1]))
    if len(argv) >= 2 and argv[0] == "run":
        role = opt("--role", "author")
        if role not in ("author", "reviewer"):
            raise SystemExit("ERROR: --role author|reviewer")
        return cmd_run(short(argv[1]), role)
    if len(argv) >= 2 and argv[0] == "spot":
        return cmd_spot(short(argv[1]), int(opt("--n", "3")), int(opt("--seed")) if "--seed" in argv else None)
    if argv[:1] == ["state"]:
        return cmd_state([short(c) for c in argv[1:]])
    if len(argv) >= 2 and argv[0] == "verdict":
        evidence = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--evidence"]
        return cmd_verdict(short(argv[1]), opt("--derived", ""), evidence)
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
