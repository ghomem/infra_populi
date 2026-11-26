#!/usr/bin/env python3
"""Move the Phase 3 check sets into the public behaviour suite (spec/behaviour/), provably neutral (HQ review of
design note F, ruling 6).

  behaviour_move.py check [<class> ...]   dry run: convert each set and run the neutrality check; prints one line per
                                           set (NEUTRAL / NOT NEUTRAL with the first difference), exit 1 if any is not
  behaviour_move.py write [<class> ...]   the same, then writes each NEUTRAL set to spec/behaviour/checks/<class>.yml,
                                           its comments to .codex_state/checks/notes/<class>.md and its identities to
                                           .codex_state/checks/moved.json (no class = every set)

The conversion replaces the lab's values with the suite's placeholders ({{NAME}}, spec/behaviour/lib/behaviour/
render.py): the run's machines and site paths in every string, the engine's records and tools cited in prose
({{SITE:...}}), and the runner variable P8_PEER_ADDR becomes PEER_ADDR (ruling 4). YAML comments (the authoring
history) leave the public file for the engine's notes. Each set gains an `apply:` block: the catalog the harness
builds for it (from the plan), so a runner without the plan can build it.

NEUTRAL means: the new set, rendered with the lab's values (per run: the base run's node and peer, each variant's
node) and with PEER_ADDR named back P8_PEER_ADDR, equals the old set parsed, every string byte for byte, apart from
the added `apply:` block. A neutral set's reviews stay valid: moved.json ties the new file to the old one's identity.
"""

from __future__ import annotations

import functools
import hashlib
import ipaddress
import json
import re
import sys
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
STATE = REPO / ".codex_state"
SUITE = REPO / "spec" / "behaviour"
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(STATE))
sys.path.insert(2, str(SUITE / "lib"))
from behaviour import render as rn  # noqa: E402

OLD_DIR = STATE / "checks"
NEW_DIR = SUITE / "checks"
NOTES_DIR = STATE / "checks" / "notes"
MOVED = STATE / "checks" / "moved.json"
MODULE = "puppet_infrastructure"

# The lab's fixed values (nodes.yml holds the nodes).
LAB = {
    "SERVER_NAME": "puppet8master.example.com",
    "SERVER_HOST": "puppet8master",
    "SERVER_ADDR": "192.168.56.10",
    "CONTROLLER_ADDR": "192.168.56.1",
    "NODE_NETWORK": "192.168.56.0",
    "NODE_PRIMARY_ADDR": "10.0.2.15",
    "LOCALDIR": "/opt/puppet-infrastructure",
}
# The engine's records and tools that the prose cites, each a placeholder of its own (rendered back exactly).
SITE = {
    ".codex_state/lab/nodes.yml": "node-inventory-file",
    "diagnosis/fleet_variant_usage.md": "fleet-usage",
    "escalations/firewall_secure_extra.behaviour.md": "escalation-firewall-secure-extra",
    "escalations/openvpn_server.behaviour.md": "escalation-openvpn-server",
    "approval_conditions.md": "approval-conditions",
    "class_rulings.txt": "class-rulings",
    "migration_plan.md": "plan-file",
    "node_inventory.py": "node-inventory-tool",
    "DESIGN_DECISIONS": "design-decisions",
    "clock_check.py": "clock-check",
    "test_class.sh": "harness",
    "CLAUDE.md": "project-instructions",
    "phase3.py": "engine-runner",
    "status.py": "status-tool",
    "nodes.yml": "node-inventory",
    "nodes.py": "node-inventory-reader",
}
EXECUTED = {"probe", "effect", "stdout", "stdout_not"}  # strings a run sends to a node or matches against output
REGEXES = {"stdout", "stdout_not"}


@functools.lru_cache(maxsize=None)
def nodes_data() -> dict:
    import nodes  # noqa: PLC0415
    return nodes.load()


def base_kind(cls: str) -> str:
    """The class's own node kind: the plan's `node` (read once), else the inventory's default (nodes.select's rule)."""
    import nodes  # noqa: PLC0415
    row = plan_rows().get(cls)
    planned = getattr(row, "node", "") if row is not None else ""
    return nodes.select(nodes_data(), kind=planned or None)["kind"]


def kind_values(kinds: dict) -> dict:
    """Each node kind's name and address, for a set that names a machine outside its own runs."""
    return {**{f"NODE:{k}": v["hostname"] for k, v in kinds.items()},
            **{f"ADDR:{k}": v["hostonly_ip"] for k, v in kinds.items()}}


