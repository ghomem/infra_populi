#!/usr/bin/env python3
"""Record helpers (step 3.2) for the harness and record_green.sh. Nothing else writes records.

  records.py stamp [--revert-first] --run1-events N [--coverage TEXT] -- <class> [<class> ...]
      Called by test_class.sh on GREEN: writes .codex_state/logs/green/<class>.json (untracked) with the
      CODE hash of the class's files as they went GREEN (comment-only and blank lines of manifests are
      ignored, so adding the header after GREEN keeps the stamp valid; any code change voids it).
  records.py verify-stamp <class>       exit 0 if a GREEN stamp matches the current code, else 1.
  records.py header-check <class>       exit 0 if the manifest gained a migration header naming its
                                        module dependencies (or `none`) versus the baseline, else 1.
  records.py tracker-set <class> [--defect SHORT] [--mock-apply SHORT]
      Rewrites the class's migrated_classes.txt line to `<class> Done [from: <baseline>]` or
      `<class> Done [from: <baseline>; upstream defect fixed: SHORT]` (HQ checkpoint-1 ruling 3).
  records.py code-unchanged <class>     exit 0 if the class's code equals HEAD's (comment-only change).
  records.py class-files <class>        the tracked files a record commit may stage for the class.
  records.py header-modules <class>     Forge modules the header names that are installed in the
                                        master's environment (for necessary_modules.txt).

The stamp directory can be redirected with P8_GREEN_DIR (tests).
"""

from __future__ import annotations

import datetime as dt
import hashlib
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
import gen_migration_order as generator  # noqa: E402
import pregate  # noqa: E402
import review_class  # noqa: E402

REPO = baseline.REPO
TRACKER = REPO / ".codex_state" / "migrated_classes.txt"
SHORT = re.compile(r"(?:puppet_infrastructure::)?([a-z][a-z0-9_]*)")


def short_name(name: str) -> str:
    match = SHORT.fullmatch(name)
    if not match:
        raise SystemExit(f"ERROR: invalid class name {name!r}")
    return match.group(1)


def green_dir() -> Path:
    return Path(os.environ.get("P8_GREEN_DIR") or REPO / ".codex_state" / "logs" / "green")


def code_lines(path: str, data: bytes) -> bytes:
    if not path.endswith(".pp"):
        return data
    kept = [line for line in data.decode("utf-8", "replace").splitlines()
            if line.strip() and not line.strip().startswith("#")]
    return "\n".join(kept).encode()


def code_hash(cls: str, ref: str | None = None) -> tuple[str, list[str]]:
    """Hash of the class's code in the worktree, or at git `ref` (same file list)."""
    files = pregate.local_class_files(cls)
    digest = hashlib.sha256()
    for path in files:
        if ref is None:
            data = (REPO / path).read_bytes()
        else:
            shown = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True)
            data = shown.stdout if shown.returncode == 0 else b"\0missing"
        digest.update(path.encode() + b"\0" + code_lines(path, data) + b"\0")
    return digest.hexdigest(), files


def cmd_code_unchanged(cls: str) -> int:
    if code_hash(cls)[0] != code_hash(cls, "HEAD")[0]:
        print(f"CODE CHANGED in {cls} since HEAD: a records fix may change comments and the tracker only",
              file=sys.stderr)
        return 1
    print(f"CODE UNCHANGED {cls} (comments/tracker only)")
    return 0


def head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()


def cmd_stamp(argv: list[str]) -> int:
    if "--" not in argv:
        raise SystemExit("ERROR: stamp needs `-- <class> ...`")
    opts, classes = argv[:argv.index("--")], argv[argv.index("--") + 1:]
    revert_first = "--revert-first" in opts
    run1 = opts[opts.index("--run1-events") + 1] if "--run1-events" in opts else "0"
    coverage = opts[opts.index("--coverage") + 1] if "--coverage" in opts else ""
    names = [short_name(c) for c in classes]
    green_dir().mkdir(parents=True, exist_ok=True)
    for cls in names:
        sha, files = code_hash(cls)
        record = {"class": cls, "at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "code_sha256": sha, "files": files, "targets": names, "revert_first": revert_first,
                  "run1_events": int(run1), "head": head(),
                  "coverage": [l for l in coverage.splitlines() if l.startswith("COVERAGE ")]}
        (green_dir() / f"{cls}.json").write_text(json.dumps(record, indent=1) + "\n")
        print(f"GREEN_STAMP {cls} {sha[:12]}")
    return 0


