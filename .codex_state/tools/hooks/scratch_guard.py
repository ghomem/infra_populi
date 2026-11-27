#!/usr/bin/env python3
"""Turn-end hook: scratch is not storage (HQ 2026-11-23 ruling 3; HQ review of the behaviour suite, ruling 5).

Run as a Stop hook. Lists the files in this project's session scratch directories
(/tmp/claude-<uid>/<project slug>/<session>/scratchpad) modified after the last commit. If there are any, the stop is
blocked once with the list: commit each to .codex_state/drafts/ or delete it, then stop. When the stop is already
the hook's own continuation (stop_hook_active), the list is printed without blocking again, so a stop never loops.

  scratch_guard.py                 the hook (reads the hook's JSON on stdin)
  scratch_guard.py --list          print the files, exit 1 if any (no stdin)

Environment: CLAUDE_PROJECT_DIR (the repository), SCRATCH_ROOT (default /tmp/claude-<uid>; tests).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def project_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[3])


def last_commit_time(repo: Path) -> float:
    p = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%ct"], capture_output=True, text=True)
    return float(p.stdout.strip() or 0)


def scratch_dirs(repo: Path) -> list[Path]:
    root = Path(os.environ.get("SCRATCH_ROOT") or f"/tmp/claude-{os.getuid()}")
    slug = str(repo.resolve()).replace("/", "-")
    return sorted((root / slug).glob("*/scratchpad"))


def newer_files(repo: Path) -> list[Path]:
    since = last_commit_time(repo)
    out = []
    for d in scratch_dirs(repo):
        for f in sorted(d.rglob("*")):
            try:
                if f.is_file() and f.stat().st_mtime > since:
                    out.append(f)
            except OSError:
                continue
    return out


def message(files: list[Path]) -> str:
    return ("Scratch files newer than the last commit (scratch is not storage): commit each to .codex_state/drafts/ "
            "or delete it before you stop.\n" + "\n".join(f"  {f}" for f in files))


def main(argv: list[str]) -> int:
    repo = project_dir()
    files = newer_files(repo)
    if argv[:1] == ["--list"]:
        if files:
            print(message(files))
        return 1 if files else 0
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        event = {}
    if not files:
        return 0
    if event.get("stop_hook_active"):
        print(message(files), file=sys.stderr)
        return 0
    print(json.dumps({"decision": "block", "reason": message(files)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
