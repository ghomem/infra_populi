#!/usr/bin/env python3
"""Phase 3 check runner (HQ batch-3 acceptance B; ruling 11 of 2026-10-27): behaviour checks for a migrated class,
derived from the pinned baseline, probed on the node only, with negative controls that must fail on the clean node.

  phase3.py validate <class>     the check file alone (no node): schema, derived_from against the class's baseline,
                                 probe rules. Exit 0 valid, 2 invalid.
  phase3.py run <class> [--role author|reviewer]
                                 validate; then, under the lab lock, the run itself through the public runner
                                 (spec/behaviour/run) with the lab as its provider (behaviour_lab.py; HQ review of the
                                 behaviour suite, ruling 2): revert the node; CLEAN phase (every probe on the reverted
                                 node: each `negative` control must FAIL, each `invariant` must PASS, else the set is
                                 INVALID); apply the class with the gate-v2 harness on that fresh node, after checking
                                 it renders exactly the runner's manifest; APPLIED phase (every check must PASS; a
                                 failure is a FINDING). The runner's record becomes the engine's result (envelope,
                                 outcomes table): JSON + JUnit XML in .codex_state/checks/results/<class>/<UTC>-<role>.
                                 Exit 0 all pass, 1 findings, 2 invalid set, 3 apply/environment failure.
  phase3.py spot <class> [--n N] [--seed S]
                                 reviewer: N random derived_from references (default 3), each printed with the
                                 baseline lines read fresh from the upstream pin, beside the check's probe/expect.
  phase3.py sweep                approved, unchanged sets whose uncovered rows the HQ batch-15 ruling-3 rule would
                                 refuse, with the row count (the scheduled sweep)
  phase3.py state [<class> ...]  behaviour state per class (HQ 2026-11-16), DERIVED from the check, result and
                                 review files: pass | finding | deferred (<needs>) | none (no check file) |
                                 unreviewed | stale (check file changed after its review) | review-failed | invalid |
                                 unjudged (no stated purpose, or a review before the purpose judgement, HQ C1);
                                 with the author-run / reviewer-run / review times. A finding
                                 without .codex_state/escalations/<class>.behaviour.md is flagged.
  phase3.py verdict <class> --derived ok|fail --evidence TEXT [--evidence ...] --purpose covered|gap
                     --purpose-evidence TEXT
                                 reviewer: compares its latest run with the latest author run (same validity, same
                                 per-check outcome on both phases) and persists .codex_state/checks/reviews/<class>/
                                 <UTC>.json. PASS = both runs valid + reproduced + derived ok + every node of the
                                 reviewer's run fresh (HQ 2026-11-17 batch-8 ruling 3: the node and, for a set with a
                                 peer, the peer; both are recorded in the verdict).

A class that cannot be tested on this lab declares a DEFERRAL instead of checks (HQ 2026-11-16):
  class / baseline as below, plus
  deferred: {needs: second-node|browser|rhel|desktop, why: <one or two sentences>, lifted_by: <node kind>}
  derived_from: [<baseline references showing why, as for a check>]
The reviewer judges a deferral too (`--phase3`: `spot` prints the cited lines beside the reason, `verdict` records
it); it counts as `deferred` only once that review passed (HQ 2026-11-16 item 7b). `lifted_by` names a kind of
.codex_state/lab/nodes.yml with the needed capability (desktop/browser -> desktop, rhel -> a RedHat node,
second-node -> second-node). Any set may also list what it does NOT cover (item 7a):
  uncovered: [{what: <behaviour>, why: <why not here>, lifted_by: <node kind>}]

Check file spec/behaviour/checks/<class>.yml (the public suite's set, HQ review of design note F; the engine renders its
placeholders with the lab's values, behaviour_move.lab_view, and runs exactly the old probes):
  class: <short name>             # = the file name
  baseline: release-0.9.10 (cf477c6)   # = `baseline.py for <class>`
  fixture: params | defaults      # what the harness applies: the class's params file, or no params file at all
  purpose: <the class's purpose in one or two sentences, from its own header and code: what it is FOR, not what it
           declares> (HQ 2026-11-18 ruling C1; >= 40 characters). The reviewer judges whether the checks test it.
  outcomes:                       # HQ 2026-11-18 ruling 2: the purpose as observable outcomes, the reviewer's table
    - outcome: <what can be observed when the class does its job (>= 15 characters)>
      from: <where the baseline says so: manifests/x.pp:12-14, a template, a header comment>
      checks: [<id of a check that probes it>, ...]        # >= 1 existing check id, or instead:
      uncovered: {why: <why the lab does not probe it (>= 20 characters)>, lifted_by: <node kind that is not active,
                  or `capability: <what is missing>`>, evidence: <a command result, or the capability the node
                  inventory lacks (>= 20 characters)>}   # HQ batch-15 ruling 3; an approved, unchanged set keeps
                  # the earlier {why, lifted_by} until the sweep (`phase3.py sweep`)
      uncovered: {why: <...>, accepted_gap: [<parameter>, ...], evidence: <...>}
                  # HQ 2026-11-23 ruling 1c: a parameter variant no production node statement sets (each parameter
                  # 0 in diagnosis/fleet_variant_usage.md; a class of the unread passwd/ layer never qualifies). The
                  # approval report lists these for Salatiel's acceptance.
  variants:                       # optional (HQ 2026-11-23 ruling 1a): more runs of the same set, each a full run
    - name: <slug>                #   (revert, clean phase, apply, applied phase) recorded under `variants` in the
      why: <why this run exists (>= 20 characters)>  #   one result file; the result's outcome combines them all
      node: <another active node kind>               # the run's lab node (default: the plan's node), and/or
      params: <slug>              # the run's params fixture: params/variants/<slug>/puppet_infrastructure::<class>.json
      no_resources: true          # optional, with params: the variant's class declares nothing (the harness's coverage
                                  #   gate then reports the empty target instead of failing)
      # A check with `variant: <name>` runs only in that run (and needs >= 1 negative control there); a check without
      # it runs in the base run only. Variant runs have no peer, session or peer_agent; a node_agent anchor that is a
      # variant's check makes the agent run in that variant's run, on its node.
  checks:
    - id: <slug>
      what: <one line>
      control: negative | invariant          # negative: must FAIL on the clean node (mandatory: >= 1 per set)
      why_invariant: <why it also holds before the class>   # required for invariant
      derived_from:                          # >= 1; each must resolve at the class's baseline commit
        - {path: manifests/x.pp, lines: "12-14", text: "<exact substring of those lines>"}
        - {path: files/x, sha256: <of the whole baseline file>}
      probe: <shell, run as root on the node via `ssh <node> sudo -n bash -s`>
      # every node and peer script starts with spec/behaviour/probe_helpers.sh (HQ batch-12 ruling 6): p8_count, p8_listening,
      # p8_tcp, p8_http, p8_service, p8_digest, p8_rc, p8_tls, p8_established read; p8_hold (mutating) only in an action
      expect: {rc: 0, stdout: <regex, re.M>, stdout_not: <regex>}   # rc defaults to 0
      # opt-in MUTATING check (HQ 2026-11-10): `probe` is an action that changes the node; the evidence is its effect
      # (`timeout: N`, 1-600 s, lets the action outlast the 120 s probe limit, e.g. to wait out a rate-limit window)
      mutates: <what the action changes on the node, declared>
      effect: <read-only shell; `expect` is matched against ITS output, never the action's>
      # MISMATCH control (HQ 2026-11-16): the same probe with ONE value deliberately wrong; it must FAIL `expect` on the
      # applied node, or the check does not discriminate and the set is INVALID. Mandatory for a probe that hands a
      # name, user, key, cipher or vhost to a tool and takes the tool's verdict (TLS, logins, HTTP by host); optional
      # for direct state reads.
      mismatch: {varies: <which value is wrong and why the verdict must change>, probe: <read-only shell>}
      host: node | peer              # where the probe runs (default node); peer needs the set's `peer` block
                                     # (not `on`: YAML 1.1 reads a bare `on` key as the boolean true)
  peer: {kind: <nodes.yml kind with second-node>, why: <why the behaviour needs a second machine>, files: [<abs path>]}
      # PEER node (HQ 2026-11-17 ruling 1, the VPN client): reverted with the node under the same lab lock, powered off
      # after the run. Its probes keep every host rule except that they may name the class node's host-only address
      # (nodes.yml), the only other host they reach. `files` are read from the node (empty in the clean phase) and
      # handed to every peer probe under /run/p8test-from-node/<basename> (the runner writes them on the peer); read
      # again before each mutating peer check, so a file a node action wrote just before reaches the peer.
  session: {user: <p8test* account the applied class creates>, desktop: plasma, why: <why the behaviour needs a login>}
      # DESKTOP SESSION (2026-11-17, HQ batch-8 ruling 5: the KDE checks on kubuntu): for behaviour that a class applies
      # only while the user is logged in (an exec guarded by `who`, the user's session D-Bus). Needs a node with the
      # `kde` capability. After the apply the runner logs the user in to Plasma (SDDM autologin drop-in, sddm
      # restarted; up when `who` lists the user and plasmashell runs, within 120 s), then makes two agent runs as the
      # harness does: the first may apply what needs the session, the second passes the harness's run-2 gate (exit 0
      # with no change events, or only the plan's expected_run2_events), now with the user logged in. Both runs are recorded under `session`; then the APPLIED
      # phase runs. The login and the agent runs are runner steps, never probes (probes keep the Puppet ban).
  peer_agent: {after: <id of a mutating check>, certname: <p8test* identity>, why: <why the peer's agent run is the evidence>}
      # PEER AGENT RUN (2026-11-18, HQ ruling C2: Hashman end to end): for a class whose node is itself a Puppet server
      # (capability puppet-server, the master-role node). Right after the named mutating check, the runner makes one
      # agent run on the peer against the class's node, as the client `certname` (the master-role server's
      # autosign.conf names it), from its own confdir /etc/p8test-agent/<certname> (own ssldir, vardir, rundir), so the
      # peer's identity toward the lab master is untouched. Its exit code and changes are recorded under `peer_agent`;
      # the checks after it judge what it applied. A runner step, never a probe (probes keep the Puppet ban).
  node_agent: {after: <id of a mutating check, or a list of ids>, why: <why an agent run after that change is the evidence>}
      # NODE AGENT RUN (2026-11-18, the backfill: a class whose purpose includes correcting drift, e.g. purging rules it
      # does not manage): right after the named mutating check (whose action made the drift), the runner makes one
      # agent run on the class's node, as the harness does. Its exit code and changes go under `node_agent`; the checks
      # after it judge whether the drift was corrected. A runner step, never a probe (probes keep the Puppet ban).

Probe rules (validate): the node is the only host — no other host name or address, no ssh/scp/sftp/rsync except to
the node itself (127.0.0.1/localhost), never Puppet (agent/apply/resource); read-only — no service or package state
change, no rm/tee/redirect into a file. Mutating checks (HQ 2026-11-10): opt-in per check with `mutates` (declared
change) + a read-only `effect`; the action may change node state (host rules and the Puppet ban still apply); they are
negative controls whose EFFECT must be absent on the clean node (the action never runs there); after apply they run
only once every read-only check has passed, in file order, and pass on the effect. Never on the master: the runner's
only execution path is the node.
P8_PHASE3_DIR redirects checks/results/reviews; P8_PHASE3_HARNESS / P8_PHASE3_REVERT / P8_PHASE3_LABVM replace the
harness, the revert tool and lab_vm.sh in the lab's hooks, P8_PARAMS_DIR the params directory (tests). Harness metrics events go to .codex_state/logs/phase3-metrics, never into Phase 1 records.
"""

