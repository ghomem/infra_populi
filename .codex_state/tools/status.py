#!/usr/bin/env python3
"""Show live migration status without writing files or Python bytecode."""

from __future__ import annotations

import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(1, str(Path(__file__).resolve().parent))
import gen_migration_order as generator

REVIEWS = generator.REVIEWS_PATH
VERIFIED = generator.VERIFIED
PENDING_RECONCILIATION = generator.PENDING_RECONCILIATION


def verification_state(name, migration, flagged, reviews: Path = REVIEWS):
    """Single implementation lives in the generator (step 4.3 moved it there)."""
    return generator.verification_state(name, migration, flagged, reviews)


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
    prod = generator.read_prod_nodes()
    pending, gated = generator.topological_pending(rows, done, set(blocked), owner_validated, prod)

    tracker = generator.read_tracker()

    # Render in memory to keep the summary identical to the generator's output.
    remigrations = generator.remigration_queue(migrations, flagged)
    rendered = generator.render(rows, done, blocked, flagged, pending, gated, owner_validated, tracker, prod,
                                remigrations)
    prefix = "Status summary: "
    summary = next(line for line in rendered.splitlines() if line.startswith(prefix))
    print(summary.removeprefix(prefix).removesuffix("."))
    import baseline as _baseline  # noqa: PLC0415  (tools dir; per-class exceptions)
    exc = _baseline.exceptions()
    print(f"Baseline: {generator.baseline_name()}"
          + (f" (+ per-class exceptions: {', '.join(f'{c} at {n}' for c, (_, n) in sorted(exc.items()))})" if exc else ""))

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

    print("\nRe-migration queue (HQ ck1 order)")
    print_table(("class", "when"), [(f"{generator.PREFIX}{name}", when) for name, when in remigrations])

    print("\nTop 15 pending")
    print_table(
        ("class", "prod", "complexity", "dep_score"),
        [
            (f"{generator.PREFIX}{row.name}", str(prod.get(row.name, 0)), str(row.complexity), str(row.dep_score))
            for row in pending[:15]
        ],
    )


if __name__ == "__main__":
    main()
