"""The manifest a run applies: a set's `apply` block made Puppet code.

In the order the set gives: its node fixture first (stand-ins for a service the node does not run), then each catalog
entry: a module's base class (`include <module>`), or one of this module's classes declared with its params fixture
(a define with its title: the set's apply.title for the class under test, the entry's `define:` for a base), or
plainly included when it has none.

Params fixtures are looked up level by level, the first level with a file in any of the params directories winning
(directories in the order given: the operator's, then the suite's own fake fixtures):  for/<target>/<class>.json  (the class as a base of this target)
                  variants/<variant>/<target>.json  (a variant's own params for the target)
                  kinds/<kind>/<class>.json  (the class on that node kind)
                  <class>.json
where <class> is the short name (a file or directory named with the module prefix, `infra_populi::<class>`,
is found too).
"""

from __future__ import annotations

import json
from pathlib import Path

from .setfile import MODULE  # noqa: E402  (the module's name, metadata.json)


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
    def named(x: str) -> list[str]:
        return [x, f"{MODULE}::{x}"]
    levels = [[Path("for") / t / f"{c}.json" for t in named(target) for c in named(cls)]]
    if variant and cls == target:
        levels.append([Path("variants") / variant / f"{t}.json" for t in named(target)])
    levels += [[Path("kinds") / kind / f"{c}.json" for c in named(cls)], [Path(f"{c}.json") for c in named(cls)]]
    for level in levels:  # a more specific file wins over a general one, whichever directory holds it
        for d in dirs:
            for rel in level:
                if (d / rel).is_file():
                    return d / rel
    return None


def family_of(kind: str, kinds: dict) -> str:
    return kinds[kind]["os_family"]


def build(data: dict, kind: str, kinds: dict, params_dirs: list[Path], fixtures: Path,
          variant: str | None = None, render=lambda s: s, variant_fixture: str | None = None) -> str:
    """The manifest for the set on a node of `kind`. `render` fills the placeholders a node or params fixture carries."""
    apply = data["apply"]
    target = data["class"]
    lines = []
    # the set's node fixture, then a variant's own (HQ 2026-11-27 item 4: state the class needs before it applies)
    for name in [n for n in (apply.get("node_fixture"), variant_fixture) if n]:
        path = fixtures / "node" / f"{name}.pp"
        if not path.is_file():
            raise FileNotFoundError(f"node fixture {name} not found ({path})")
        lines.append(render(path.read_text(encoding="utf-8")).rstrip("\n"))
    family = family_of(kind, kinds)
    for entry in apply["catalog"][family]:
        if "external" in entry:
            lines.append(f"include {entry['external']}")
            continue
        cls = entry["class"]
        full = f"{MODULE}::{cls}"
        is_target = cls == target
        define = (is_target and apply.get("resource_type") == "define") or "define" in entry
        title = apply.get("title", "") if is_target else entry.get("define", "")
        pfile = params_file(cls, target, kind, variant, params_dirs)
        if pfile is None:
            if define:
                raise FileNotFoundError(f"{cls} is a define and needs a params fixture ({cls}.json)")
            lines.append(f"include {full}")
            continue
        params = json.loads(render(pfile.read_text(encoding="utf-8")))
        head = f"{full} {{ {literal(title)}:" if define else f"class {{ '{full}':"
        lines += [head, *(f"  {k} => {literal(v)}," for k, v in params.items()), "}"]
    return "\n".join(lines) + "\n"