from __future__ import annotations

import datetime as dt
import functools
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
    """Where the engine keeps its records of the sets: results/ and reviews/ (and, before the move, the sets)."""
    return Path(os.environ.get("P8_PHASE3_DIR") or REPO / ".codex_state" / "checks")


SUITE = REPO / "spec" / "behaviour"
MOVED = REPO / ".codex_state" / "checks" / "moved.json"


def sets_dir() -> Path:
    """The check sets: the public suite's (spec/behaviour/checks, HQ review of design note F); a test's P8_PHASE3_DIR
    keeps its own sets beside its records."""
    env = os.environ.get("P8_PHASE3_DIR")
    return Path(env) if env else SUITE / "checks"


def set_path(cls: str) -> Path:
    return sets_dir() / f"{cls}.yml"


def moved_entry(cls: str) -> dict | None:
    """The set's neutral move (behaviour_move.py): the old file's identity and the new file's, or None."""
    if os.environ.get("P8_PHASE3_DIR") or not MOVED.is_file():
        return None
    return json.loads(MOVED.read_text()).get(cls)


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
    """The set as the engine runs it: the public template rendered with the lab's values (behaviour_move.lab_view: the
    run's machines, the site paths, P8_PEER_ADDR), its `apply` block left to the harness; and the file's bytes."""
    path = set_path(cls)
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
    import behaviour_move  # noqa: PLC0415
    return behaviour_move.lab_view(cls, data), raw


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
# Probe helpers (HQ batch-12 ruling 6): the public runner prepends them to every node and peer script; the mutating ones
# only in an action.
MUTATING_HELPER = re.compile(r"\bp8_hold\b")


