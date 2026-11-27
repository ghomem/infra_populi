#!/usr/bin/env python3
"""The fixtures the public suite can carry (HQ review of design note F, rulings 2 and 6).

  fixtures_move.py check          which local params files and node fixtures become suite fixtures, and why others stay
  fixtures_move.py write          writes them to spec/behaviour/fixtures/{params,node} (short names) and the record
                                  .codex_state/checks/fixtures_moved.json
  fixtures_move.py verify         each suite fixture, rendered with the lab's values of every run that uses it, still
                                  equals the engine's file (exit 1 if not; params are skipped where the local dir is
                                  absent)

Node fixtures (.codex_state/tools/tests/fixtures/node/<name>.pp, the harness's stand-ins) move with their Puppet code
neutral: the code lines, rendered with the lab's values of each set that names the fixture, equal the engine's code
lines; the engine's comments (its authoring history) stay with the engine's copy, the suite's copy says what it is.

The local params directory (~/.config/infra_populi/params, P8_PARAMS_DIR) stays the harness's source of record: the
suite's copy is derived from it and proven neutral, as the sets were. A file moves when:
  - every run that uses it (each set whose catalog declares the class, on each of the set's node kinds, base and
    variants) renders the template back to exactly the local file: the lab's values become placeholders by role
    (CONTROLLER_ADDR, SERVER_NAME, PEER_ADDR+100, ...) only where the role means the same machine in every such run;
  - no lab value is left;
  - every value is plainly fake (suite_check.fake_problems).
A file no set uses is judged with its class's base run.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(REPO / "spec" / "behaviour" / "lib"))

import behaviour_move as bm  # noqa: E402
import module_name  # noqa: E402
import suite_check  # noqa: E402
import yaml  # noqa: E402
from behaviour import render as rn  # noqa: E402

LOCAL = Path(os.environ.get("P8_PARAMS_DIR") or Path.home() / ".config" / "infra_populi" / "params")
OUT = REPO / "spec" / "behaviour" / "fixtures" / "params"
RECORD = REPO / ".codex_state" / "checks" / "fixtures_moved.json"
NODE_IN = TOOLS / "tests" / "fixtures" / "node"
NODE_OUT = REPO / "spec" / "behaviour" / "fixtures" / "node"
PREFIX = f"{bm.MODULE}::"


def short(rel: Path) -> Path:
    """The path with the module prefix removed from each part (either name: the record keeps the old one)."""
    return Path(*[module_name.short(p) for p in rel.parts])


def now(rel: Path) -> Path:
    """A recorded params path as it is named under the module's current name (the record keeps the old one)."""
    return Path(module_name.to_current(str(rel)))


