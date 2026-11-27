#!/usr/bin/env python3
"""The module's name, single source (P2): metadata.json's `name` (Phase 2 rename plan, mechanics 2; HQ review of the
behaviour suite, ruling 8).

OLD is the name the pinned upstream baseline and the repository's history carry. A comparison with the baseline reads
the baseline as it would read under the current name (`to_current`), so a renamed class is identical to its
baseline; a search of history (commit subjects) accepts either name. While the module still has the old name, every
function here is the identity.

  module_name.py              print the current name
  module_name.py prefix       print `<name>::`
  module_name.py short <cls>  print a class name without either name's prefix

P8_MODULE_NAME overrides metadata.json (tests).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OLD = "puppet_infrastructure"


def current() -> str:
    return os.environ.get("P8_MODULE_NAME") or json.loads((REPO / "metadata.json").read_text(encoding="utf-8"))["name"]


MODULE = current()
PREFIX = f"{MODULE}::"


def forms(name: str) -> list[str]:
    """Every spelling of a module name in code, paths and prose: `x_y`, `X_y` (a resource reference), `x-y` (paths,
    units, instance names)."""
    return [name, name[:1].upper() + name[1:], name.replace("_", "-")]


def mapping(old: str = OLD, new: str | None = None) -> list[tuple[str, str]]:
    new = new or MODULE
    return [] if new == old else list(zip(forms(old), forms(new)))


def to_current(data: bytes | str | None) -> bytes | str | None:
    """Baseline content as it reads under the current name (each old form replaced by the current one)."""
    if data is None:
        return None
    for a, b in mapping():
        data = data.replace(a.encode(), b.encode()) if isinstance(data, bytes) else data.replace(a, b)
    return data


def either() -> str:
    """A regex alternation matching the old or the current name (for history, which keeps the old one)."""
    return "|".join(re.escape(n) for n in dict.fromkeys([MODULE, OLD]))


def short(name: str) -> str:
    """A class name without the module prefix (either name's)."""
    return re.sub(rf"^(?:{either()})::", "", name)


if __name__ == "__main__":
    if sys.argv[1:2] == ["short"] and len(sys.argv) == 3:
        print(short(sys.argv[2]))
    else:
        print(PREFIX if sys.argv[1:] == ["prefix"] else MODULE)