def probe_problems(probe: str, mutating: bool = False, allow: str | None = None) -> list[str]:
    """`allow`: the one other host a peer probe may name, the class node's host-only address."""
    rules = FORBIDDEN[:HOST_RULES] if mutating else FORBIDDEN
    if allow:
        probe = re.sub(rf"(?<![\d.]){re.escape(allow)}(?![\d.])", "CLASS_NODE", probe)  # no angle brackets: `>` reads as a redirect
    out = [f"probe {why}: {pat.pattern}" for pat, why in rules if pat.search(probe)]
    if not mutating and MUTATING_HELPER.search(probe):
        out.append("probe calls a mutating helper (p8_hold), which belongs in a check's action")
    if LOCAL_SSH.search(probe) and not LOCAL_TARGET.search(probe):
        out.append("probe uses ssh to a host other than the node itself (127.0.0.1/localhost)")
    return out


def peer_problems(cls: str, peer) -> tuple[list[str], str | None]:
    """(problems, the class node's host-only address that peer probes may name)."""
    import nodes  # noqa: PLC0415
    inventory = nodes.load()["nodes"]
    node_ip = nodes.select(nodes.load(), cls=cls)["hostonly_ip"]
    if not isinstance(peer, dict) or not set(peer) <= {"kind", "why", "files"} or len(str(peer.get("why", ""))) < 20:
        return ["peer takes kind, why (>= 20 characters) and optional files"], node_ip
    out = []
    kind = peer.get("kind")
    if kind not in inventory:
        out.append(f"peer: {kind!r} is not a node kind of nodes.yml")
    elif inventory[kind]["hostonly_ip"] == node_ip:
        out.append("peer: the peer is the class's own node")
    elif "second-node" not in inventory[kind]["capabilities"]:
        out.append(f"peer: node {kind} lacks the capability 'second-node'")
    files = peer.get("files") or []
    if not isinstance(files, list) or not all(isinstance(f, str) and re.fullmatch(r"/[\w./-]+", f) for f in files):
        out.append("peer.files is a list of absolute paths on the node")
    return out, node_ip


PURPOSE_MISSING = "purpose: the class's purpose (one or two sentences, >= 40 characters) is required (HQ 2026-11-18 C1)"
OUTCOMES_MISSING = "outcomes: the purpose as observable outcomes, each mapped to checks or uncovered, is required (HQ ruling 2)"


FLEET_USAGE = REPO / ".codex_state" / "diagnosis" / "fleet_variant_usage.md"


def param_default(text: str, param: str) -> str | None:
    """A class's default for `param` as written (spaces removed), or None when it has none (a required parameter)."""
    head = text[:text.find("{", text.find("("))] if "(" in text else ""
    m = re.search(rf"\${param}\s*(?:=\s*([^,\n#]+?))?\s*(?:,|\)|#|\n)", head)
    return re.sub(r"\s+", "", m.group(1)) if m and m.group(1) else None


def composite_sets(cls: str, param: str) -> list[str]:
    """The repository's classes that declare `cls` with `param` set, so that their value reaches every node declaring
    them. A composite that forwards its own parameter (`param => $own`) with the same default as `cls` is not counted:
    fleet_variant_usage.md already follows that forwarding, and its default is no variant (2026-11-23)."""
    import fleet_variants  # noqa: PLC0415
    own_file = REPO / "manifests" / f"{cls}.pp"
    own_default = param_default(fleet_variants.strip_comments(own_file.read_text()), param) if own_file.is_file() else None
    found = []
    for path in sorted((REPO / "manifests").glob("*.pp")):
        if path.stem == cls:
            continue
        text = fleet_variants.strip_comments(path.read_text(errors="replace"))
        for m in fleet_variants.DECL.finditer(text):
            if (m.group(2) or m.group(4)) != cls:
                continue
            body = fleet_variants.body_at(text, m.start())
            if param not in fleet_variants.top_level_params(body):
                continue
            fwd = re.search(rf"(?:^|[,{{\s]){param}\s*=>\s*\$(\w+)\s*(?:,|$)", body, re.M)
            if fwd and own_default is not None and param_default(text, fwd.group(1)) == own_default:
                continue
            found.append(path.stem)
            break
    return found


def accepted_gap_problems(cls: str, u: dict, where: str) -> list[str]:
    """HQ 2026-11-23 ruling 1c: an accepted gap is a parameter variant no production node statement sets: each named
    parameter of the class's manifest reads 0 in diagnosis/fleet_variant_usage.md (absent = 0); a class of the passwd/
    layer, which the engine never reads, is undeterminable and never qualifies."""
    import fleet_variants  # noqa: PLC0415
    gap, out = u.get("accepted_gap"), []
    if not isinstance(gap, list) or not gap or not all(isinstance(g, str) and re.fullmatch(r"\w+", g) for g in gap):
        return [f"{where}: accepted_gap lists the class's parameter names"]
    if cls in fleet_variants.PASSWD_LAYER:
        return [f"{where}: accepted_gap: {cls}'s production use lives in the passwd/ layer, which is never read "
                "(undeterminable): not an accepted gap; a check, or a row naming what is missing"]
    counts = {}
    for line in (FLEET_USAGE.read_text().splitlines() if FLEET_USAGE.is_file() else []):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) == 5 and cells[1] == cls:
            counts[cells[2]] = cells[3]
    manifest = REPO / "manifests" / f"{cls}.pp"
    text = manifest.read_text() if manifest.is_file() else ""
    for g in gap:
        if not re.search(rf"\${g}\b", text):
            out.append(f"{where}: accepted_gap: {g} is not a parameter of manifests/{cls}.pp")
        elif re.search(rf"\${g}\s*=\s*lookup\(", text):
            out.append(f"{where}: accepted_gap: {g} defaults to a Hiera lookup(), which production may set in Hiera, "
                       "and fleet_variant_usage.md reads node files only (undeterminable)")
        elif composite_sets(cls, g):
            out.append(f"{where}: accepted_gap: {', '.join(composite_sets(cls, g))} set(s) {g} on {cls}, so production "
                       "nodes declaring that composite get its value (not counted by fleet_variant_usage.md): a check")
        elif counts.get(g, "0") != "0":
            out.append(f"{where}: accepted_gap: production sets {g} on {counts[g]} node statement(s) "
                       "(fleet_variant_usage.md): a variant production uses becomes a check")
    return out


