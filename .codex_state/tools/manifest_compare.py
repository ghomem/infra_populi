#!/usr/bin/env python3
"""The public runner's manifest equals the harness's, run by run (HQ review of design note F, ruling 7 groundwork).

  manifest_compare.py [<class> ...]   (no class = every set with an apply block)

For each set and each of its runs (base, and each variant on its node kind with its params), builds the manifest the
public runner applies (spec/behaviour/lib/behaviour/manifest.py: the suite's fixtures rendered with the lab's values,
then the local params directory for the files that stay local) and the one the harness applies
(`test_class.sh --render-only --node <kind>`, P8_PARAMS_VARIANT for a variant's params), and compares their Puppet code
line by line, comments aside. Offline: the harness renders without the lab. Exit 0 all equal, 1 otherwise.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(REPO / "spec" / "behaviour" / "lib"))

import behaviour_move as bm  # noqa: E402
import fixtures_move as fm  # noqa: E402
from behaviour import manifest as mf  # noqa: E402
from behaviour import render as rn  # noqa: E402
from behaviour import setfile  # noqa: E402

HARNESS = os.environ.get("P8_HARNESS") or str(Path.home() / ".local" / "bin" / "infra_populi_tools" / "test_class.sh")
SUITE = REPO / "spec" / "behaviour"


def code(text: str) -> list[str]:
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("# BEGIN CODEX MANAGED"):
            inside = True
            continue
        if line.startswith("# END CODEX MANAGED"):
            break
        if inside and line.strip() and not line.lstrip().startswith("#"):
            out.append(line.rstrip())
    return out


def public_code(text: str) -> list[str]:
    return [l.rstrip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]


def harness(cls: str, kind: str | None, params: str | None) -> tuple[int, str]:
    env = {**os.environ}
    if params:
        env["P8_PARAMS_VARIANT"] = params
    args = [HARNESS, *(["--node", kind] if kind else []), "--render-only", f"{bm.MODULE}::{cls}"]
    p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout + p.stderr


def compare(cls: str, data: dict, kinds: dict) -> list[str]:
    ctxs = bm.contexts(cls, data)
    base = data["apply"]["node"]
    runs = [("base", base, None)] + [(v["name"], v.get("node", base), v.get("params"))
                                    for v in data.get("variants") or []]
    out = []
    for run, kind, params in runs:
        rc, text = harness(cls, None if run == "base" else kind, params)
        if rc != 0:
            out.append(f"{cls} ({run}): the harness did not render: {text.strip().splitlines()[-1:]}")
            continue
        try:
            mine = mf.build(data, kind, kinds, [SUITE / "fixtures" / "params", fm.LOCAL], SUITE / "fixtures",
                            variant=params, render=lambda t, c=ctxs[run]: rn.render(t, c))
        except (FileNotFoundError, KeyError) as err:
            out.append(f"{cls} ({run}): the public manifest did not build: {err}")
            continue
        theirs, ours = code(text), public_code(mine)
        if theirs != ours:
            first = next((i for i, (a, b) in enumerate(zip(theirs, ours)) if a != b), min(len(theirs), len(ours)))
            out.append(f"{cls} ({run}): line {first + 1}: harness {theirs[first:first + 1]} vs public "
                       f"{ours[first:first + 1]}")
    return out


def main(argv: list[str]) -> int:
    kinds = setfile.kinds()
    sets = fm.sets()
    classes = argv or sorted(sets)
    bad, runs = [], 0
    for cls in classes:
        data = sets[cls]
        runs += 1 + len(data.get("variants") or [])
        bad += compare(cls, data, kinds)
    for line in bad:
        print(line)
    print(f"{len(classes)} sets, {runs} runs: {runs - len(bad)} equal, {len(bad)} differ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
