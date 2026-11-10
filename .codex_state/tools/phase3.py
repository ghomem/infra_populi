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
  phase3.py verdict <class> --derived ok|fail --evidence TEXT [--evidence ...]
                                 reviewer: compares its latest run with the latest author run (same validity, same
                                 per-check outcome on both phases) and persists .codex_state/checks/reviews/<class>/
                                 <UTC>.json. PASS = both runs valid + reproduced + derived ok.

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

Probe rules (validate): the node is the only host — no other host name or address, no ssh/scp/sftp/rsync except to
the node itself (127.0.0.1/localhost); read-only — no puppet agent/apply/resource, no service or package state
change, no rm/tee/redirect into a file.
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
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import baseline  # noqa: E402

NODE = "puppet8node"
PROBE_TIMEOUT = 120
PARAMS_DIR = Path(os.environ.get("P8_PARAMS_DIR") or Path.home() / ".config" / "infra_populi" / "params")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{1,62}")
FORBIDDEN = [
    (re.compile(r"puppet8master|puppet8node|example\.com:8140|\b192\.168\.\d+\.\d+"), "names another lab host"),
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
    data = yaml.safe_load(raw)
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


def probe_problems(probe: str) -> list[str]:
    out = [f"probe {why}: {pat.pattern}" for pat, why in FORBIDDEN if pat.search(probe)]
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
    if data.get("fixture") not in ("params", "defaults"):
        problems.append("fixture must be `params` or `defaults`")
    params = PARAMS_DIR / f"puppet_infrastructure::{cls}.json"
    if data.get("fixture") == "params" and not params.is_file():
        problems.append(f"fixture: params but {params} is missing")
    if data.get("fixture") == "defaults" and params.is_file():
        problems.append(f"fixture: defaults but {params} exists (the harness would apply it)")
    minutes = (data.get("authoring") or {}).get("minutes")
    if not isinstance(minutes, (int, float)) or minutes <= 0:
        problems.append("authoring.minutes (authoring time, minutes) is required")
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
        if not isinstance(c.get("probe"), str) or not c["probe"].strip():
            problems.append(f"{where}: probe is required")
        else:
            problems += [f"{where}: {p}" for p in probe_problems(c["probe"])]
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
    neg = sum(1 for c in data["checks"] if c["control"] == "negative")
    print(f"VALID {cls}: {len(data['checks'])} checks ({neg} negative controls), "
          f"{sum(len(c['derived_from']) for c in data['checks'])} baseline references at {data['baseline']}")
    return 0


# ------------------------------------------------------------------ run

def node_env() -> dict:
    env = dict(os.environ)
    env["PATH"] = f"{TOOLS / 'sshmux'}:{env['PATH']}"  # one multiplexed connection, like the harness
    return env


def run_probe(check: dict) -> dict:
    try:
        proc = subprocess.run(["ssh", "-o", "BatchMode=yes", NODE, "sudo -n bash -s"], input=check["probe"],
                              capture_output=True, text=True, timeout=PROBE_TIMEOUT, env=node_env())
        rc, out, err = proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        rc, out, err = 124, "", f"probe timed out after {PROBE_TIMEOUT}s"
    exp = check.get("expect") or {}
    passed = rc == exp.get("rc", 0)
    if passed and "stdout" in exp:
        passed = re.search(exp["stdout"], out, re.M) is not None
    if passed and "stdout_not" in exp:
        passed = re.search(exp["stdout_not"], out, re.M) is None
    return {"id": check["id"], "control": check["control"], "rc": rc, "passed": passed,
            "stdout": out[-2000:], "stderr": err[-1000:]}


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
            if rule == "control":
                ok, msg = r["ok"], ("negative control passed on the clean node" if r["control"] == "negative"
                                    else "invariant failed on the clean node")
            else:
                ok, msg = r["passed"], "check failed after the class was applied (finding)"
            if not ok:
                bad += 1
                ET.SubElement(case, "failure", message=msg).text = f"rc {r['rc']}\n{r['stdout']}\n{r['stderr']}"
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
              "clean": [], "apply": None, "applied": [], "findings": [], "outcome": None}

    def finish(outcome: str, rc: int) -> int:
        record["outcome"] = outcome
        stem = write_outputs(cls, record)
        shown = stem.relative_to(REPO) if stem.is_relative_to(REPO) else stem
        print(f"PHASE3 {outcome} {cls}: {shown}.json (+ .xml)")
        return rc

    if problems:
        for p in problems:
            print(f"INVALID {cls}: {p}", file=sys.stderr)
        return finish("INVALID_SET", 2)
    revert = os.environ.get("P8_PHASE3_REVERT") or str(TOOLS / "revert_node.sh")
    print("==> Reverting the node (clean phase runs on the baseline)")
    if subprocess.run([revert], env=node_env()).returncode != 0:
        record["problems"].append("node revert failed")
        return finish("ENVIRONMENT_FAILED", 3)
    print("==> CLEAN phase: negative controls must fail, invariants must pass")
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
    print("==> APPLIED phase: every check must pass")
    for check in data["checks"]:
        r = run_probe(check)
        record["applied"].append(r)
        print(f"  {'pass' if r['passed'] else 'FAIL'} {check['id']}")
    record["findings"] = [r["id"] for r in record["applied"] if not r["passed"]]
    if record["findings"]:
        return finish("FINDINGS", 1)
    return finish("ALL_PASS", 0)


# ------------------------------------------------------------------ reviewer: spot + verdict

def cmd_spot(cls: str, n: int, seed: int | None) -> int:
    problems, data, _ = validate(cls)
    if problems:
        print(f"INVALID {cls}: the set does not validate; spot-check nothing", file=sys.stderr)
        return 2
    base = baseline.for_class(cls)
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
        print("probe:\n" + "\n".join(f"  $ {l}" for l in c["probe"].strip().splitlines()))
        print(f"expect: {json.dumps(c.get('expect') or {'rc': 0})}")
    print("\nJudge each: does the probe + expect test what these baseline lines declare, under the fixture?")
    return 0


def latest(cls: str, role: str) -> dict | None:
    files = sorted((phase3_dir() / "results" / cls).glob(f"*-{role}.json"))
    return json.loads(files[-1].read_text()) if files else None


def outcomes(record: dict) -> dict:
    return {"valid": record["valid"], "clean": {r["id"]: r["passed"] for r in record["clean"]},
            "applied": {r["id"]: r["passed"] for r in record["applied"]}}


def cmd_verdict(cls: str, derived: str, evidence: list[str]) -> int:
    if derived not in ("ok", "fail") or not evidence:
        raise SystemExit("ERROR: verdict needs --derived ok|fail and at least one --evidence")
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
    record = {"class": cls, "at": now(), "verdict": verdict, "checks": checks, "evidence": evidence,
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
    return 0 if verdict == "PASS" else 1


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
    if len(argv) >= 2 and argv[0] == "verdict":
        evidence = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--evidence"]
        return cmd_verdict(short(argv[1]), opt("--derived", ""), evidence)
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
