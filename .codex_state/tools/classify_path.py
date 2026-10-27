#!/usr/bin/env python3
"""Generation path for one pending class (ruling 3, step 3.3). Decides; never edits.

  classify_path.py <class>

  exit 0  PATH unchanged-validated — manifest + templates/files identical to the baseline, pregate CLEAN,
          `test_class.sh --compile-only` OK. Advisor-direct: revert-first harness to GREEN, header,
          record_green.sh. No Codex. The reviewer verifies independently as for any class.
  exit 1  PATH syntax-work — the reasons are printed (pregate findings, compile error). Codex with the
          orientation packet; one run is the target.
  exit 3  PATH baseline-sync first — local content differs from the baseline (hazard 8).
  exit 4  PATH context-gap — the compile lacks context the plan or the harness must supply before either
          path runs (block category 3): a Hiera key (master Hiera fixture), a mandatory parameter (params
          fixture), or a resource from an undeclared required_base (plan fix).
  exit 2  ERROR — a check could not run (master/node unreachable, pregate ERROR); nothing is decided.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import baseline  # noqa: E402
import pregate  # noqa: E402

HARNESS = TOOLS / "test_class.sh"
CONTEXT_GAP = re.compile(r"did not find a value for the name|expects a value for parameter|"
                         r"Could not find data item|Cannot render define|"
                         r"Could not find resource '[^']+' in parameter '(?:require|before|notify|subscribe)'")


def compile_only(cls: str) -> tuple[str, str]:
    """('ok'|'fail'|'error', first relevant line)."""
    proc = subprocess.run([str(HARNESS), "--compile-only", cls], capture_output=True, text=True, timeout=600,
                          stdin=subprocess.DEVNULL)
    text = proc.stdout + proc.stderr
    if proc.returncode == 0 and "COMPILE OK" in text:
        return "ok", "COMPILE OK"
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(("Error:", "ERROR:"))), None)
    if start is None:
        first = text.strip()[-300:]
    else:  # the error line plus its indented continuation lines (run.sh keeps them)
        block = [lines[start].strip()]
        block += [l.strip() for l in lines[start + 1:start + 6] if l.startswith((" ", "\t"))]
        first = " ".join(block)
    return ("fail" if "COMPILE FAILED" in text or "no concrete resources" in text else "error"), first


def decide(cls: str) -> tuple[int, str, list[str]]:
    base = baseline.load()
    drift = baseline.local_drift(cls, base)
    if drift:
        return 3, "baseline-sync first", [f"{p} differs from {base.name}" for p in drift]
    report = pregate.pregate_class(cls)
    if report.status == "ERROR":
        return 2, "ERROR", [f"pregate {c}: {d}" for lvl, c, d in report.lines if lvl == "ERROR"]
    reasons = [f"pregate {c}: {d}" for lvl, c, d in report.lines if lvl == "FINDING"]
    if reasons:
        return 1, "syntax-work", reasons
    status, line = compile_only(cls)
    if status == "error":
        return 2, "ERROR", [f"compile-only could not run: {line}"]
    if status == "fail" and CONTEXT_GAP.search(line):
        return 4, "context-gap", [f"compile-only: {line}"]
    if status == "fail":
        return 1, "syntax-work", [f"compile-only: {line}"]
    return 0, "unchanged-validated", [f"identical to {base.name}; pregate CLEAN; compile-only OK"]


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not re.fullmatch(r"(puppet_infrastructure::)?[a-z][a-z0-9_]*", argv[0]):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    cls = argv[0].removeprefix("puppet_infrastructure::")
    code, path, reasons = decide(cls)
    if code != 2:  # step 3.4: metrics event
        subprocess.run([sys.executable, str(TOOLS / "metrics.py"), "event", cls, "path",
                        json.dumps({"path": path, "reasons": reasons[:5]})], capture_output=True)
    print(f"PATH {cls}: {path}")
    for reason in reasons:
        print(f"  - {reason}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
