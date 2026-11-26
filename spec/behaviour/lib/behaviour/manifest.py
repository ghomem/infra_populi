"""The manifest a run applies: a set's `apply` block made Puppet code.

In the order the set gives: its node fixture first (stand-ins for a service the node does not run), then each catalog
entry: a module's base class (`include <module>`), or one of this module's classes declared with its params fixture
(a define with its title), or plainly included when it has none.

Params fixtures are looked up, first match wins, in each params directory given (the suite's own fake fixtures, then
the operator's):  for/<target>/<class>.json  (the class as a base of this target)
                  variants/<variant>/<target>.json  (a variant's own params for the target)
                  kinds/<kind>/<class>.json  (the class on that node kind)
                  <class>.json
where <class> is the short name (no module prefix).
"""

from __future__ import annotations

import json
from pathlib import Path

MODULE = "puppet_infrastructure"


def literal(v) -> str:
    if v is None:
        return "undef"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(v, list):
        return "[" + ", ".join(literal(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{literal(str(k))} => {literal(x)}" for k, x in v.items()) + "}"
    raise TypeError(type(v))


def params_file(cls: str, target: str, kind: str, variant: str | None, dirs: list[Path]) -> Path | None:
    for d in dirs:
        candidates = [d / "for" / target / f"{cls}.json"]
        if variant and cls == target:
            candidates.append(d / "variants" / variant / f"{target}.json")
        candidates += [d / "kinds" / kind / f"{cls}.json", d / f"{cls}.json"]
        for c in candidates:
            if c.is_file():
                return c
    return None


def family_of(kind: str, kinds: dict) -> str:
    return kinds[kind]["os_family"]


def build(data: dict, kind: str, kinds: dict, params_dirs: list[Path], fixtures: Path,
          variant: str | None = None, render=lambda s: s) -> str:
    """The manifest for the set on a node of `kind`. `render` fills the placeholders a params fixture may carry."""
    apply = data["apply"]
    target = data["class"]
    lines = []
    if apply.get("node_fixture"):
        path = fixtures / "node" / f"{apply['node_fixture']}.pp"
        if not path.is_file():
            raise FileNotFoundError(f"node fixture {apply['node_fixture']} not found ({path})")
        lines += [f"# node fixture: {apply['node_fixture']}", path.read_text(encoding="utf-8").rstrip("\n")]
    family = family_of(kind, kinds)
    for entry in apply["catalog"][family]:
        if "external" in entry:
            lines.append(f"include {entry['external']}")
            continue
        cls = entry["class"]
        full = f"{MODULE}::{cls}"
        is_target = cls == target
        define = is_target and apply.get("resource_type") == "define"
        pfile = params_file(cls, target, kind, variant, params_dirs)
        if pfile is None:
            if define:
                raise FileNotFoundError(f"{target} is a define and needs a params fixture ({target}.json)")
            lines.append(f"include {full}")
            continue
        params = json.loads(render(pfile.read_text(encoding="utf-8")))
        head = f"{full} {{ {literal(apply.get('title', ''))}:" if define else f"class {{ '{full}':"
        lines += [head, *(f"  {k} => {literal(v)}," for k, v in params.items()), "}"]
    return "\n".join(lines) + "\n"