def uncovered_problems(u, where: str, strict: bool, cls: str = "") -> list[str]:
    """An outcome left uncovered. Strict (HQ batch-15 ruling 3, applied capability-based): why, lifted_by and evidence
    for the reason (a command result, or a capability the node inventory lacks); lifted_by names a node kind that is
    not active, or the missing capability as `capability: ...`. A row lifted by an active node kind is refused: the
    node exists, so the outcome is a work item to test there. Not strict: the rule before it (why and lifted_by)."""
    import nodes  # noqa: PLC0415
    if isinstance(u, dict) and "accepted_gap" in u:
        if set(u) != {"why", "accepted_gap", "evidence"} or len(str(u.get("why", ""))) < 20 or \
                len(str(u.get("evidence", "")).strip()) < 20:
            return [f"{where}: an accepted gap takes why (>= 20 characters), accepted_gap and evidence"]
        return accepted_gap_problems(cls, u, where)
    allowed = [{"why", "lifted_by", "evidence"}] if strict else [{"why", "lifted_by"}, {"why", "lifted_by", "evidence"}]
    if not isinstance(u, dict) or set(u) not in allowed or len(str(u.get("why", ""))) < 20:
        return [f"{where}: uncovered takes why (>= 20 characters), lifted_by" + (" and evidence" if strict else "")]
    lifted = str(u["lifted_by"])
    if not strict and "evidence" not in u:  # an earlier row of an approved set: the earlier rule until the sweep
        return lifting_problems(lifted, None, where)
    out = []
    if len(str(u["evidence"]).strip()) < 20:
        out.append(f"{where}: evidence (>= 20 characters) backs the reason: a command result, or a capability the node "
                   "inventory lacks (HQ batch-15 ruling 3)")
    if lifted.startswith("capability:"):
        if len(lifted.split(":", 1)[1].strip()) < 10:
            out.append(f"{where}: lifted_by `capability: ...` names the missing capability")
        return out
    found = lifting_problems(lifted, None, where)
    if found:
        return out + found
    if nodes.load()["nodes"][lifted].get("status") == "active":
        out.append(f"{where}: lifted_by {lifted!r} is an active node kind: test it there (a work item), or name what is "
                   "missing as `capability: ...` with evidence (HQ batch-15 ruling 3)")
    return out


def open_uncovered(cls: str) -> int:
    """The class's open uncovered rows: outcomes of its set that no check probes yet (HQ batch-15 follow-up 3: status.py
    and the approval report show the count). 0 without a set or with an unreadable one."""
    path = set_path(cls)
    try:
        data = yaml.safe_load(path.read_bytes()) if path.is_file() else None
    except yaml.YAMLError:
        return 0
    rows = (data or {}).get("outcomes") or [] if isinstance(data, dict) else []
    return sum(1 for r in rows if isinstance(r, dict) and "uncovered" in r)


def strip_authoring(raw: bytes) -> bytes:
    """The set without a top-level `authoring:` block (the key line and every indented or blank line after it): HQ
    2026-11-20 item 2 removed the hand-entered field, which must not make a reviewed set stale."""
    out, skipping = [], False
    for line in raw.decode("utf-8").splitlines(keepends=True):
        if line.startswith("authoring:"):
            skipping = True
            continue
        if skipping and (line.startswith((" ", "\t")) or not line.strip()):
            continue
        skipping = False
        out.append(line)
    return "".join(out).encode("utf-8")


def content_sha(raw: bytes) -> str:
    return hashlib.sha256(strip_authoring(raw)).hexdigest()


@functools.lru_cache(maxsize=None)
def _content_shas_by_full_sha(path: str, repo: str) -> dict:
    """Every committed version of a set file: its full-file sha256 -> its content sha (older records name only the
    former). Empty outside a git work tree."""
    rel = os.path.relpath(path, repo)
    log = subprocess.run(["git", "-C", repo, "log", "--format=%H", "--", rel], capture_output=True, text=True)
    out = {}
    for commit in log.stdout.split() if log.returncode == 0 else []:
        blob = subprocess.run(["git", "-C", repo, "show", f"{commit}:{rel}"], capture_output=True)
        if blob.returncode == 0:
            out.setdefault(hashlib.sha256(blob.stdout).hexdigest(), content_sha(blob.stdout))
    return out