def current(obj):
    """A rendered fixture as it reads under the module's current name: the proof was made under the old one, and the
    rename changed both sides alike (the identity until the module is renamed)."""
    if isinstance(obj, dict):
        return {module_name.to_current(k): current(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [current(v) for v in obj]
    return module_name.to_current(obj) if isinstance(obj, str) else obj


def sets() -> dict:
    out = {}
    for p in sorted(bm.NEW_DIR.glob("*.yml")):
        data = yaml.safe_load(p.read_text())
        if isinstance(data, dict) and "apply" in data:
            out[p.stem] = data
    return out


def uses(rel: Path, all_sets: dict) -> list[tuple[str, str, dict]]:
    """(set, run, lab values) of every run that reads this file (the harness's lookup, first match wins)."""
    kinds = bm.nodes_data()["nodes"]
    parts = short(rel).parts
    out = []
    for target, data in all_sets.items():
        ctxs = bm.contexts(target, data)
        runs = [("base", data["apply"]["node"], None)] + [
            (v["name"], v.get("node", data["apply"]["node"]), v.get("params")) for v in data.get("variants") or []]
        for run, kind, slug in runs:
            family = kinds[kind]["os_family"]
            declared = [e["class"] for e in data["apply"]["catalog"].get(family, []) if "class" in e]
            if parts[0] == "for":
                hit = parts[1] == target and parts[2][:-5] in declared
            elif parts[0] == "variants":
                hit = parts[1] == slug and parts[2][:-5] == target
            else:
                cls = parts[0][:-5]
                shadowed = (cls == target and slug and (LOCAL / "variants" / slug / f"{PREFIX}{target}.json").is_file()) \
                    or (LOCAL / "for" / f"{PREFIX}{target}" / f"{PREFIX}{cls}.json").is_file()
                hit = cls in declared and not shadowed
            if hit:
                out.append((target, run, ctxs[run]))
    return out


def strings_map(obj, fn):
    if isinstance(obj, dict):
        return {fn(k) if isinstance(k, str) else k: strings_map(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strings_map(v, fn) for v in obj]
    return fn(obj) if isinstance(obj, str) else obj


def common(ctxs: list[dict]) -> dict:
    """The values that mean the same in every run (a role whose machine differs between runs is left out)."""
    first = ctxs[0]
    return {k: v for k, v in first.items() if all(c.get(k) == v for c in ctxs[1:])}


def judge(rel: Path, all_sets: dict) -> tuple[dict | None, str]:
    original = json.loads((LOCAL / rel).read_text())
    used = uses(rel, all_sets)
    if not used:
        cls = short(rel).parts[-1][:-5]
        kinds = bm.nodes_data()["nodes"]
        kind = bm.base_kind(cls) if cls in bm.plan_rows() else "ubuntu"
        used = [(cls, "base", bm.context(kinds, kind, None))]
    ctxs = [c for _, _, c in used]
    values = common(ctxs)
    template = strings_map(original, lambda s: bm.templatise(s, values, "probe"))
    for target, run, ctx in used:
        try:
            back = strings_map(template, lambda s: rn.render(s, ctx))
        except (KeyError, ValueError) as err:
            return None, f"does not render for {target} ({run}): {err}"
        if back != original:
            return None, f"not neutral for {target} ({run})"
    left = sorted({v for c in ctxs for v in bm.lab_left(template, {"x": c})}) if hasattr(bm, "lab_left") else []
    if left:
        return None, f"names a lab value no single role covers: {', '.join(left[:3])}"
    fake = sorted({p for s in suite_check.strings(template) for p in suite_check.fake_problems(s)})
    if fake:
        return None, f"not plainly fake: {fake[0]}"
    return template, f"used by {len({t for t, _, _ in used})} set(s), {len(used)} run(s)"


def code(text: str) -> list[str]:
    return [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def node_uses(name: str, all_sets: dict) -> list[tuple[str, dict]]:
    return [(t, bm.contexts(t, d)["base"]) for t, d in all_sets.items() if d["apply"].get("node_fixture") == name]


def judge_node(name: str, all_sets: dict) -> tuple[str | None, str]:
    original = code((NODE_IN / f"{name}.pp").read_text())
    used = node_uses(name, all_sets)
    if not used:
        return None, "no set names it"
    ctxs = [c for _, c in used]
    values = common(ctxs)
    lines = [bm.templatise(l, values, "probe") for l in original]
    for target, ctx in used:
        if [rn.render(l, ctx) for l in lines] != original:
            return None, f"not neutral for {target}"
    left = sorted({v for c in ctxs for v in bm.lab_left({"probe": "\n".join(lines)}, {"x": c})})
    if left:
        return None, f"names a lab value no single role covers: {', '.join(left[:3])}"
    head = [f"# Node fixture {name}: stand-ins the class under test expects on the node (a service, a path or a user",
            "# the test node does not have). Applied before the class; placeholders are filled from the run."]
    text = "\n".join(head + lines) + "\n"
    found = suite_check.text_problems(text, suite_check.lab_values(), suite_check.engine_files())
    if found:
        return None, found[0]
    return text, f"used by {', '.join(t for t, _ in used)}"


def local_files() -> list[Path]:
    return sorted(p.relative_to(LOCAL) for p in LOCAL.rglob("*.json"))


def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    mode = argv[0] if argv else ""
    if mode not in ("check", "write", "verify"):
        print(__doc__)
        return 2
    all_sets = sets()
    if mode == "verify":
        record = json.loads(RECORD.read_text())
        bad = 0
        for name in record.get("node", {}):
            ctxs = node_uses(name, all_sets)
            lines = code((NODE_OUT / f"{name}.pp").read_text())
            original = code((NODE_IN / f"{name}.pp").read_text())
            wrong = [t for t, c in ctxs if [module_name.to_current(rn.render(l, c)) for l in lines] != original]
            print(f"NOT NEUTRAL node/{name}: {', '.join(wrong)}" if wrong or not ctxs else f"NEUTRAL node/{name}")
            bad += bool(wrong or not ctxs)
        record = record.get("params", {})
        for rel_s, entry in sorted(record.items()):
            rel, new = Path(rel_s), OUT / entry["fixture"]
            if not (LOCAL / now(rel)).is_file():  # another machine: the operator's params are not here
                print(f"NO LOCAL {rel_s}")
                continue
            template = json.loads(new.read_text())
            original = json.loads((LOCAL / now(rel)).read_text())
            used = uses(rel, all_sets) or [("-", "base", bm.context(bm.nodes_data()["nodes"], "ubuntu", None))]
            wrong = [f"{t} ({r})" for t, r, c in used
                     if current(strings_map(template, lambda s, c=c: rn.render(s, c))) != original]
            print(f"NOT NEUTRAL {rel_s}: {', '.join(wrong[:3])}" if wrong else f"NEUTRAL {rel_s}")
            bad += bool(wrong)
        print(f"{len(record) + len(json.loads(RECORD.read_text()).get('node', {})) - bad} neutral, {bad} not neutral")
        return 1 if bad else 0
    nodes, moved, kept = {}, {}, {}
    for p in sorted(NODE_IN.glob("*.pp")):
        text, why = judge_node(p.stem, all_sets)
        if text is None:
            kept[f"node/{p.name}"] = why
        else:
            nodes[p.stem] = text
    for rel in local_files() if LOCAL.is_dir() else []:
        template, why = judge(rel, all_sets)
        if template is None:
            kept[str(rel)] = why
            continue
        moved[str(rel)] = (template, why)
    for rel, why in kept.items():
        print(f"LOCAL {rel}: {why}")
    print(f"{len(moved)} params and {len(nodes)} node fixtures move, {len(kept)} stay with the engine")
    if mode == "write":
        record = {"node": {}, "params": {}}
        NODE_OUT.mkdir(parents=True, exist_ok=True)
        for name, text in nodes.items():
            (NODE_OUT / f"{name}.pp").write_text(text)
            record["node"][name] = {"engine_sha256": hashlib.sha256((NODE_IN / f"{name}.pp").read_bytes()).hexdigest()}
        for rel, (template, _) in moved.items():
            dest = OUT / short(Path(rel))
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(dump(template))
            record["params"][rel] = {"fixture": str(short(Path(rel))),
                           "local_sha256": hashlib.sha256((LOCAL / rel).read_bytes()).hexdigest()}
        RECORD.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
