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
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import baseline  # noqa: E402
import module_name  # noqa: E402
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


def params_dir() -> Path:
    return Path(os.environ.get("P8_PARAMS_DIR") or Path.home() / ".config" / "infra_populi" / "params")


def missing_define_params(cls: str) -> str | None:
    """Hazard 10 (batch 4, user_kde_lock_screen): a define needs its params file for the harness even when every
    parameter has a default; compile-only renders it without one, so it passed here and the harness refused it."""
    import gen_migration_order as gen  # noqa: PLC0415
    row = gen.parse_plan().get(cls)
    path = params_dir() / f"{module_name.PREFIX}{cls}.json"
    if row is not None and row.resource_type == "define" and not path.is_file():
        return f"hazard 10: define params fixture missing ({path}); the harness cannot render the define without it"
    return None


# Baseline-inherited lint that Puppet 8 accepts (the compile-only step still proves it): Codex is told to leave it
# (CODEX_RUNBOOK §2.3), so it never routes a baseline-identical class to syntax-work on its own.
COSMETIC_INHERITED = ("lint:parameter_order",)


def decide(cls: str) -> tuple[int, str, list[str]]:
    base = baseline.for_class(cls)
    drift = baseline.local_drift(cls, base)
    if drift:
        return 3, "baseline-sync first", [f"{p} differs from {base.name}" for p in drift]
    report = pregate.pregate_class(cls)
    if report.status == "ERROR":
        return 2, "ERROR", [f"pregate {c}: {d}" for lvl, c, d in report.lines if lvl == "ERROR"]
    findings = [(c, d) for lvl, c, d in report.lines if lvl == "FINDING"]
    inherited = [(c, d) for c, d in findings if c in COSMETIC_INHERITED and d.endswith("(also in baseline)")]
    findings = [f for f in findings if f not in inherited]
    reasons = [f"pregate {c}: {d}" for c, d in findings]
    if reasons and all(c in ("hazard14-module-base", "hazard4-prereq") for c, _ in findings):
        return 4, "context-gap", reasons  # a plan required_external (advisor), not syntax work
    if reasons:
        return 1, "syntax-work", reasons
    missing = missing_define_params(cls)
    if missing:  # hazard 10: the harness renders a define only from its params file (compile-only uses defaults)
        return 4, "context-gap", [missing]
    status, line = compile_only(cls)
    if status == "error":
        return 2, "ERROR", [f"compile-only could not run: {line}"]
    if status == "fail" and CONTEXT_GAP.search(line):
        return 4, "context-gap", [f"compile-only: {line}"]
    if status == "fail":
        return 1, "syntax-work", [f"compile-only: {line}"]
    left = f" (inherited lint left as in {base.name}: {', '.join(sorted({c for c, _ in inherited}))} x{len(inherited)})" \
        if inherited else ""
    return 0, "unchanged-validated", [f"identical to {base.name}; pregate CLEAN{left}; compile-only OK"]


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not re.fullmatch(rf"(?:(?:{module_name.either()})::)?[a-z][a-z0-9_]*", argv[0]):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    cls = module_name.short(argv[0])
    import time  # noqa: PLC0415
    started = time.monotonic()
    code, path, reasons = decide(cls)
    if code != 2:  # step 3.4: metrics event
        subprocess.run([sys.executable, str(TOOLS / "metrics.py"), "event", cls, "path",
                        json.dumps({"path": path, "reasons": reasons[:5],
                                    "duration_s": round(time.monotonic() - started, 1)})], capture_output=True)
    print(f"PATH {cls}: {path}")
    for reason in reasons:
        print(f"  - {reason}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
