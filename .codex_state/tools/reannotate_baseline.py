#!/usr/bin/env python3
"""Mechanical re-annotation of tracker provenance after a baseline bump (ruling 1).

Rewrites `[from: <old>]` to `[from: <new>]` in .codex_state/migrated_classes.txt ONLY for classes
whose manifest + referenced templates/files are byte-identical between the old and new upstream
refs. Anything else keeps its old marker and is listed for re-migration. Changes nothing else on
the line (marker position `X Done` / `Done X` is preserved, per the 2026-07-01 rule).

  reannotate_baseline.py            dry run: print the plan, change nothing
  reannotate_baseline.py --apply    rewrite the tracker
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import baseline  # noqa: E402

OLD_NAME = "release-0.9.8"
# The ref the 0.9.8-era tools diffed against (origin/release-0.9.8; tag 0.9.8 has identical
# manifests/templates/files). Pinned so a later fetch cannot move it.
OLD_COMMIT = "5f34e6b47ff2f937462c14a682b3fd9ed30c8646"
TRACKER = baseline.REPO / ".codex_state" / "migrated_classes.txt"


def plan(lines: list[str], old_name: str, new_name: str, identical) -> tuple[list[str], list[tuple[str, str, list[str]]]]:
    """Return (new lines, decisions). identical(cls) -> (bool, differing paths)."""
    marker_old = f"[from: {old_name}]"
    marker_new = f"[from: {new_name}]"
    out, decisions = [], []
    for line in lines:
        if marker_old not in line:
            out.append(line)
            continue
        names = [tok for tok in re.split(r"\s+", line.replace(marker_old, "").strip()) if tok and tok != "Done"]
        if len(names) != 1:
            raise SystemExit(f"ERROR: cannot identify the class on tracker line: {line!r}")
        cls = names[0]
        same, differing = identical(cls)
        if same:
            out.append(line.replace(marker_old, marker_new))
            decisions.append((cls, "reannotate", []))
        else:
            out.append(line)
            decisions.append((cls, "keep (content differs)", differing))
    return out, decisions


def only_markers_changed(before: str, after: str, old_name: str, new_name: str) -> bool:
    """True when the two tracker texts differ only in old->new marker text."""
    def strip(s: str) -> str:
        return s.replace(f"[from: {old_name}]", "[from: *]").replace(f"[from: {new_name}]", "[from: *]")
    return strip(before) == strip(after)


def main(argv: list[str]) -> int:
    if argv not in ([], ["--apply"]):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    base = baseline.load()
    text = TRACKER.read_text(encoding="utf-8")
    lines = text.split("\n")
    new_lines, decisions = plan(
        lines, OLD_NAME, base.name,
        lambda cls: baseline.identical_between(cls, OLD_COMMIT, base.commit, base.upstream),
    )
    for cls, action, differing in decisions:
        print(f"{cls}: {action}" + (f" — {', '.join(differing)}" if differing else ""))
    changed = sum(1 for _, a, _ in decisions if a == "reannotate")
    print(f"{changed} reannotated, {len(decisions) - changed} kept, {OLD_NAME} ({OLD_COMMIT[:7]}) -> "
          f"{base.name} ({base.commit[:7]})")
    if argv == ["--apply"]:
        TRACKER.write_text("\n".join(new_lines), encoding="utf-8")
        if not only_markers_changed(text, TRACKER.read_text(encoding="utf-8"), OLD_NAME, base.name):
            raise SystemExit("ERROR: tracker changed beyond the marker text; inspect with git diff")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
