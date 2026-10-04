#!/usr/bin/env python3
"""Show live migration status without writing files or Python bytecode."""

from __future__ import annotations

import re
import sys
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gen_migration_order as generator


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

    # Render in memory to keep the summary identical to the generator's output.
    rendered = generator.render(rows, done, blocked, flagged, pending, gated, owner_validated)
    prefix = "Status summary: "
    summary = next(line for line in rendered.splitlines() if line.startswith(prefix))
    print(summary.removeprefix(prefix).removesuffix("."))

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
