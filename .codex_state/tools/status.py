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
VERIFIED_STANDIN = "verified with stand-in"
NODE_FIXTURES = Path(__file__).resolve().parent / "tests" / "fixtures" / "node"
LIFTED_BY = "# Lifted by:"


def lifted_by(fixture: str, fixtures: Path = NODE_FIXTURES) -> str:
    """What lifts a stand-in: its node fixture's one `# Lifted by:` header line (HQ batch-7 ruling 3; single source)."""
    path = fixtures / f"{fixture}.pp"
    found = [line.removeprefix(LIFTED_BY).strip()
             for line in (path.read_text().splitlines() if path.is_file() else []) if line.startswith(LIFTED_BY)]
    if len(found) != 1 or not found[0]:
        generator.fail(f"node fixture {fixture}: needs exactly one '{LIFTED_BY} <what>' header line ({path})")
    return found[0]


def standins(rows, verified, fixtures: Path = NODE_FIXTURES) -> list[tuple[str, str, str]]:
    """(class, node fixture, lifted by) for every verified class whose GREEN used a mock-apply node fixture."""
    return [(name, rows[name].node_fixture, lifted_by(rows[name].node_fixture, fixtures))
            for name in sorted(verified) if name in rows and rows[name].node_fixture]


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
    if sys.argv[1:] not in ([], ["--standins"]):
        generator.fail(f"usage: {Path(sys.argv[0]).name} [--standins]")

    rows = generator.parse_plan()
    migrations = generator.git_migrations()
    blocked = generator.read_blocked()
    flagged = generator.find_flagged_migrations(migrations)
    owner_validated = {name for name, row in rows.items() if row.owner_validated}
    conflicting = sorted(owner_validated & set(blocked))
    if conflicting:
        generator.fail("owner_validated classes must not also be blocked: " + ", ".join(conflicting))
    tracker = generator.read_tracker()
    retired = generator.retired_classes(tracker, rows, blocked)
    done = set(migrations) - set(blocked) - owner_validated - set(retired)
    prod = generator.read_prod_nodes()
    pending, gated = generator.topological_pending(rows, done, set(blocked), owner_validated, prod)

    states = {name: verification_state(name, migrations[name], flagged) for name in sorted(done)}
    verified = [name for name, (state, _) in states.items() if state == VERIFIED]
    stand_in = standins(rows, verified)
    if sys.argv[1:] == ["--standins"]:  # machine-readable, for the pre-commit hook's batch-report check
        for row in stand_in:
            print("\t".join(row))
        return

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

    print(f"Done split: {len(verified) - len(stand_in)} {VERIFIED} / {len(stand_in)} {VERIFIED_STANDIN} / "
          f"{len(done) - len(verified)} {PENDING_RECONCILIATION}")
    import phase3  # noqa: PLC0415  (tools dir; Phase 3 behaviour state, HQ 2026-11-16)
    behaviour = {name: phase3.behaviour_state(name)["state"] for name in sorted(done)}
    counts: dict[str, int] = {}
    for b in behaviour.values():
        counts[b] = counts.get(b, 0) + 1
    print("Behaviour (Phase 3, separate from the Phase 1 record): "
          + " / ".join(f"{counts[k]} {k}" for k in sorted(counts)) + f" (of {len(done)} done)")

    print("\nDone classes by verification state (derived from .codex_state/reviews/)")
    stand_in_names = {name for name, _, _ in stand_in}
    print_table(
        ("class", "state", "tracker marker", "latest v2 verdict", "behaviour"),
        [
            (
                f"{generator.PREFIX}{name}",
                VERIFIED_STANDIN if name in stand_in_names else state,
                marker(tracker.get(name)),
                "PASS" if state == VERIFIED else failing_checks(verdict),
                behaviour[name],
            )
            for name, (state, verdict) in sorted(states.items(), key=lambda item: (item[1][0] != VERIFIED, item[0]))
        ],
    )

    print(f"\nStand-ins ({VERIFIED_STANDIN}: the GREEN used a mock-apply node fixture; behaviour NOT verified)")
    print_table(("class", "node fixture", "lifted by"),
                [(f"{generator.PREFIX}{name}", fixture, lift) for name, fixture, lift in stand_in])

    print("\nBlocked classes")
    print_table(
        ("class", "category", "reason"),
        [
            (f"{generator.PREFIX}{name}", blocked_category(reason), short_reason(reason))
            for name, reason in sorted(blocked.items())
        ],
    )

    print("\nRetired classes (removed from the module)")
    print_table(("class", "reason"), [(f"{generator.PREFIX}{name}", reason) for name, reason in sorted(retired.items())])

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