def view_sha(cls: str, raw: bytes) -> str | None:
    """The sha256 of the set as the engine runs it (behaviour_move.lab_view: rendered with the lab's values, without
    its `apply` block), canonical JSON; None for a file that does not parse. An edit to the `apply` block alone (how
    the public runner builds the catalog, e.g. `requires: [server]`) leaves it unchanged."""
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    import behaviour_move  # noqa: PLC0415
    view = behaviour_move.lab_view(cls, data)
    return hashlib.sha256(json.dumps(view, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def reviewed_as_is(cls: str, record: dict | None, raw: bytes, repo: Path | None = None) -> bool:
    """Whether `record` (a review or a result) judged the set as it stands: the same file, or the same file but for the
    removed `authoring:` block (its own content sha, or for an older record the content sha of the git version its
    full-file sha names)."""
    if not record:
        return False
    sha = hashlib.sha256(raw).hexdigest()
    if record.get("check_file_sha256") == sha:
        return True
    moved = moved_entry(cls)
    if moved and (moved.get("new_sha256") == sha or
                  (moved.get("view_sha256") is not None and moved["view_sha256"] == view_sha(cls, raw))):
        # HQ review of design note F, ruling 6: the set as it stands is the neutral move of the old file, so a record
        # of the old file judged this one
        if record.get("check_file_sha256") == moved["old_sha256"]:
            return True
        mine, path = moved["old_content_sha256"], REPO / ".codex_state" / "checks" / f"{cls}.yml"
    else:
        mine, path = content_sha(raw), set_path(cls)
    if record.get("content_sha256"):
        return record["content_sha256"] == mine
    return _content_shas_by_full_sha(str(path), str(repo or REPO)).get(record.get("check_file_sha256")) == mine


def approved_unchanged(cls: str, raw: bytes) -> bool:
    """HQ batch-15 ruling 3's scope: a set whose latest review passed it as it stands keeps the earlier uncovered rule
    until the scheduled sweep; a new or changed set meets the new rule at once."""
    review = latest_review(cls)
    return bool(review) and review.get("verdict") == "PASS" and reviewed_as_is(cls, review, raw)


def outcome_problems(data: dict, strict: bool = True) -> list[str]:
    """HQ 2026-11-18 ruling 2: every outcome maps to at least one check of the set, or is declared uncovered."""
    rows = data.get("outcomes")
    if not rows:
        return [OUTCOMES_MISSING]
    if not isinstance(rows, list):
        return ["outcomes must be a list"]
    ids = {c.get("id") for c in data.get("checks") or [] if isinstance(c, dict)}
    out = []
    for i, row in enumerate(rows):
        where = f"outcomes[{i}]"
        if not isinstance(row, dict) or len(str(row.get("outcome", ""))) < 15 or not str(row.get("from", "")).strip():
            out.append(f"{where}: takes outcome (>= 15 characters) and from (the baseline reference)")
            continue
        has_checks, has_uncovered = "checks" in row, "uncovered" in row
        if has_checks == has_uncovered:
            out.append(f"{where}: maps to `checks` (>= 1 check id) or is `uncovered`, exactly one of them")
        elif has_checks:
            refs = row["checks"]
            if not isinstance(refs, list) or not refs:
                out.append(f"{where}: checks must list at least one check id")
            else:
                out += [f"{where}: no check {r!r} in the set" for r in refs if r not in ids]
        else:
            out += uncovered_problems(row["uncovered"], f"{where}.uncovered", strict, str(data.get("class", "")))
    return out


def outcome_results(data: dict, applied: list[dict]) -> list[dict]:
    """Per outcome: covered by which checks, and whether all of them passed after apply (the approval report's row)."""
    passed = {r["id"]: r.get("passed") for r in applied}
    rows = []
    for row in data.get("outcomes") or []:
        if not isinstance(row, dict):
            continue
        if "checks" in row:
            rows.append({"outcome": row.get("outcome"), "checks": row["checks"],
                         "passed": all(passed.get(c) is True for c in row["checks"])})
        else:
            rows.append({"outcome": row.get("outcome"), "uncovered": row.get("uncovered")})
    return rows


def validate(cls: str) -> tuple[list[str], dict, bytes]:
    data, raw = load_set(cls)
    problems: list[str] = []
    base = baseline.for_class(cls)
    if data.get("class") != cls:
        problems.append(f"class {data.get('class')!r} != file name {cls!r}")
    if data.get("baseline") != label(base):
        problems.append(f"baseline {data.get('baseline')!r} != the class's baseline {label(base)!r}")
    if "deferred" not in data:  # the public runner applies the set's own catalog, on the set's node kind (ruling 2)
        applied_on = ((yaml.safe_load(raw) or {}).get("apply") or {}).get("node")
        if not applied_on:
            problems.append("apply: the catalog the public runner applies (resource_type, node, catalog) is missing")
        else:
            import nodes  # noqa: PLC0415
            planned = nodes.select(nodes.load(), cls=cls)["kind"]
            if applied_on != planned:
                problems.append(f"apply.node {applied_on!r} != the plan's node kind for the class {planned!r}")
    if "authoring" in data:  # HQ 2026-11-20 item 2: computed by the tool or not recorded
        problems.append("authoring is not entered by hand (HQ 2026-11-20 item 2): remove the block")
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
    if len(str(data.get("purpose") or "").strip()) < 40:
        problems.append(PURPOSE_MISSING)
    problems += outcome_problems(data, strict=not approved_unchanged(cls, raw))
    peer_ip = None
    if "peer" in data:
        found, peer_ip = peer_problems(cls, data["peer"])
        problems += found
    if "session" in data:
        problems += session_problems(cls, data["session"])
    if "peer_agent" in data:
        problems += peer_agent_problems(cls, data["peer_agent"], data)
    if "node_agent" in data:
        problems += node_agent_problems(data["node_agent"], data)
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
        if any(isinstance(k, bool) for k in c):
            problems.append(f"{where}: a key read as a boolean (YAML 1.1 `on:`/`yes:`/`no:`); a peer probe is `host: peer`")
        mutating = "mutates" in c
        # 2026-11-18: an action that must first wait out a protocol window (e.g. a 60 s rate-limit) may run longer
        if "timeout" in c and (not mutating or not isinstance(c["timeout"], int) or not 1 <= c["timeout"] <= 600):
            problems.append(f"{where}: timeout (seconds, 1-600) is for a mutating check's action only")
        on = c.get("host", "node")
        allow = None
        if on not in ("node", "peer"):
            problems.append(f"{where}: host must be node|peer")
        elif on == "peer":
            if "peer" not in data:
                problems.append(f"{where}: host: peer needs the set's `peer` block")
            allow = peer_ip
        if not isinstance(c.get("probe"), str) or not c["probe"].strip():
            problems.append(f"{where}: probe is required")
        else:
            problems += [f"{where}: {p}" for p in probe_problems(c["probe"], mutating, allow)]
        if mutating:
            if not isinstance(c["mutates"], str) or len(c["mutates"].strip()) < 10:
                problems.append(f"{where}: mutates must declare what the action changes")
            if not isinstance(c.get("effect"), str) or not c["effect"].strip():
                problems.append(f"{where}: a mutating check needs a read-only `effect` probe (the evidence)")
            else:
                problems += [f"{where}: effect {p}" for p in probe_problems(c["effect"], False, allow)]
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
                    problems += [f"{where}: mismatch {p}" for p in probe_problems(mm["probe"], False, allow)]
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
    if not any(isinstance(c, dict) and c.get("control") == "negative" and "variant" not in c for c in checks):
        problems.append("no negative control: at least one check of the base run must fail on the clean node")
    problems += variant_problems(cls, data, checks)
    return problems, data, raw


VARIANT_KEYS = {"name", "why", "node", "params", "no_resources"}


def variant_params(cls: str, name: str) -> Path:
    return PARAMS_DIR / "variants" / name / f"puppet_infrastructure::{cls}.json"


def variant_problems(cls: str, data: dict, checks: list) -> list[str]:
    """HQ 2026-11-23 ruling 1a: more than one params fixture per set, and a set's checks on a second node kind."""
    import nodes  # noqa: PLC0415
    variants = data.get("variants")
    tagged = [c for c in checks if isinstance(c, dict) and "variant" in c]
    if variants is None:
        return [f"check {c.get('id')}: `variant` names no variant (the set has no `variants`)" for c in tagged]
    if not isinstance(variants, list) or not variants:
        return ["variants must be a non-empty list"]
    out, names = [], set()
    inventory = nodes.load()["nodes"]
    plan_node = nodes.select(nodes.load(), cls=cls)["kind"]
    for i, v in enumerate(variants):
        where = f"variant {v.get('name', i) if isinstance(v, dict) else i}"
        if not isinstance(v, dict) or not set(v) <= VARIANT_KEYS or not {"name", "why"} <= set(v):
            out.append(f"{where}: takes name, why and node and/or params")
            continue
        if not SLUG.fullmatch(str(v["name"])) or v["name"] in names:
            out.append(f"{where}: name must be a unique slug")
        names.add(v["name"])
        if len(str(v["why"]).strip()) < 20:
            out.append(f"{where}: why (>= 20 characters) says what this run adds")
        if "node" not in v and "params" not in v:
            out.append(f"{where}: needs node and/or params")
        if "node" in v:
            kind = v["node"]
            if kind not in inventory or inventory[kind].get("status") != "active":
                out.append(f"{where}: node {kind!r} is not an active node kind (nodes.yml)")
            elif kind == plan_node and "params" not in v:
                out.append(f"{where}: node {kind} is the plan's own node; a variant there needs params")
        if "no_resources" in v and (v["no_resources"] is not True or "params" not in v):
            out.append(f"{where}: no_resources is `true`, for a params variant whose class declares nothing")
        if "params" in v:
            if not SLUG.fullmatch(str(v["params"])):
                out.append(f"{where}: params must be a slug")
            elif not variant_params(cls, v["params"]).is_file():
                out.append(f"{where}: params {v['params']} but {variant_params(cls, v['params'])} is missing")
    for c in tagged:
        if c["variant"] not in names:
            out.append(f"check {c.get('id')}: variant {c['variant']!r} is not declared")
        if c.get("host") == "peer":
            out.append(f"check {c.get('id')}: a variant run has no peer")
    for name in names:
        mine = [c for c in tagged if c.get("variant") == name]
        if not any(c.get("control") == "negative" for c in mine):
            out.append(f"variant {name}: needs >= 1 negative control of its own")
    return out


def sweep_pending(cls: str, data: dict) -> list[str]:
    """The uncovered rows of an approved, unchanged set that the strict rule would refuse (the scheduled sweep)."""
    raw = set_path(cls).read_bytes()
    if "deferred" in data or not approved_unchanged(cls, raw):
        return []
    return [p for p in outcome_problems(data, strict=True) if ".uncovered" in p]


def cmd_sweep() -> int:
    """List every approved set whose uncovered rows await the HQ batch-15 ruling-3 sweep, with the row count."""
    total = 0
    for path in sorted(sets_dir().glob("*.yml")):
        cls = path.stem
        problems, data, _ = validate(cls)
        if problems:
            continue
        pending = sweep_pending(cls, data)
        if pending:
            total += len(pending)
            print(f"{cls}: {len(pending)}")
    print(f"SWEEP: {total} uncovered row(s) in approved sets await the ruling-3 sweep")
    return 0


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
    pending = sweep_pending(cls, data)
    if pending:
        print(f"SWEEP {cls}: {len(pending)} uncovered row(s) await the HQ batch-15 ruling-3 sweep (approved as it "
              f"stands): {pending[0]}")
    neg = sum(1 for c in data["checks"] if c["control"] == "negative")
    mut = sum(1 for c in data["checks"] if "mutates" in c)
    mism = sum(1 for c in data["checks"] if "mismatch" in c)
    print(f"VALID {cls}: {len(data['checks'])} checks ({neg} negative controls, {mut} mutating, {mism} mismatch), "
          f"{sum(len(c['derived_from']) for c in data['checks'])} baseline references at {data['baseline']}")
    return 0


# ------------------------------------------------------------------ run

SESSION_USER = re.compile(r"p8test[a-z0-9]*")
SESSION_KEYS = {"user", "desktop", "why"}
def session_problems(cls: str, session) -> list[str]:
    import nodes  # noqa: PLC0415
    if not isinstance(session, dict) or set(session) != SESSION_KEYS or len(str(session.get("why", ""))) < 20:
        return ["session takes user, desktop and why (>= 20 characters)"]
    out = []
    if not SESSION_USER.fullmatch(str(session["user"])):
        out.append("session.user must be a p8test* fixture account")
    if session["desktop"] != "plasma":
        out.append("session.desktop must be plasma (the only desktop session the runner starts)")
    node = nodes.select(nodes.load(), cls=cls)
    if "kde" not in node.get("capabilities", []):
        out.append(f"session: the class's node {node['kind']} lacks the capability 'kde'")
    return out


PEER_AGENT_KEYS = {"after", "certname", "why"}
PEER_AGENT_CERT = re.compile(r"p8test[a-z0-9-]{0,40}")
def peer_agent_problems(cls: str, block, data: dict) -> list[str]:
    import nodes  # noqa: PLC0415
    if not isinstance(block, dict) or set(block) != PEER_AGENT_KEYS or len(str(block.get("why", ""))) < 20:
        return ["peer_agent takes after, certname and why (>= 20 characters)"]
    out = []
    if "peer" not in data:
        out.append("peer_agent needs the set's `peer` block (the machine that makes the agent run)")
    if not PEER_AGENT_CERT.fullmatch(str(block["certname"])):
        out.append("peer_agent.certname must be a p8test* fixture identity")
    mutating = [c.get("id") for c in data.get("checks") or [] if isinstance(c, dict) and "mutates" in c]
    if block["after"] not in mutating:
        out.append("peer_agent.after must name a mutating check of the set (the run follows its action)")
    node = nodes.select(nodes.load(), cls=cls)
    if "puppet-server" not in node.get("capabilities", []):
        out.append(f"peer_agent: the class's node {node['kind']} lacks the capability 'puppet-server'")
    return out


NODE_AGENT_KEYS = {"after", "why"}


def node_agent_problems(block, data: dict) -> list[str]:
    if not isinstance(block, dict) or set(block) != NODE_AGENT_KEYS or len(str(block.get("why", ""))) < 20:
        return ["node_agent takes after and why (>= 20 characters)"]
    mutating = [c.get("id") for c in data.get("checks") or [] if isinstance(c, dict) and "mutates" in c]
    anchors = block["after"] if isinstance(block["after"], list) else [block["after"]]
    if not anchors or any(a not in mutating for a in anchors):
        return ["node_agent.after must name a mutating check of the set, or a list of them (a run follows each action)"]
    return []


def git_head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True,
                          text=True).stdout.strip()


def junit(cls: str, record: dict) -> bytes:
    suites = ET.Element("testsuites", name=f"phase3.{cls}")
    junit_suites(suites, cls, record)
    for name, v in (record.get("variants") or {}).items():  # HQ 2026-11-23 ruling 1a: one suite pair per run
        junit_suites(suites, f"{cls}.{name}", v)
    return ET.tostring(suites, encoding="utf-8", xml_declaration=True)


def junit_suites(suites, cls: str, record: dict) -> None:
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
                ET.Element("skipped", message=str(record["outcome"])))