def context(kinds: dict, node_kind: str, peer_kind: str | None) -> dict:
    node = kinds[node_kind]
    values = {**LAB, **kind_values(kinds), **{f"SITE:{slug}": lit for lit, slug in SITE.items()},
              "NODE_NAME": node["hostname"], "NODE_ADDR": node["hostonly_ip"]}
    if peer_kind:
        values.update(PEER_NAME=kinds[peer_kind]["hostname"], PEER_ADDR=kinds[peer_kind]["hostonly_ip"])
    return values


def contexts(cls: str, data: dict) -> dict:
    """The lab's values per run: 'base', and each variant's name. A variant run keeps the base run's peer values (it
    has no peer of its own, but its fixtures may name the peer's addresses)."""
    kinds = nodes_data()["nodes"]
    mine = base_kind(cls)
    peer_kind = (data.get("peer") or {}).get("kind")
    out = {"base": context(kinds, mine, peer_kind)}
    for v in data.get("variants") or []:
        if isinstance(v, dict) and "name" in v:
            out[v["name"]] = context(kinds, v.get("node", mine), peer_kind)
    return out


# ------------------------------------------------------------------ lab values -> placeholders

ADDR = re.compile(r"(?<![\d.])(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?![\d])")
ESCAPED_ADDR = re.compile(r"(?<![\d.\\])(\d{1,3}\\\.\d{1,3}\\\.\d{1,3}\\\.\d{1,3})(?![\d])")  # in a regex


START = r"(?:(?<=\\[A-Za-z])|(?<![\w.-]))"  # a token start; a regex escape such as \A or \n before it counts as one


def word(value: str) -> re.Pattern:
    """A value as a whole token: not inside a longer name, word or address."""
    return re.compile(rf"{START}{re.escape(value)}(?![\w-]|\.\d)")


def templatise(text: str, values: dict, field: str | None) -> str:
    """Replace the lab's values in one string with placeholders. Executed strings name the run's machines by role;
    prose names other node kinds as {{NODE:<kind>}} and cites the engine's records as {{SITE:...}}."""
    executed = field in EXECUTED
    if not executed:
        for literal in sorted(SITE, key=len, reverse=True):
            text = re.sub(rf"(?<![\w/.-]){re.escape(literal)}(?![\w])", "{{SITE:%s}}" % SITE[literal], text)
    text = re.sub(r"\bP8_PEER_ADDR\b", "PEER_ADDR", text)
    roles = ["SERVER_NAME", "LOCALDIR", "NODE_NAME", "PEER_NAME", "SERVER_HOST"]
    named = [(values[r], "{{%s}}" % r) for r in roles if r in values]
    if not executed:  # prose: a lab machine by its kind, not by its role in this run
        named = [(v, p) for v, p in named if p not in ("{{NODE_NAME}}", "{{PEER_NAME}}")]
    named += [(v, "{{%s}}" % k) for k, v in values.items() if k.startswith("NODE:")]
    seen, ordered = set(), []
    for v, p in sorted(named, key=lambda vp: len(vp[0]), reverse=True):
        if v not in seen:
            seen.add(v)
            ordered.append((v, p))
    for value, ph in ordered:
        if field in REGEXES:
            esc = rn.re_escape(value)
            if esc != value:
                text = re.sub(rf"{START}{re.escape(esc)}(?![\w-])", ph[:-2] + "|re}}", text)
        text = word(value).sub(ph, text)
    roles_addr = {values[r]: r for r in ("NODE_ADDR", "PEER_ADDR", "SERVER_ADDR", "CONTROLLER_ADDR", "NODE_NETWORK",
                                         "NODE_PRIMARY_ADDR") if r in values}

    def name_of(a: str) -> str | None:
        """The placeholder (without braces) for a lab address, or None for an address that is not the lab's."""
        if a in roles_addr:
            return roles_addr[a]
        by_kind = [k for k, v in values.items() if k.startswith("ADDR:") and v == a]
        if by_kind:
            return by_kind[0]
        try:
            ip = ipaddress.IPv4Address(a)
        except ValueError:
            return None
        base = values.get("PEER_ADDR") or values.get("NODE_ADDR")
        role = "PEER_ADDR" if values.get("PEER_ADDR") else "NODE_ADDR"
        if base and ip in ipaddress.IPv4Network(f"{values['NODE_NETWORK']}/24"):
            n = int(a.rsplit(".", 1)[1]) - int(base.rsplit(".", 1)[1])
            if n > 0:
                return f"{role}+{n}"
        return None

    if field in REGEXES:
        def escaped(m: re.Match) -> str:
            ph = name_of(m.group(1).replace("\\.", "."))
            return "{{%s|re}}" % ph if ph else m.group(0)
        text = ESCAPED_ADDR.sub(escaped, text)

    def addr(m: re.Match) -> str:
        ph = name_of(m.group(1))
        return "{{%s}}" % ph if ph else m.group(1)
    return ADDR.sub(addr, text)


