#!/usr/bin/env python3
"""Show live migration status without writing files or Python bytecode."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_migration_order as generator

REVIEWS = generator.SCRIPT_DIR / "reviews"
VERIFIED = "verified (gate v2)"
PENDING_RECONCILIATION = "done (gate v1, reconciliation pending)"


def latest_verdict(name: str, reviews: Path = REVIEWS) -> dict | None:
    files = sorted((reviews / name).glob("*.json")) if (reviews / name).is_dir() else []
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def verification_state(
    name: str, migration: generator.MigrationCommit, flagged: set[str], reviews: Path = REVIEWS
) -> tuple[str, dict | None]:
    """Derived (HQ checkpoint-1 ruling 1): verified only by a reviewer-v2 PASS whose reviewed commit is
    the class's current effective commit, with no non-record manifest change since."""
    verdict = latest_verdict(name, reviews)
    reviewed = (verdict or {}).get("migrate_commit") or ""
    if (
        verdict
        and verdict.get("verdict") == "PASS"
        and reviewed
        and migration.commit.startswith(reviewed)
        and name not in flagged
    ):
        return VERIFIED, verdict
    return PENDING_RECONCILIATION, verdict


def failing_checks(verdict: dict | None) -> str:
    if verdict is None:
        return "no v2 verdict"
    failed = [n for n, c in verdict.get("checks", {}).items() if c.get("status") != "ok"]
    if verdict.get("faithful", {}).get("status") != "ok":
        failed.append("faithful")
    if verdict.get("verdict") == "PASS":
        return "PASS on an older commit"
    return ",".join(failed) or verdict.get("verdict", "?")


def print_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    widths = [
        max([len(header), *(len(row[index]) for row in rows)])
        for index, header in enumerate(headers)
    ]
    for row in [headers, tuple("-" * width for width in widths), *rows]:
        print(" | ".join(cell.ljust(width) for cell, width in zip(row, widths)))
    if not rows:
        print("(none)")


def blocked_category(reason: str) -> str:
    match = re.search(r"\bcategory\s+(\d+)\b", reason, re.IGNORECASE)
    return match.group(1) if match else "unknown"


def marker(entry: generator.TrackerEntry | None) -> str:
    if entry is None or not entry.done:
        return "(not Done in tracker)"
    if not entry.from_ref:
        return "plain Done"
    fixed = f"; upstream defect fixed: {entry.defect_fixed}" if entry.defect_fixed else ""
    return f"[from: {entry.from_ref}{fixed}]"


def short_reason(reason: str) -> str:
    reason = reason.removeprefix("—").strip()
    return reason if len(reason) <= 70 else reason[:67] + "..."


def main() -> None:
    if sys.argv[1:]:
        generator.fail(f"usage: {Path(sys.argv[0]).name}")

    rows = generator.parse_plan()
    migrations = generator.git_migrations()
    blocked = generator.read_blocked()
    flagged = generator.find_flagged_migrations(migrations)
    owner_validated = {name for name, row in rows.items() if row.owner_validated}
    conflicting = sorted(owner_validated & set(blocked))
    if conflicting:
        generator.fail("owner_validated classes must not also be blocked: " + ", ".join(conflicting))
    done = set(migrations) - set(blocked) - owner_validated
    pending, gated = generator.topological_pending(rows, done, set(blocked), owner_validated)

    tracker = generator.read_tracker()

    # Render in memory to keep the summary identical to the generator's output.
    rendered = generator.render(rows, done, blocked, flagged, pending, gated, owner_validated, tracker)
    prefix = "Status summary: "
    summary = next(line for line in rendered.splitlines() if line.startswith(prefix))
    print(summary.removeprefix(prefix).removesuffix("."))
    print(f"Baseline: {generator.baseline_name()}")

    states = {name: verification_state(name, migrations[name], flagged) for name in sorted(done)}
    verified = [name for name, (state, _) in states.items() if state == VERIFIED]
    print(f"Done split: {len(verified)} {VERIFIED} / {len(done) - len(verified)} {PENDING_RECONCILIATION}")

    print("\nDone classes by verification state (derived from .codex_state/reviews/)")
    print_table(
        ("class", "state", "tracker marker", "latest v2 verdict"),
        [
            (
                f"{generator.PREFIX}{name}",
                state,
                marker(tracker.get(name)),
                "PASS" if state == VERIFIED else failing_checks(verdict),
            )
            for name, (state, verdict) in sorted(states.items(), key=lambda item: (item[1][0] != VERIFIED, item[0]))
        ],
    )

    print("\nBlocked classes")
    print_table(
        ("class", "category", "reason"),
        [
            (f"{generator.PREFIX}{name}", blocked_category(reason), short_reason(reason))
            for name, reason in sorted(blocked.items())
        ],
    )

    print("\nTop 15 pending")
    print_table(
        ("class", "complexity", "dep_score"),
        [
            (f"{generator.PREFIX}{row.name}", str(row.complexity), str(row.dep_score))
            for row in pending[:15]
        ],
    )


if __name__ == "__main__":
    main()
