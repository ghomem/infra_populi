"""Check-set files: reading and validating them.

A set (checks/<class>.yml) states the class's purpose, the purpose as observable outcomes, and the checks that observe
them. `validate` checks the set alone, without a node. Its rules are in README.md ("The set format").
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from . import probes, render

SUITE = Path(__file__).resolve().parents[2]
# The module the suite belongs to: its name is metadata.json's (the suite lives in the module's tree).
MODULE = json.loads((SUITE.parents[1] / "metadata.json").read_text(encoding="utf-8"))["name"]
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{1,62}")
CLASS = re.compile(r"[a-z][a-z0-9_]*")
# The values a run supplies (README.md, "Placeholders"); NODE:<kind> and ADDR:<kind> name a machine of another kind.
RUN_VALUES = {"NODE_NAME", "NODE_ADDR", "NODE_PRIMARY_ADDR", "NODE_NETWORK", "PEER_NAME", "PEER_ADDR", "SERVER_NAME",
              "SERVER_HOST", "SERVER_ADDR", "CONTROLLER_ADDR", "LOCALDIR"}
RUN_FAMILIES = {"NODE", "ADDR"}
PROSE_FAMILIES = {"SITE"}  # a site's own records, cited in prose for provenance; never needed to run a set
EXECUTED = {"probe", "effect", "stdout", "stdout_not"}
DUMMY = {**{v: "203.0.113.7" if v.endswith(("ADDR", "NETWORK")) else "x.example.invalid" for v in RUN_VALUES},
         "LOCALDIR": "/opt/site"}
DEFER_NEEDS = ("second-node", "browser", "rhel", "desktop")
SESSION_USER = re.compile(r"p8test[a-z0-9]*")
PEER_AGENT_CERT = re.compile(r"p8test[a-z0-9-]{0,40}")
VARIANT_KEYS = {"name", "why", "node", "params", "no_resources"}


def kinds(suite: Path = SUITE) -> dict:
    return yaml.safe_load((suite / "kinds.yml").read_text(encoding="utf-8"))


def load(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as err:
        raise ValueError(f"{path.name} is not valid YAML: {str(err).splitlines()[0]}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a YAML mapping")
    return data, raw


def placeholder_problems(data: dict) -> list[str]:
    out = []
    for name in sorted(render.needed(data, only=EXECUTED)):
        fam = name.split(":", 1)[0]
        if ":" in name and fam not in RUN_FAMILIES or ":" not in name and name not in RUN_VALUES:
            out.append(f"placeholder {{{{{name}}}}} in a probe or an expectation is not a value a run supplies")
    for name in sorted(render.needed(data)):
        fam = name.split(":", 1)[0]
        if ":" in name and fam not in RUN_FAMILIES | PROSE_FAMILIES or ":" not in name and name not in RUN_VALUES:
            out.append(f"placeholder {{{{{name}}}}} is unknown (README.md lists the placeholders)")
    return sorted(set(out))


def dummy_values(data: dict) -> dict:
    values = dict(DUMMY)
    for name in render.needed(data):
        if name.startswith("ADDR:"):
            values[name] = "203.0.113.9"
        elif ":" in name:
            values[name] = "y.example.invalid"
    return values


def uncovered_problems(u, where: str, known: dict) -> list[str]:
    if not isinstance(u, dict) or len(str(u.get("why", ""))) < 20:
        return [f"{where}: uncovered takes why (>= 20 characters)"]
    if "accepted_gap" in u:
        gap = u["accepted_gap"]
        if not isinstance(gap, list) or not gap or not all(isinstance(g, str) and re.fullmatch(r"\w+", g) for g in gap):
            return [f"{where}: accepted_gap lists the class's parameter names"]
        return []
    lifted = str(u.get("lifted_by", ""))
    if lifted.startswith("capability:"):
        return [] if len(lifted.split(":", 1)[1].strip()) >= 10 else [f"{where}: `capability: ...` names what is missing"]
    if lifted not in known:
        return [f"{where}: lifted_by names a node kind of kinds.yml or `capability: <what is missing>`"]
    return []


def outcome_problems(data: dict, known: dict) -> list[str]:
    rows = data.get("outcomes")
    if not isinstance(rows, list) or not rows:
        return ["outcomes: the purpose as observable outcomes, each mapped to checks or uncovered, is required"]
    ids = {c.get("id") for c in data.get("checks") or [] if isinstance(c, dict)}
    out = []
    for i, row in enumerate(rows):
        where = f"outcomes[{i}]"
        if not isinstance(row, dict) or len(str(row.get("outcome", ""))) < 15 or not str(row.get("from", "")).strip():
            out.append(f"{where}: takes outcome (>= 15 characters) and from (where the code says so)")
            continue
        if ("checks" in row) == ("uncovered" in row):
            out.append(f"{where}: maps to `checks` or is `uncovered`, exactly one of them")
        elif "checks" in row:
            refs = row["checks"]
            if not isinstance(refs, list) or not refs:
                out.append(f"{where}: checks lists at least one check id")
            else:
                out += [f"{where}: no check {r!r} in the set" for r in refs if r not in ids]
        else:
            out += uncovered_problems(row["uncovered"], f"{where}.uncovered", known)
    return out


def apply_problems(data: dict, cls: str, known: dict) -> list[str]:
    a = data.get("apply")
    if not isinstance(a, dict):
        return ["apply: the catalog the set applies (resource_type, node, catalog) is required"]
    out = []
    if a.get("resource_type") not in ("class", "define"):
        out.append("apply.resource_type is class or define")
    if a.get("resource_type") == "define" and not isinstance(a.get("title"), str):
        out.append("apply.title: a define's title is required")
    if a.get("node") not in known:
        out.append(f"apply.node {a.get('node')!r} is not a kind of kinds.yml")
    cat = a.get("catalog")
    if not isinstance(cat, dict) or not cat or not set(cat) <= {"Debian", "RedHat"}:
        out.append("apply.catalog maps an OS family (Debian, RedHat) to its list of classes")
    else:
        for fam, entries in cat.items():
            if not isinstance(entries, list) or not entries or entries[-1] != {"class": cls} or not all(
                    isinstance(e, dict) and (set(e) == {"external"} or set(e) == {"class"} or (
                        set(e) == {"class", "define"} and isinstance(e["define"], str) and e["define"]))
                    for e in entries):
                out.append(f"apply.catalog.{fam}: a list of {{class: ...}} (a base define with define: <title>) / "
                           "{external: ...} ending with the class")
    if "node_fixture" in a and not re.fullmatch(r"[a-z0-9_]+", str(a["node_fixture"])):
        out.append("apply.node_fixture names a manifest of fixtures/node/")
    events = a.get("expected_run2_events", [])
    if not isinstance(events, list) or not all(isinstance(e, str) and e for e in events):
        out.append("apply.expected_run2_events lists resource references")
    if "requires" in a and a["requires"] != ["server"]:
        out.append("apply.requires is [server] (a set that local apply cannot run)")
    if "requires" in a and len(str(a.get("requires_why", ""))) < 20:
        out.append("apply.requires_why: what the set needs a Puppet server for (a server fact, a file mount, ...)")
    return out


def check_problems(c, i: int, data: dict) -> list[str]:
    where = f"check {c.get('id', i) if isinstance(c, dict) else i}"
    if not isinstance(c, dict):
        return [f"{where}: not a mapping"]
    out = []
    if not SLUG.fullmatch(str(c.get("id", ""))):
        out.append(f"{where}: id must be a slug")
    if not c.get("what"):
        out.append(f"{where}: `what` is required")
    if c.get("control") not in ("negative", "invariant"):
        out.append(f"{where}: control must be negative|invariant")
    if c.get("control") == "invariant" and not c.get("why_invariant"):
        out.append(f"{where}: an invariant needs why_invariant")
    if any(isinstance(k, bool) for k in c):
        out.append(f"{where}: a key read as a boolean (YAML 1.1 `on:`/`yes:`); a peer probe is `host: peer`")
    mutating = "mutates" in c
    if "timeout" in c and (not mutating or not isinstance(c["timeout"], int) or not 1 <= c["timeout"] <= 600):
        out.append(f"{where}: timeout (seconds, 1-600) is for a mutating check's action only")
    if c.get("host", "node") not in ("node", "peer"):
        out.append(f"{where}: host must be node|peer")
    elif c.get("host") == "peer" and "peer" not in data:
        out.append(f"{where}: host: peer needs the set's `peer` block")
    if not isinstance(c.get("probe"), str) or not c["probe"].strip():
        out.append(f"{where}: probe is required")
    else:
        out += [f"{where}: {p}" for p in probes.probe_problems(c["probe"], mutating)]
    if mutating:
        if not isinstance(c["mutates"], str) or len(c["mutates"].strip()) < 10:
            out.append(f"{where}: mutates must declare what the action changes")
        if not isinstance(c.get("effect"), str) or not c["effect"].strip():
            out.append(f"{where}: a mutating check needs a read-only `effect` probe (the evidence)")
        else:
            out += [f"{where}: effect {p}" for p in probes.probe_problems(c["effect"])]
        if c.get("control") != "negative":
            out.append(f"{where}: a mutating check is a negative control")
    elif "effect" in c:
        out.append(f"{where}: `effect` without `mutates`")
    mm = c.get("mismatch")
    verdict_of = probes.tool_verdict(c["probe"]) if isinstance(c.get("probe"), str) and not mutating else None
    if mm is None and verdict_of:
        out.append(f"{where}: the probe takes a tool's verdict ({verdict_of}); a `mismatch` control is mandatory")
    if mm is not None:
        if mutating:
            out.append(f"{where}: a mutating check takes no mismatch control (its evidence is the effect)")
        elif not isinstance(mm, dict) or set(mm) != {"varies", "probe"} or len(str(mm.get("varies", ""))) < 10:
            out.append(f"{where}: mismatch takes `varies` (>= 10 characters) and `probe`")
        elif str(mm["probe"]).strip() == str(c.get("probe", "")).strip():
            out.append(f"{where}: mismatch.probe is identical to the probe")
        else:
            out += [f"{where}: mismatch {p}" for p in probes.probe_problems(str(mm["probe"]))]
    exp = c.get("expect") or {}
    if not isinstance(exp, dict) or not set(exp) <= {"rc", "stdout", "stdout_not"}:
        out.append(f"{where}: expect takes rc, stdout, stdout_not")
    else:
        for k in ("stdout", "stdout_not"):
            if k in exp:
                try:
                    re.compile(render.render(str(exp[k]), dummy_values(data)), re.M)
                except (re.error, KeyError, ValueError) as err:
                    out.append(f"{where}: expect.{k} is not a regex ({err})")
    return out


def block_problems(data: dict, known: dict) -> list[str]:
    out = []
    mutating = [c.get("id") for c in data.get("checks") or [] if isinstance(c, dict) and "mutates" in c]
    peer = data.get("peer")
    if peer is not None:
        if not isinstance(peer, dict) or not set(peer) <= {"kind", "why", "files"} or len(str(peer.get("why", ""))) < 20:
            out.append("peer takes kind, why (>= 20 characters) and optional files")
        elif "second-node" not in (known.get(peer.get("kind")) or {}).get("capabilities", []):
            out.append(f"peer: kind {peer.get('kind')!r} is not a second-node kind of kinds.yml")
        elif not all(isinstance(f, str) and re.fullmatch(r"/[\w./-]+", f) for f in peer.get("files") or []):
            out.append("peer.files is a list of absolute paths on the node")
    session = data.get("session")
    if session is not None and (not isinstance(session, dict) or set(session) != {"user", "desktop", "why"} or
                                not SESSION_USER.fullmatch(str(session.get("user"))) or session.get("desktop") != "plasma"):
        out.append("session takes user (a p8test* account), desktop (plasma) and why")
    pa = data.get("peer_agent")
    if pa is not None and (not isinstance(pa, dict) or set(pa) != {"after", "certname", "why"} or "peer" not in data or
                           not PEER_AGENT_CERT.fullmatch(str(pa.get("certname"))) or pa.get("after") not in mutating):
        out.append("peer_agent takes after (a mutating check), certname (a p8test* identity) and why, with a peer")
    na = data.get("node_agent")
    if na is not None:
        anchors = na.get("after") if isinstance(na, dict) else None
        anchors = anchors if isinstance(anchors, list) else [anchors]
        if not isinstance(na, dict) or set(na) != {"after", "why"} or any(a not in mutating for a in anchors):
            out.append("node_agent takes after (a mutating check, or a list of them) and why")
    return out


def variant_problems(data: dict, checks: list, known: dict, params_found) -> list[str]:
    variants = data.get("variants")
    tagged = [c for c in checks if isinstance(c, dict) and "variant" in c]
    if variants is None:
        return [f"check {c.get('id')}: `variant` names no variant (the set has no `variants`)" for c in tagged]
    if not isinstance(variants, list) or not variants:
        return ["variants must be a non-empty list"]
    out, names = [], set()
    for i, v in enumerate(variants):
        where = f"variant {v.get('name', i) if isinstance(v, dict) else i}"
        if not isinstance(v, dict) or not set(v) <= VARIANT_KEYS or not {"name", "why"} <= set(v):
            out.append(f"{where}: takes name, why and node and/or params")
            continue
        if not SLUG.fullmatch(str(v["name"])) or v["name"] in names:
            out.append(f"{where}: name must be a unique slug")
        names.add(v["name"])
        if "node" not in v and "params" not in v:
            out.append(f"{where}: needs node and/or params")
        if "node" in v and v["node"] not in known:
            out.append(f"{where}: node {v['node']!r} is not a kind of kinds.yml")
        if "params" in v and not SLUG.fullmatch(str(v["params"])):
            out.append(f"{where}: params must be a slug")
        elif "params" in v and params_found is not None and not params_found(v["params"]):
            out.append(f"{where}: no params fixture for variant params {v['params']!r}")
    for c in tagged:
        if c["variant"] not in names:
            out.append(f"check {c.get('id')}: variant {c['variant']!r} is not declared")
        if c.get("host") == "peer":
            out.append(f"check {c.get('id')}: a variant run has no peer")
    for name in names:
        if not any(c.get("variant") == name and c.get("control") == "negative" for c in tagged):
            out.append(f"variant {name}: needs >= 1 negative control of its own")
    return out


def validate(path: Path, suite: Path = SUITE, params_found=None) -> list[str]:
    """The set's problems (empty when valid). `params_found(variant_or_None)` says whether a params fixture exists
    (None: not checked here, the runner checks it)."""
    cls = path.stem
    try:
        data, _ = load(path)
    except ValueError as err:
        return [str(err)]
    known = kinds(suite)
    out = []
    if data.get("class") != cls:
        out.append(f"class {data.get('class')!r} != the file name {cls!r}")
    if not CLASS.fullmatch(cls):
        out.append(f"{cls!r} is not a class name")
    if len(str(data.get("purpose") or "").strip()) < 40:
        out.append("purpose: the class's purpose (one or two sentences, >= 40 characters) is required")
    out += placeholder_problems(data)
    if "deferred" in data:
        d = data["deferred"]
        if not isinstance(d, dict) or d.get("needs") not in DEFER_NEEDS or len(str(d.get("why", "")).strip()) < 20:
            out.append(f"deferred needs `needs` ({'|'.join(DEFER_NEEDS)}) and a `why` of at least 20 characters")
        if "checks" in data:
            out.append("a deferred set has no checks")
        return out
    if data.get("fixture") not in ("params", "defaults"):
        out.append("fixture must be `params` or `defaults`")
    elif data["fixture"] == "params" and params_found is not None and not params_found(None):
        out.append("fixture: params, but there is no params fixture for the class")
    out += outcome_problems(data, known)
    out += apply_problems(data, cls, known)
    out += block_problems(data, known)
    checks = data.get("checks")
    if not isinstance(checks, list) or not checks:
        return out + ["no checks"]
    ids = [c.get("id") for c in checks if isinstance(c, dict)]
    if len(ids) != len(set(ids)):
        out.append("check ids must be unique")
    for i, c in enumerate(checks):
        out += check_problems(c, i, data)
    if not any(isinstance(c, dict) and c.get("control") == "negative" and "variant" not in c for c in checks):
        out.append("no negative control: at least one check of the base run must fail on the clean node")
    out += variant_problems(data, checks, known, params_found)
    return out
