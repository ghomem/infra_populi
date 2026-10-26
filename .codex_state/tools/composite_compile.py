#!/usr/bin/env python3
"""Standing composite compiles and default-parameter variants (step 2.2). Never runs the node.

  composite_compile.py               every composite in compile/composites.txt vs its expectation
  composite_compile.py --defaults    every git-DONE class compiled with default parameters (report)

Composites: exit 0 when every result matches its `expect`, 1 otherwise. Defaults: report only
(exit 0); a class whose defaults need a mandatory parameter is reported as such, not as a failure.
Deploys the tree once, then calls `test_class.sh --compile-only` with SKIP_DEPLOY=1.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS.parent))
HARNESS = TOOLS / "test_class.sh"
COMPOSITES = TOOLS / "compile" / "composites.txt"


def parse_composites(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 4 or parts[1] not in ("debian", "redhat") or not (
                parts[2] == "pass" or parts[2].startswith("fail:")):
            raise SystemExit(f"ERROR: bad composites line: {line!r}")
        rows.append({"name": parts[0], "facts": parts[1], "expect": parts[2], "classes": parts[3].split()})
    return rows


def judge(expect: str, rc: int, output: str) -> tuple[bool, str]:
    """(matches expectation, one-line outcome)."""
    outcome = "pass" if rc == 0 else "fail: " + first_error(output)
    if expect == "pass":
        return rc == 0, outcome
    return rc != 0 and expect[5:] in output, outcome


def compile_only(classes: list[str], facts: str = "debian", defaults: bool = False, deploy: bool = False) -> tuple[int, str]:
    # Composites declare exactly what production declares (--no-expand): required_base is a test-node
    # projection and would add classes production never declares beside these.
    argv = [str(HARNESS), "--compile-only", "--facts", facts] + (["--defaults"] if defaults else ["--no-expand"]) + \
        [f"puppet_infrastructure::{c}" for c in classes]
    env = dict(os.environ, SKIP_DEPLOY="0" if deploy else "1")
    proc = subprocess.run(argv, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=600)
    return proc.returncode, proc.stdout + proc.stderr


def first_error(output: str) -> str:
    """First compiler error with its indented continuation lines, on one line."""
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Error:"):
            parts = [line]
            for more in lines[i + 1:]:
                if not more[:1].isspace():
                    break
                parts.append(more.strip())
            return " ".join(parts)[:300]
    return (lines[-1] if lines else "")[:300]


def run_composites() -> int:
    bad = 0
    for i, row in enumerate(parse_composites(COMPOSITES.read_text(encoding="utf-8"))):
        rc, out = compile_only(row["classes"], row["facts"], deploy=(i == 0))
        ok, outcome = judge(row["expect"], rc, out)
        bad += not ok
        print(f"{'OK  ' if ok else 'DIFF'} {row['name']} ({row['facts']}): expected {row['expect']} -> {outcome}")
    print(f"COMPOSITES: {'all as expected' if not bad else f'{bad} differ from expectation'}")
    return 1 if bad else 0


def run_defaults() -> int:
    import gen_migration_order as gen  # noqa: PLC0415
    done = sorted(set(gen.git_migrations()) - set(gen.read_blocked()))
    for i, cls in enumerate(done):
        rc, out = compile_only([cls], defaults=True, deploy=(i == 0))
        if rc == 0:
            outcome = "pass"
        elif re.search(r"expects a value for parameter|Must pass \w+ to|expects an? \S+ value, got Undef", out):
            outcome = "needs params (mandatory parameter without default)"
        else:
            outcome = "FAIL: " + first_error(out)
        print(f"DEFAULTS {cls}: {outcome}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == []:
        sys.exit(run_composites())
    if sys.argv[1:] == ["--defaults"]:
        sys.exit(run_defaults())
    raise SystemExit(__doc__)
