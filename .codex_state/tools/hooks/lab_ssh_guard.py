#!/usr/bin/env python3
"""PreToolUse hook for Bash (HQ 2026-11-20, after batch 16, item 3): a command run by hand on a lab machine goes through
lab_exec.sh, which refuses while another run holds the lab lock. This hook refuses (exit 2, the reason on stderr) any
Bash command whose shell segment runs ssh, scp, sftp or rsync against a lab host without lab_exec.sh. The engine's own
tools (revert_node.sh, test_class.sh, phase3.py, ...) take the lock themselves and run ssh inside, so a command that
calls them is not touched. Anything that cannot be parsed is let through: the hook guards a habit, not a boundary."""
from __future__ import annotations

import json
import re
import sys

LAB_HOST = re.compile(r"(?<![\w.-])(puppet8master(?:-rsync)?|puppet8node(?:-rsync)?|p8lab-[a-z0-9-]+|192\.168\.56\.\d+)(?![\w.-])")
REMOTE = re.compile(r"(?:^|[\s;&|(`])(ssh|scp|sftp|rsync)\s")
SEGMENT = re.compile(r"&&|\|\||[;\n|&]")


def offending(command: str) -> str | None:
    """The first shell segment that reaches a lab host with ssh/scp/sftp/rsync outside lab_exec.sh, or None."""
    for segment in SEGMENT.split(command):
        if "lab_exec.sh" in segment:
            continue
        if REMOTE.search(" " + segment) and LAB_HOST.search(segment):
            return segment.strip()
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    command = str((event.get("tool_input") or {}).get("command") or "")
    seg = offending(command)
    if seg is None:
        return 0
    print(f"LAB ACCESS REFUSED (HQ 2026-11-20 item 3): `{seg[:160]}` reaches a lab machine directly. Run it through "
          ".codex_state/tools/lab_exec.sh <host> '<command>' (stdin passes through), which refuses while another run "
          "holds the lab lock.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