def cmd_verify_stamp(cls: str) -> int:
    path = green_dir() / f"{cls}.json"
    if not path.is_file():
        print(f"NO GREEN STAMP for {cls}: run the harness to GREEN first", file=sys.stderr)
        return 1
    stamp = json.loads(path.read_text())
    sha, _ = code_hash(cls)
    if stamp.get("code_sha256") != sha:
        print(f"STALE GREEN STAMP for {cls}: the code changed after the GREEN run at {stamp.get('at')}; "
              "re-run the harness", file=sys.stderr)
        return 1
    print(f"GREEN STAMP OK {cls} ({stamp.get('at')}, run 1 {stamp.get('run1_events')} events, "
          f"{'reverted first' if stamp.get('revert_first') else 'not reverted first'})")
    return 0


def header_added(cls: str) -> list[str]:
    base = baseline.for_class(cls)
    upstream = (baseline.git_show(base.upstream, base.commit, f"manifests/{cls}.pp") or b"").decode("utf-8", "replace")
    local = (REPO / f"manifests/{cls}.pp").read_text(encoding="utf-8")
    added, _ = review_class.diff_lines("\n".join(review_class.header_block(upstream)),
                                       "\n".join(review_class.header_block(local)))
    return [line for line in added if review_class.is_comment(line)]


def cmd_header_check(cls: str) -> int:
    added = header_added(cls)
    if not added:
        print(f"NO HEADER on manifests/{cls}.pp: add the 2-line migration header before the class line",
              file=sys.stderr)
        return 1
    if not any(re.search(r"depend", line, re.I) for line in added):
        print(f"HEADER on manifests/{cls}.pp does not state module dependencies (or `none`)", file=sys.stderr)
        return 1
    # same claim parser as the reviewer's header_modules check (offline: known Forge authors only)
    unversioned = [forge for forge, version in review_class.module_claims(added, {"modules": {}}) if not version]
    if unversioned:
        print(f"HEADER on manifests/{cls}.pp names {', '.join(unversioned)} without a version (x.y.z) — the reviewer "
              "reads every `author-module` in the header as a dependency claim", file=sys.stderr)
        return 1
    print(f"HEADER OK {cls}: " + " | ".join(line.strip() for line in added))
    return 0


def tracker_text(text: str, cls: str, base_name: str, defect: str, mock: str = "") -> str:
    marker = (f"[from: {base_name}" + (f"; upstream defect fixed: {defect}" if defect else "")
              + (f"; mock-apply: {mock}" if mock else "") + "]")
    new_line = f"{cls} Done {marker}"
    if generator.parse_tracker_line(new_line) != generator.TrackerEntry(cls, True, base_name, defect, mock):
        raise SystemExit(f"ERROR: marker does not parse back: {new_line!r}")
    lines, hits = [], 0
    for line in text.splitlines():
        entry = generator.parse_tracker_line(line)
        if entry is not None and entry.name == cls:
            lines.append(new_line)
            hits += 1
        else:
            lines.append(line)
    if hits != 1:
        raise SystemExit(f"ERROR: migrated_classes.txt has {hits} lines for {cls}; expected 1")
    return "\n".join(lines) + "\n"


def cmd_tracker_set(cls: str, argv: list[str]) -> int:
    defect = argv[argv.index("--defect") + 1].strip() if "--defect" in argv else ""
    mock = argv[argv.index("--mock-apply") + 1].strip() if "--mock-apply" in argv else ""
    fixture = generator.parse_plan().get(cls)
    if bool(mock) != bool(fixture and fixture.node_fixture):
        raise SystemExit(f"ERROR: --mock-apply is required exactly when the plan gives {cls} a node_fixture "
                         f"(plan: {fixture.node_fixture if fixture else None!r})")
    base_name = baseline.for_class(cls).name
    TRACKER.write_text(tracker_text(TRACKER.read_text(encoding="utf-8"), cls, base_name, defect, mock))
    extra = (f"; upstream defect fixed: {defect}" if defect else "") + (f"; mock-apply: {mock}" if mock else "")
    print(f"TRACKER {cls} Done [from: {base_name}{extra}]")
    return 0


def cmd_header_modules(cls: str) -> int:
    inv = review_class.master_inventory()
    env = {m["forge"] for m in inv["modules"].values() if m["kind"] == "env"}
    for forge, _version in review_class.module_claims(header_added(cls), inv):
        if forge in env:
            print(forge)
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["stamp"]:
        return cmd_stamp(argv[1:])
    if len(argv) >= 2 and argv[0] in ("verify-stamp", "header-check", "tracker-set", "class-files", "header-modules",
                                         "code-unchanged"):
        cls = short_name(argv[1])
        if argv[0] == "verify-stamp":
            return cmd_verify_stamp(cls)
        if argv[0] == "header-check":
            return cmd_header_check(cls)
        if argv[0] == "tracker-set":
            return cmd_tracker_set(cls, argv[2:])
        if argv[0] == "code-unchanged":
            return cmd_code_unchanged(cls)
        if argv[0] == "class-files":
            print("\n".join(pregate.local_class_files(cls)))
            return 0
        return cmd_header_modules(cls)
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