def lab_left(data, values_by_run: dict) -> set[str]:
    """Lab values still written literally in a converted set (none may be: no lab-specific names)."""
    lab = set()
    for values in values_by_run.values():
        lab |= {v for k, v in values.items() if not k.startswith("SITE:") and k != "LOCALDIR"}
        lab.add(values["LOCALDIR"])
    found: set[str] = set()

    def look(s, f):
        for v in lab:
            if word(v).search(s) or (f in REGEXES and rn.re_escape(v) != v and
                                     re.search(rf"{START}{re.escape(rn.re_escape(v))}(?![\w-])", s)):
                found.add(v)
        return s
    walk(data, look)
    return found


def walk(obj, fn, field=None):
    if isinstance(obj, dict):
        return {k: walk(v, fn, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk(v, fn, field) for v in obj]
    if isinstance(obj, str):
        return fn(obj, field)
    return obj


def per_run(data: dict, ctxs: dict, fn) -> dict:
    """Apply fn(string, field, values) to the set, each check with its run's values (a variant's check, its variant's)."""
    out = {}
    for k, v in data.items():
        if k == "checks" and isinstance(v, list):
            out[k] = [walk(c, lambda s, f, vals=ctxs.get(c.get("variant"), ctxs["base"]): fn(s, f, vals))
                      if isinstance(c, dict) else c for c in v]
        elif k == "variants" and isinstance(v, list):
            out[k] = [walk(x, lambda s, f, vals=ctxs.get(x.get("name"), ctxs["base"]): fn(s, f, vals))
                      if isinstance(x, dict) else x for x in v]
        else:
            out[k] = walk(v, lambda s, f: fn(s, f, ctxs["base"]), k)
    return out


def to_template(data: dict, ctxs: dict) -> dict:
    return per_run(data, ctxs, lambda s, f, vals: templatise(s, vals, f))


def to_lab(data: dict, ctxs: dict) -> dict:
    """The template rendered with the lab's values, PEER_ADDR named back P8_PEER_ADDR (the old sets' name)."""
    def one(s, f, vals):
        out = rn.render(s, vals)
        return re.sub(r"(?<!\w)PEER_ADDR\b", "P8_PEER_ADDR", out)
    return per_run(data, ctxs, one)


# ------------------------------------------------------------------ the apply recipe (from the plan)

@functools.lru_cache(maxsize=None)
def plan_rows() -> dict:
    import gen_migration_order as gen  # noqa: PLC0415
    return gen.parse_plan()


def expand(cls: str, rows: dict, family: str) -> list[dict]:
    """The harness's catalog for `cls` on a node of `family`: bases first (recursively), then externals, then the class
    (test_class.sh expand_one_class); a Debian-only external (apt) is not declared on RedHat."""
    out, state = [], {}

    def bases_of(row) -> list[str]:
        found = []
        for b in getattr(row, "required_base", None) or []:
            m = re.fullmatch(r"(?:\[(Debian|RedHat)\])?(?:puppet_infrastructure::)?(\w+)", str(b).strip())
            if m and (not m.group(1) or m.group(1) == family):
                found.append(m.group(2))
        return found

    def one(name: str, kind: str):
        k = f"{kind}:{name}"
        if state.get(k) == 2:
            return
        if state.get(k) == 1:
            raise SystemExit(f"circular required_base at {name}")
        state[k] = 1
        if kind == "internal":
            row = rows.get(name)
            for b in bases_of(row) if row else []:
                one(b, "internal")
            for e in (getattr(row, "required_external", None) or []) if row else []:
                if e == "apt" and family == "RedHat":
                    continue
                one(e, "external")
        state[k] = 2
        out.append({"external": name} if kind == "external" else {"class": name})
    one(cls, "internal")
    return out


def apply_block(cls: str, data: dict, ctx_kinds: dict) -> dict:
    rows = plan_rows()
    row = rows.get(cls)
    kinds = nodes_data()["nodes"]
    families = sorted({kinds[k]["os_family"] for k in ctx_kinds})
    block = {"resource_type": getattr(row, "resource_type", None) or "class"}
    title = getattr(row, "title", None)
    if title:
        block["title"] = title
    block["catalog"] = {fam: [dict(e) for e in expand(cls, rows, fam)] for fam in families}
    fixture = getattr(row, "node_fixture", None)
    if fixture:
        block["node_fixture"] = fixture
    events = list(getattr(row, "expected_run2_events", None) or [])
    if events:
        block["expected_run2_events"] = events
    return block


# ------------------------------------------------------------------ YAML out

class Dumper(yaml.SafeDumper):
    pass


def _str(dumper, s: str):
    if "\n" in s and not any(line != line.rstrip() for line in s.split("\n")) and "\t" not in s:
        return dumper.represent_scalar("tag:yaml.org,2002:str", s, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", s)


Dumper.add_representer(str, _str)


def dump(data: dict) -> str:
    return yaml.dump(data, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=120, default_flow_style=False)


# ------------------------------------------------------------------ check / write

def first_difference(a, b, path="") -> str | None:
    if type(a) is not type(b):
        return f"{path}: {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a or k not in b:
                return f"{path}.{k}: only in {'old' if k in a else 'new'}"
            d = first_difference(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: {len(a)} items != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_difference(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} != {b!r}"[:400]
    return None


def convert(cls: str) -> tuple[dict, str, str | None]:
    """(new set, its YAML text, the first difference that makes it not neutral or None)."""
    raw = (OLD_DIR / f"{cls}.yml").read_text(encoding="utf-8")
    old = yaml.safe_load(raw)
    ctxs = contexts(cls, old)
    new = to_template(old, ctxs)
    if "deferred" not in old:
        run_kinds = {base_kind(cls)} | {v["node"] for v in old.get("variants") or []
                                        if isinstance(v, dict) and "node" in v}
        new["apply"] = apply_block(cls, old, run_kinds)
    left = lab_left({k: v for k, v in new.items() if k != "apply"}, ctxs)
    if left:
        return new, dump(new), f"lab values left in the set: {sorted(left)}"
    text = dump(new)
    reread = yaml.safe_load(text)
    if reread != new:
        return new, text, f"the YAML text does not read back as the converted set: {first_difference(new, reread)}"
    leftover = rn.needed({k: v for k, v in reread.items() if k != "apply"}) - set().union(*ctxs.values())
    if leftover:
        return new, text, f"placeholders without a lab value: {sorted(leftover)}"
    lab = to_lab({k: v for k, v in reread.items() if k != "apply"}, ctxs)
    return new, text, first_difference(old, lab)


def comments(raw: str) -> str:
    return "".join(line for line in raw.splitlines(keepends=True) if line.lstrip().startswith("#"))


def all_classes() -> list[str]:
    return sorted(p.stem for p in OLD_DIR.glob("*.yml"))


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("check", "write"):
        print(__doc__)
        return 2
    classes = argv[1:] or all_classes()
    moved = json.loads(MOVED.read_text()) if MOVED.is_file() else {}
    bad = 0
    for cls in classes:
        try:
            new, text, diff = convert(cls)
        except (KeyError, ValueError, SystemExit) as err:
            new, text, diff = None, "", f"conversion failed: {err}"
        if diff:
            bad += 1
            print(f"NOT NEUTRAL {cls}: {diff}")
            continue
        print(f"NEUTRAL {cls}")
        if argv[0] == "write":
            raw = (OLD_DIR / f"{cls}.yml").read_bytes()
            NEW_DIR.mkdir(parents=True, exist_ok=True)
            (NEW_DIR / f"{cls}.yml").write_text(text, encoding="utf-8")
            note = comments(raw.decode("utf-8"))
            NOTES_DIR.mkdir(parents=True, exist_ok=True)
            (NOTES_DIR / f"{cls}.md").write_text(
                f"# {cls}: authoring notes (the comments of .codex_state/checks/{cls}.yml, moved here when the set "
                "moved to spec/behaviour/checks/)\n\n```\n" + note + "```\n", encoding="utf-8")
            import phase3  # noqa: PLC0415
            moved[cls] = {"old_sha256": hashlib.sha256(raw).hexdigest(), "old_content_sha256": phase3.content_sha(raw),
                          "new_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    if argv[0] == "write":
        MOVED.write_text(json.dumps(moved, indent=1, sort_keys=True) + "\n")
    print(f"{len(classes) - bad} neutral, {bad} not neutral")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
