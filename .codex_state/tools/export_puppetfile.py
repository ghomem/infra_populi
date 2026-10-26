#!/usr/bin/env python3
"""Export the lab master's Puppetfile into the repo and check its pins.

The master (puppet8master) is never restored, so its Puppetfile is the only
record of which module versions the lab runs. This tool keeps a byte-identical
copy at .codex_state/lab/Puppetfile (ruling 5/3.5: exported on every change).

  export_puppetfile.py            fetch from the master, check pins, write the copy
  export_puppetfile.py --verify   fail if the repo copy differs from the master
  export_puppetfile.py --check F  check pins in a local file only (no network)

Every `mod` line must carry an exact version (2026-09-30 rule: never leave
`mod` unpinned). A line with a git/local source is reported, not accepted.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
EXPORT_PATH = REPO / ".codex_state" / "lab" / "Puppetfile"
MASTER_HOST = "puppet8master"
MASTER_PUPPETFILE = "/home/deployment/infra_populi_env/Puppetfile"

MOD_RE = re.compile(r"""^\s*mod\s+(['"])(?P<name>[^'"]+)\1\s*(?P<rest>.*)$""")
VERSION_RE = re.compile(r"""^,\s*(['"])(?P<version>\d+\.\d+\.\d+)\1\s*(#.*)?$""")


def unpinned_lines(text: str) -> list[str]:
    """Return a description of every mod line that lacks an exact version."""
    problems = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = MOD_RE.match(line)
        if not match:
            continue
        if not VERSION_RE.match(match.group("rest").strip()):
            problems.append(f"line {number}: {line.strip()}")
    return problems


def pinned_modules(text: str) -> dict[str, str]:
    """Map module name -> pinned version for every correctly pinned line."""
    result = {}
    for line in text.splitlines():
        match = MOD_RE.match(line)
        if not match:
            continue
        version = VERSION_RE.match(match.group("rest").strip())
        if version:
            result[match.group("name")] = version.group("version")
    return result


def fetch_master() -> str:
    proc = subprocess.run(
        ["ssh", "-T", MASTER_HOST, f"sudo -n cat {MASTER_PUPPETFILE}"],
        capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        raise SystemExit(f"ERROR: cannot read {MASTER_PUPPETFILE} on {MASTER_HOST}: {proc.stderr.strip()}")
    return proc.stdout


def check_or_die(text: str, origin: str) -> None:
    problems = unpinned_lines(text)
    if problems:
        raise SystemExit(f"ERROR: unpinned mod lines in {origin}:\n  " + "\n  ".join(problems))


def main(argv: list[str]) -> int:
    if argv[:1] == ["--check"] and len(argv) == 2:
        check_or_die(Path(argv[1]).read_text(encoding="utf-8"), argv[1])
        print(f"OK: every mod line in {argv[1]} is pinned")
        return 0
    if argv == ["--verify"]:
        master = fetch_master()
        local = EXPORT_PATH.read_text(encoding="utf-8") if EXPORT_PATH.exists() else None
        if local != master:
            print(f"DRIFT: {EXPORT_PATH.relative_to(REPO)} differs from {MASTER_HOST}:{MASTER_PUPPETFILE}; re-export")
            return 1
        print("OK: repo Puppetfile matches the master")
        return 0
    if argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    master = fetch_master()
    check_or_die(master, f"{MASTER_HOST}:{MASTER_PUPPETFILE}")
    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EXPORT_PATH.write_text(master, encoding="utf-8")
    print(f"exported {len(pinned_modules(master))} pinned modules to {EXPORT_PATH.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
