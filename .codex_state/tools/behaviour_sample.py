#!/usr/bin/env python3
"""The engine's switch to the public runner: the sample (HQ review of design note F, ruling 7).

  behaviour_sample.py compare [--local] <class>...   the public runner's latest record (--local: of its local-apply mode,
                                           .codex_state/checks/public/local/, HQ ruling 3's measurement) (.codex_state/checks/public/harness/) next
                                           to the engine's latest run the set's review judged (checks/results), per
                                           check and phase, base and variants; exit 1 on any difference
  behaviour_sample.py measure              ruling 3's measurement: per set, the local-apply record next to the engine's
                                           (outcome, differing checks, measured durations); a set whose local run
                                           differs is a candidate for `apply.requires: [server]`
  behaviour_sample.py cover [<class>...]   what the classes cover of ruling 7's list (every probe helper, every node kind,
                                           a second node, a mutating probe, the desktop session, the browser flow)

A check compares by its verdict: clean phase `ok` (a negative control failed, an invariant passed), applied phase
`passed`, a mismatch control's `passed`, a mutating check's action exit code. Outputs are not compared (times, ids).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SUITE = REPO / "spec" / "behaviour"
OLD = REPO / ".codex_state" / "checks" / "results"
NEW = REPO / ".codex_state" / "checks" / "public" / "harness"
HELPERS = sorted(set(re.findall(r"^(p8_[a-z_]+)\(\)", (SUITE / "probe_helpers.sh").read_text(), re.M)))


def latest(directory: Path, pattern: str = "*.json") -> dict | None:
    files = sorted(directory.glob(pattern))
    return json.loads(files[-1].read_text()) if files else None


def engine_record(cls: str) -> dict | None:
    """The engine's run the set's latest review judged: its reviewer run (the review re-runs the checks)."""
    return latest(OLD / cls, "*-reviewer.json") or latest(OLD / cls)


def verdicts(record: dict) -> dict:
    out = {}
    for r in record.get("clean") or []:
        out[("clean", r["id"])] = r.get("ok")
    for r in record.get("applied") or []:
        out[("applied", r["id"])] = None if r.get("not_run") else r.get("passed")
        if r.get("mismatch") and not r["mismatch"].get("not_run"):
            out[("mismatch", r["id"])] = r["mismatch"].get("passed")
        if r.get("action"):
            out[("action rc", r["id"])] = r["action"].get("rc")
    out[("outcome", "")] = record.get("outcome")
    out[("apply green", "")] = (record.get("apply") or {}).get("green")
    return out


def compare(cls: str) -> list[str]:
    old, new = engine_record(cls), latest(NEW / cls)
    if not old or not new:
        return [f"{cls}: {'no engine record' if not old else 'no public record'}"]
    out = []
    pairs = [("base", old, new)] + [(f"variant {n}", v, (new.get("variants") or {}).get(n) or {})
                                    for n, v in (old.get("variants") or {}).items()]
    for run, a, b in pairs:
        va, vb = verdicts(a), verdicts(b)
        for key in sorted(set(va) | set(vb), key=str):
            if va.get(key) != vb.get(key):
                out.append(f"{cls} {run} {key[0]} {key[1]}: engine {va.get(key)!r}, public {vb.get(key)!r}")
    return out


def features(cls: str) -> set[str]:
    d = yaml.safe_load((SUITE / "checks" / f"{cls}.yml").read_text())
    text = yaml.safe_dump(d.get("checks"))
    out = {h for h in HELPERS if re.search(rf"\b{h}\b", text)}
    out |= {f"kind {k}" for k in {d["apply"]["node"], *(v.get("node", d["apply"]["node"]) for v in d.get("variants") or []),
                                  *([d["peer"]["kind"]] if d.get("peer") else [])}}
    if d.get("peer"):
        out.add("second node")
    if any("mutates" in c for c in d["checks"]):
        out.add("mutating probe")
    if d.get("session"):
        out.add("desktop session")
    if re.search(r"playwright|chromium|browser", text, re.I):
        out.add("browser flow")
    return out


def cover(classes: list[str]) -> int:
    sys.path.insert(0, str(SUITE / "lib"))
    from behaviour import setfile  # noqa: PLC0415
    kinds = sorted(setfile.kinds())
    wanted = set(HELPERS) | {f"kind {k}" for k in kinds} | {"second node", "mutating probe", "desktop session",
                                                            "browser flow"}
    got = set().union(*(features(c) for c in classes)) if classes else set()
    used = set().union(*(features(p.stem) for p in (SUITE / "checks").glob("*.yml")
                         if "deferred" not in yaml.safe_load(p.read_text())))
    for w in sorted(wanted):
        state = "covered" if w in got else ("used by no set" if w not in used else "NOT COVERED")
        print(f"{state:15} {w}")
    return 1 if any(w in used and w not in got for w in wanted) else 0


def measure() -> int:
    global NEW
    NEW = NEW.parent / "local"
    rows, same = [], 0
    for path in sorted((SUITE / "checks").glob("*.yml")):
        cls = path.stem
        if "deferred" in yaml.safe_load(path.read_text()):
            continue
        old, new = engine_record(cls), latest(NEW / cls)
        if not new:
            rows.append((cls, "not run", (old or {}).get("outcome"), "", (old or {}).get("duration_s"), None))
            continue
        diffs = compare(cls)
        same += not diffs
        rows.append((cls, new.get("outcome"), (old or {}).get("outcome"), len(diffs), (old or {}).get("duration_s"),
                     new.get("duration_s")))
    print("| set | local | engine | differing checks | engine s | local s |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join("" if x is None else str(x) for x in r) + " |")
    ran = sum(1 for r in rows if r[1] != "not run")
    print(f"\n{len(rows)} sets: {ran} measured, {same} identical to the engine, {ran - same} differ")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["measure"]:
        return measure()
    if not argv or argv[0] not in ("compare", "cover"):
        print(__doc__)
        return 2
    if argv[0] == "cover":
        return cover(argv[1:])
    global NEW
    classes = argv[1:]
    if classes[:1] == ["--local"]:
        NEW, classes = NEW.parent / "local", classes[1:]
    diffs = [d for cls in classes for d in compare(cls)]
    for d in diffs:
        print(d)
    print(f"{len(classes)} sets: {len(diffs)} differences")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