def write_outputs(cls: str, record: dict) -> Path:
    out = phase3_dir() / "results" / cls
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"{record['at']}-{record['role']}"
    stem.with_suffix(".json").write_text(json.dumps(record, indent=1) + "\n")
    stem.with_suffix(".xml").write_bytes(junit(cls, record))
    return stem


def public_run(cls: str) -> tuple[dict | None, str]:
    """The run itself, through the public runner with the lab as its provider (HQ review of the behaviour suite,
    ruling 2): behaviour_lab.py's command mode, the gate-v2 harness applying after checking it renders exactly the
    runner's manifest. The caller holds the lab lock. Returns the runner's record (None if it wrote none) and its
    output's tail."""
    import tempfile  # noqa: PLC0415
    import behaviour_lab  # noqa: PLC0415
    with tempfile.TemporaryDirectory(prefix="phase3-") as out:
        cmd, env = behaviour_lab.runner_command(Path(out), checks=sets_dir())
        env["P8_LAB_LOCKED"] = "1"
        env["BEHAVIOUR_LAB_CHECKS"] = str(sets_dir())
        proc = subprocess.Popen(cmd + [cls], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        tail: list[str] = []
        for line in proc.stdout:
            if not line.startswith(f"{cls}: "):  # the runner's own record path is a temporary one
                print(line, end="")
            tail = (tail + [line])[-40:]
        proc.wait()
        files = sorted((Path(out) / cls).glob("*.json"))
        return (json.loads(files[-1].read_text()) if files else None), "".join(tail)


# The runner's record keys the engine's result takes over as they are (the envelope, the outcomes table and the
# freshness judgement stay the engine's).
TAKEN = ("clean", "apply", "applied", "findings", "not_run", "session", "node_agent", "peer_agent", "variants",
         "manifest_sha256")


def cmd_run(cls: str, role: str) -> int:
    started = now()
    problems, data, raw = validate(cls)
    record = {"class": cls, "role": role, "at": started, "runner": git_head(), "baseline": data.get("baseline"),
              "check_file_sha256": hashlib.sha256(raw).hexdigest(), "content_sha256": content_sha(raw),
              "valid": not problems, "problems": problems,
              "clean": [], "apply": None, "applied": [], "findings": [], "not_run": [], "outcome": None}

    t0 = time.monotonic()

    def finish(outcome: str, rc: int) -> int:
        record["outcome"] = outcome
        applied = record["applied"] + [r for v in (record.get("variants") or {}).values() for r in v["applied"]]
        record["outcomes"] = outcome_results(data, applied)
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
    # One lab run at a time (lab_lock.sh), held across the whole run: every revert, both probe phases and the apply.
    lock = subprocess.run([str(TOOLS / "lab_lock.sh"), "take", str(os.getpid()), f"phase3.py run {cls} {role}"],
                          capture_output=True, text=True)
    if lock.returncode != 0:
        record["problems"].append(f"another lab run holds the lab lock: {lock.stderr.strip()}")
        print(f"REFUSED: another lab run holds the lab lock ({lock.stderr.strip()})", file=sys.stderr)
        return finish("ENVIRONMENT_FAILED", 3)
    import nodes  # noqa: PLC0415
    inventory = nodes.load()["nodes"]
    node = nodes.select(nodes.load(), cls=cls)
    record["node"] = node["kind"]
    record["nodes"] = {"node": {"kind": node["kind"], "snapshot": node.get("baseline_snapshot")}}
    try:
        if "peer" in data:
            peer = {**inventory[data["peer"]["kind"]], "kind": data["peer"]["kind"]}
            record["peer"] = peer["kind"]
            record["nodes"]["peer"] = {"kind": peer["kind"], "snapshot": peer.get("baseline_snapshot")}
            if peer["status"] != "active":
                record["problems"].append(f"peer node {peer['kind']} is {peer['status']}")
                return finish("ENVIRONMENT_FAILED", 3)
        pub, tail = public_run(cls)
        if pub is None:
            record["problems"].append(f"the public runner wrote no record: {tail.strip()[-300:]}")
            return finish("ENVIRONMENT_FAILED", 3)
        for key in TAKEN:
            if key in pub:
                record[key] = pub[key]
        record["valid"] = record["valid"] and pub.get("valid", True)
        record["problems"] += pub.get("problems") or []
        record["nodes"] = pub.get("nodes") or record["nodes"]
        record["node"] = record["nodes"].get("node", {}).get("kind", record["node"])
        outcome = pub.get("outcome") or "ENVIRONMENT_FAILED"
        return finish(outcome, OUTCOME_RC[outcome])
    finally:
        subprocess.run([str(TOOLS / "lab_lock.sh"), "release", str(os.getpid())], capture_output=True)


OUTCOME_RC = {"ALL_PASS": 0, "FINDINGS": 1, "INVALID_SET": 2, "APPLY_FAILED": 3, "ENVIRONMENT_FAILED": 3}
OUTCOME_ORDER = ["INVALID_SET", "ENVIRONMENT_FAILED", "APPLY_FAILED", "FINDINGS", "ALL_PASS"]
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


def cmd_verdict(cls: str, derived: str, evidence: list[str], purpose: str = "", purpose_evidence: str = "") -> int:
    if derived not in ("ok", "fail") or not evidence:
        raise SystemExit("ERROR: verdict needs --derived ok|fail and at least one --evidence")
    # HQ 2026-11-18 ruling C1: the reviewer also judges whether the checks test the class's stated purpose
    if purpose not in ("covered", "gap") or len(purpose_evidence.strip()) < 20:
        raise SystemExit("ERROR: verdict needs --purpose covered|gap and --purpose-evidence TEXT (>= 20 characters)")
    evidence = evidence + [f"purpose {purpose}: {purpose_evidence.strip()}"]
    problems, data, raw = validate(cls)
    if "deferred" in data:  # no runs to reproduce: the reviewer judges the stated reason against the cited lines
        checks = {"deferral_valid": "fail" if problems else "ok", "derived_from": derived,
                  "purpose": "ok" if purpose == "covered" else "fail"}
        verdict = "PASS" if all(v == "ok" for v in checks.values()) else "FAIL"
        record = {"class": cls, "at": now(), "verdict": verdict, "deferral": True, "checks": checks,
                  "evidence": evidence, "check_file_sha256": hashlib.sha256(raw).hexdigest(),
                  "content_sha256": content_sha(raw), "findings": [],
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
    same = bool(mine and theirs) and outcomes(mine) == outcomes(theirs) and (
        mine["check_file_sha256"] == theirs["check_file_sha256"]
        or (mine.get("content_sha256") or "x") == (theirs.get("content_sha256") or "y"))
    checks["reproduced"] = "ok" if same else "fail"
    checks["derived_from"] = derived
    # HQ 2026-11-17 batch-8 ruling 3: the reviewer's run had every node fresh (with a peer: both), recorded below.
    ran = (mine or {}).get("nodes") or {}
    want = {"node", "peer"} if "peer" in data else {"node"}
    checks["nodes_fresh"] = "ok" if set(ran) == want and all(e.get("fresh") for e in ran.values()) else "fail"
    checks["purpose"] = "ok" if purpose == "covered" else "fail"
    verdict = "PASS" if all(v == "ok" for v in checks.values()) else "FAIL"
    started = dt.datetime.strptime(mine["at"], "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc) if mine else None
    review_s = round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 1) if started else None
    record = {"class": cls, "at": now(), "verdict": verdict, "checks": checks, "evidence": evidence,
              "review_s": review_s, "check_file_sha256": mine and mine["check_file_sha256"],
              "content_sha256": mine and mine.get("content_sha256"),
              "reviewer_result": mine and f"{mine['at']}-reviewer", "author_result": theirs and f"{theirs['at']}-author",
              "findings": (mine or {}).get("findings", []), "nodes": ran}
    out = phase3_dir() / "reviews" / cls
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{record['at']}.json"
    path.write_text(json.dumps(record, indent=1) + "\n")
    print(f"VERDICT {verdict}\nclass {cls}\nchecks {json.dumps(checks)}\nfindings {record['findings']}")
    for role_name, e in ran.items():
        print(f"{role_name} {e.get('kind')} {e.get('snapshot')} boot {str(e.get('boot_id'))[:8]} "
              f"{'fresh' if e.get('fresh') else 'NOT FRESH'}")
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
    row = {"class": cls, "state": "none", "detail": "", "author_run_s": None,
           "reviewer_run_s": None, "review_s": None}
    if not set_path(cls).is_file():
        return row
    problems, data, raw = validate(cls)
    # HQ 2026-11-18 ruling C1: a set that states no purpose yet, or whose review predates the purpose judgement, is
    # `unjudged` (its earlier PASS stands as history, not as behaviour approval)
    if problems and set(problems) <= {PURPOSE_MISSING, OUTCOMES_MISSING}:
        return {**row, "state": "unjudged", "detail": "no purpose yet" if PURPOSE_MISSING in problems
                else "no outcomes table yet (HQ 2026-11-18 ruling 2)"}
    if problems:
        return {**row, "state": "invalid", "detail": problems[0]}
    if "deferred" in data:
        review = latest_review(cls)
        d = data["deferred"]
        if not review or not reviewed_as_is(cls, review, raw):
            return {**row, "state": "unreviewed", "detail": f"deferral ({d['needs']}) not yet judged by the reviewer"}
        if review["verdict"] != "PASS":
            return {**row, "state": "review-failed", "detail": "deferral rejected"}
        if "purpose" not in review["checks"]:
            return {**row, "state": "unjudged", "detail": "the review predates the purpose judgement"}
        return {**row, "state": "deferred", "detail": f"{d['needs']}, lifted by {d['lifted_by']}"}
    author, reviewer, review = latest(cls, "author"), latest(cls, "reviewer"), latest_review(cls)
    row["author_run_s"] = (author or {}).get("duration_s")
    row["reviewer_run_s"] = (reviewer or {}).get("duration_s")
    row["review_s"] = (review or {}).get("review_s")
    if not review:
        return {**row, "state": "unreviewed", "detail": (author or {}).get("outcome") or "not run"}
    judged = review if review.get("check_file_sha256") else reviewer
    if not reviewed_as_is(cls, judged, raw):
        return {**row, "state": "stale", "detail": "the check file changed after its review"}
    if review["verdict"] != "PASS":
        failed = ", ".join(k for k, v in review["checks"].items() if v != "ok")
        return {**row, "state": "review-failed", "detail": failed}
    if "purpose" not in review["checks"]:
        return {**row, "state": "unjudged", "detail": "the review predates the purpose judgement"}
    if review.get("findings"):
        esc = REPO / ".codex_state" / "escalations" / f"{cls}.behaviour.md"
        detail = ", ".join(review["findings"]) + ("" if esc.is_file() else " — NO ESCALATION FILE")
        return {**row, "state": "finding", "detail": detail}
    return {**row, "state": "pass"}


def cmd_state(classes: list[str]) -> int:
    if not classes:
        classes = sorted(p.stem for p in sets_dir().glob("*.yml"))
    rows = [behaviour_state(c) for c in classes]
    m = lambda v, unit: "–" if v is None else f"{v:g}{unit}"  # noqa: E731
    print("| class | behaviour | detail | author run | reviewer run | review |")
    print("|---|---|---|---:|---:|---:|")
    for r in rows:
        print(f"| {r['class']} | {r['state']} | {r['detail']} | "
              f"{m(r['author_run_s'], ' s')} | {m(r['reviewer_run_s'], ' s')} | {m(r['review_s'], ' s')} |")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print("\n" + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())))
    return 0


def inhibit_sleep(argv: list[str]) -> None:
    """Hold a logind sleep/idle inhibitor for the run (a laptop suspend between probes breaks the run; as
    test_class.sh, 2026-11-17). Re-executes under systemd-inhibit once, where logind offers one."""
    if os.environ.get("P8_SLEEP_INHIBITED") or os.environ.get("P8_NO_SLEEP_INHIBIT"):
        return
    probe = ["systemd-inhibit", "--what=sleep:idle", "--who=infra_populi", "--why=probe", "true"]
    try:
        if subprocess.run(probe, capture_output=True).returncode != 0:
            return
    except FileNotFoundError:
        return
    os.environ["P8_SLEEP_INHIBITED"] = "1"
    os.execvp("systemd-inhibit", ["systemd-inhibit", "--what=sleep:idle", "--who=infra_populi",
                                  f"--why=lab run: phase3.py {' '.join(argv)}", sys.executable, __file__, *argv])


def main(argv: list[str]) -> int:
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    if len(argv) == 2 and argv[0] == "validate":
        return cmd_validate(short(argv[1]))
    if len(argv) >= 2 and argv[0] == "run":
        inhibit_sleep(argv)
        role = opt("--role", "author")
        if role not in ("author", "reviewer"):
            raise SystemExit("ERROR: --role author|reviewer")
        return cmd_run(short(argv[1]), role)
    if len(argv) >= 2 and argv[0] == "spot":
        return cmd_spot(short(argv[1]), int(opt("--n", "3")), int(opt("--seed")) if "--seed" in argv else None)
    if argv[:1] == ["state"]:
        return cmd_state([short(c) for c in argv[1:]])
    if argv == ["sweep"]:
        return cmd_sweep()
    if len(argv) >= 2 and argv[0] == "verdict":
        evidence = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == "--evidence"]
        return cmd_verdict(short(argv[1]), opt("--derived", ""), evidence, opt("--purpose", ""),
                           opt("--purpose-evidence", ""))
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
