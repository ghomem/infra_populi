#!/usr/bin/env python3
"""Regenerate the Puppet migration order from migration_plan.md and git."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PLAN_PATH = SCRIPT_DIR / "migration_plan.md"
ORDER_PATH = SCRIPT_DIR / "migration_order.md"
BLOCKED_PATH = SCRIPT_DIR / "blocked.txt"
TRACKER_PATH = SCRIPT_DIR / "migrated_classes.txt"
FLEET_PATH = SCRIPT_DIR / "diagnosis" / "fleet_class_usage.md"
REVIEWS_PATH = SCRIPT_DIR / "reviews"
REMIGRATION_PATH = SCRIPT_DIR / "rules" / "remigration_order.txt"
VERIFIED = "verified (gate v2)"
PENDING_RECONCILIATION = "done (gate v1, reconciliation pending)"
BASELINE_ENV = SCRIPT_DIR / "baseline.env"
PREFIX = "puppet_infrastructure::"
REQUIRED_COLUMNS = {
    "class",
    "complexity",
    "dep_score",
    "p8_surface",
    "self_contained",
    "internal_deps",
    "resource_type",
}
KNOWN_GAP = (
    "node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant "
    "(routed via shared filesystem_base, which node_base already depends on) and was "
    "a considered omission, not an oversight. Revisit only if composition ever depends "
    "on it directly."
)


def baseline_name() -> str:
    """Declared baseline name from .codex_state/baseline.env (single source)."""
    for line in BASELINE_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("BASELINE_NAME="):
            return line.split("=", 1)[1].strip()
    fail(f"{BASELINE_ENV} has no BASELINE_NAME")


@dataclass(frozen=True)
class ClassRow:
    name: str
    complexity: int
    dep_score: int
    p8_surface: int
    self_contained: str
    internal_deps: tuple[str, ...]
    resource_type: str
    title: str
    required_base: tuple[str, ...]
    required_external: tuple[str, ...]
    owner_validated: str
    node_fixture: str = ""

    @property
    def sort_key(self) -> tuple[int, int, int, str]:
        return (self.complexity, self.dep_score, self.p8_surface, self.name)


@dataclass(frozen=True)
class MigrationCommit:
    commit: str
    date: str


@dataclass(frozen=True)
class TrackerEntry:
    """One migrated_classes.txt line. Marker grammar (HQ checkpoint-1 ruling 3):
    `[from: <ref>]` or `[from: <ref>; upstream defect fixed: <short>]`."""

    name: str
    done: bool
    from_ref: str
    defect_fixed: str
    mock_apply: str = ""


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def clean_cell(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith("`") and cell.endswith("`") and len(cell) >= 2:
        cell = cell[1:-1]
    return cell.strip()


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [clean_cell(cell) for cell in stripped[1:-1].split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_int(value: str, column: str, class_name: str) -> int:
    try:
        return int(value)
    except ValueError:
        fail(f"invalid integer in {column} for {class_name}: {value!r}")


def parse_plan() -> dict[str, ClassRow]:
    if not PLAN_PATH.exists():
        fail(f"plan file not found: {PLAN_PATH}")

    lines = PLAN_PATH.read_text(encoding="utf-8").splitlines()
    header_index = None
    headers: list[str] = []
    for index, line in enumerate(lines):
        cells = split_markdown_row(line)
        if cells and "class" in cells and "internal_deps" in cells:
            headers = cells
            header_index = index
            break

    if header_index is None:
        fail("could not find migration_plan.md class table header")

    missing = sorted(REQUIRED_COLUMNS - set(headers))
    if missing:
        fail(f"migration_plan.md table missing required columns: {', '.join(missing)}")

    if header_index + 1 >= len(lines) or not is_separator_row(split_markdown_row(lines[header_index + 1])):
        fail("migration_plan.md class table header is not followed by a separator row")

    indexes = {name: headers.index(name) for name in REQUIRED_COLUMNS}
    title_index = headers.index("title") if "title" in headers else None
    required_base_index = headers.index("required_base") if "required_base" in headers else None
    required_external_index = (
        headers.index("required_external") if "required_external" in headers else None
    )
    owner_validated_index = (
        headers.index("owner_validated") if "owner_validated" in headers else None
    )
    node_fixture_index = headers.index("node_fixture") if "node_fixture" in headers else None
    rows: dict[str, ClassRow] = {}

    for line_number, line in enumerate(lines[header_index + 2 :], start=header_index + 3):
        cells = split_markdown_row(line)
        if not cells:
            break
        if len(cells) != len(headers):
            fail(
                f"malformed table row at {PLAN_PATH}:{line_number}: "
                f"expected {len(headers)} columns, found {len(cells)}"
            )

        full_class = cells[indexes["class"]]
        if not full_class.startswith(PREFIX):
            fail(f"class at {PLAN_PATH}:{line_number} lacks {PREFIX!r} prefix: {full_class!r}")
        name = full_class.removeprefix(PREFIX)
        if not name:
            fail(f"empty class short-name at {PLAN_PATH}:{line_number}")
        if name in rows:
            fail(f"duplicate class row in migration_plan.md: {name}")

        self_contained = cells[indexes["self_contained"]].lower()
        if self_contained not in {"yes", "no"}:
            fail(f"invalid self_contained for {name}: {self_contained!r}")

        deps_cell = cells[indexes["internal_deps"]]
        deps = tuple(dep.strip() for dep in deps_cell.split(",") if dep.strip())

        resource_type = cells[indexes["resource_type"]].lower()
        if resource_type not in {"class", "define"}:
            fail(f"invalid resource_type for {name}: {resource_type!r}")

        title = cells[title_index] if title_index is not None else ""
        required_base_cell = cells[required_base_index] if required_base_index is not None else ""
        required_base = tuple(
            base.strip() for base in required_base_cell.split(",") if base.strip()
        )
        required_external_cell = (
            cells[required_external_index] if required_external_index is not None else ""
        )
        required_external = tuple(
            external.strip()
            for external in required_external_cell.split(",")
            if external.strip()
        )
        owner_validated = cells[owner_validated_index] if owner_validated_index is not None else ""
        if owner_validated and not re.fullmatch(r"[A-Za-z0-9_]+", owner_validated):
            fail(f"invalid owner_validated class short-name for {name}: {owner_validated!r}")

        node_fixture = cells[node_fixture_index] if node_fixture_index is not None else ""
        if node_fixture and not re.fullmatch(r"[a-z0-9_]+", node_fixture):
            fail(f"invalid node_fixture for {name}: {node_fixture!r}")
        if node_fixture and not (SCRIPT_DIR / "tools" / "tests" / "fixtures" / "node" / f"{node_fixture}.pp").is_file():
            fail(f"node_fixture for {name} does not exist: tools/tests/fixtures/node/{node_fixture}.pp")
        rows[name] = ClassRow(
            name=name,
            complexity=parse_int(cells[indexes["complexity"]], "complexity", name),
            dep_score=parse_int(cells[indexes["dep_score"]], "dep_score", name),
            p8_surface=parse_int(cells[indexes["p8_surface"]], "p8_surface", name),
            self_contained=self_contained,
            internal_deps=deps,
            resource_type=resource_type,
            title=title,
            required_base=required_base,
            required_external=required_external,
            owner_validated=owner_validated,
            node_fixture=node_fixture,
        )

    if not rows:
        fail("migration_plan.md class table contains no class rows")
    for name, row in rows.items():
        if not row.owner_validated:
            continue
        if row.resource_type != "define":
            fail(f"owner_validated is only valid for defines: {name}")
        owner = rows.get(row.owner_validated)
        if owner is None:
            fail(f"owner_validated owner for {name} is not in migration_plan.md: {row.owner_validated}")
        if owner.resource_type != "class":
            fail(f"owner_validated owner for {name} is not a class: {row.owner_validated}")
    return rows


TRACKER_LINE = re.compile(
    r"(?:(?P<name>[A-Za-z0-9_]+)(?P<done> Done)?|Done (?P<name2>[A-Za-z0-9_]+))"
    r"(?: \[from: (?P<ref>[A-Za-z0-9._-]+)(?:; upstream defect fixed: (?P<defect>[^\]\[;]+?))?"
    r"(?:; mock-apply: (?P<mock>[^\]\[;]+?))?\])?"
)


def parse_tracker_line(line: str) -> TrackerEntry | None:
    """Parse one tracker line; None for blank/comment lines; fail() on anything malformed.
    Accepts `<class>`, `<class> Done [marker]` and the historical `Done <class> [marker]`."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    match = TRACKER_LINE.fullmatch(stripped)
    if not match or (match.group("ref") and not (match.group("done") or match.group("name2"))):
        fail(f"malformed migrated_classes.txt line: {stripped!r}")
    return TrackerEntry(
        name=match.group("name") or match.group("name2"),
        done=bool(match.group("done") or match.group("name2")),
        from_ref=match.group("ref") or "",
        defect_fixed=(match.group("defect") or "").strip(),
        mock_apply=(match.group("mock") or "").strip(),
    )


def read_tracker(path: Path | None = None) -> dict[str, TrackerEntry]:
    path = path or TRACKER_PATH
    entries: dict[str, TrackerEntry] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = parse_tracker_line(line)
        if entry is None:
            continue
        if entry.name in entries:
            fail(f"duplicate class in {path.name}: {entry.name}")
        entries[entry.name] = entry
    return entries


def tracker_mismatches(entries: dict[str, TrackerEntry], done: set[str]) -> tuple[list[str], list[str]]:
    """(git-done but not Done in the tracker, Done in the tracker but not git-done)."""
    tracked_done = {name for name, entry in entries.items() if entry.done}
    return sorted(done - tracked_done), sorted(tracked_done - done)


def read_prod_nodes(path: Path | None = None) -> dict[str, int]:
    """Production node statements per class (`prod` column of fleet_class_usage.md, composites propagated).
    Step 4.3: the secondary sort key after dependencies. A class missing from the table counts 0."""
    path = path or FLEET_PATH
    if not path.is_file():
        return {}
    prod: dict[str, int] = {}
    header: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = split_markdown_row(line)
        if cells[:2] == ["class", "prod"]:
            header = cells
            continue
        if header and len(cells) == len(header) and re.fullmatch(r"[a-z][a-z0-9_]*", cells[0]):
            try:
                prod[cells[0]] = int(cells[1])
            except ValueError:
                fail(f"invalid prod value for {cells[0]} in {path.name}: {cells[1]!r}")
        elif header and not cells:
            header = []
    return prod


def latest_verdict(name: str, reviews: Path | None = None) -> dict | None:
    reviews = reviews or REVIEWS_PATH
    files = sorted((reviews / name).glob("*.json")) if (reviews / name).is_dir() else []
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def verification_state(name: str, migration: "MigrationCommit", flagged: set[str],
                       reviews: Path | None = None) -> tuple[str, dict | None]:
    """Derived (HQ checkpoint-1 ruling 1): verified only by a reviewer-v2 PASS whose reviewed commit is the
    class's current effective commit, with no non-record manifest change since."""
    verdict = latest_verdict(name, reviews)
    reviewed = (verdict or {}).get("migrate_commit") or ""
    if verdict and verdict.get("verdict") == "PASS" and reviewed and migration.commit.startswith(reviewed) \
            and name not in flagged:
        return VERIFIED, verdict
    return PENDING_RECONCILIATION, verdict


def read_remigration_order(path: Path | None = None) -> list[tuple[str, str]]:
    path = path or REMIGRATION_PATH
    if not path.is_file():
        return []
    order = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2 or parts[1] not in ("first", "sink"):
            fail(f"bad line in {path.name}: {line!r}")
        order.append((parts[0], parts[1]))
    return order


def remigration_queue(migrations: dict[str, "MigrationCommit"], flagged: set[str],
                      reviews: Path | None = None, order_path: Path | None = None) -> list[tuple[str, str]]:
    """The HQ-ordered re-migrations still pending reconciliation: [(class, first|sink)]."""
    return [(name, when) for name, when in read_remigration_order(order_path)
            if name in migrations and verification_state(name, migrations[name], flagged, reviews)[0] != VERIFIED]


def run_git(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        fail(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def git_migrations() -> dict[str, MigrationCommit]:
    output = run_git(["log", "--format=%H%x09%cI%x09%s"])
    pattern = re.compile(rf"\bP8: migrate\s+{re.escape(PREFIX)}([A-Za-z0-9_]+)\b")
    migrations: dict[str, MigrationCommit] = {}

    for line in output.splitlines():
        if "P8: migrate" not in line:
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        commit, commit_date, subject = parts
        match = pattern.search(subject)
        if match:
            name = match.group(1)
            if name not in migrations:
                migrations[name] = MigrationCommit(commit=commit, date=commit_date)
    return migrations


def find_flagged_migrations(migrations: dict[str, MigrationCommit]) -> set[str]:
    flagged: set[str] = set()
    for name, migration in migrations.items():
        manifest = f"manifests/{name}.pp"
        output = run_git(["log", "--format=%s", f"{migration.commit}..HEAD", "--", manifest])
        if any(not subject.startswith("P8: record") for subject in output.splitlines()):
            flagged.add(name)
    return flagged


def read_blocked() -> dict[str, str]:
    if not BLOCKED_PATH.exists():
        return {}

    blocked: dict[str, str] = {}
    for line_number, line in enumerate(BLOCKED_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split(None, 1)
        name = parts[0]
        if not re.fullmatch(r"[A-Za-z0-9_]+", name):
            fail(f"invalid blocked class short-name at {BLOCKED_PATH}:{line_number}: {name!r}")
        if name in blocked:
            fail(f"duplicate blocked class at {BLOCKED_PATH}:{line_number}: {name}")
        blocked[name] = parts[1].strip() if len(parts) > 1 else ""
    return blocked


def topological_pending(
    rows: dict[str, ClassRow],
    done: set[str],
    blocked: set[str],
    owner_validated: set[str],
    prod: dict[str, int] | None = None,
) -> tuple[list[ClassRow], set[str]]:
    prod = prod or {}
    pending = set(rows) - done - blocked - owner_validated
    placed: set[str] = set()
    ordered: list[ClassRow] = []

    while pending:
        schedulable = [
            rows[name]
            for name in pending
            if all(
                dep in done or dep in placed or dep in owner_validated
                for dep in rows[name].internal_deps
            )
        ]
        if not schedulable:
            unmet = {
                name: tuple(
                    dep
                    for dep in rows[name].internal_deps
                    if dep not in done and dep not in placed and dep not in owner_validated
                )
                for name in pending
            }
            gated: set[str] = set()
            while True:
                newly_gated = {
                    name
                    for name in pending - gated
                    if all(dep in blocked or dep in gated for dep in unmet[name])
                }
                if not newly_gated:
                    break
                gated.update(newly_gated)

            genuinely_stuck = pending - gated
            if not genuinely_stuck:
                return ordered, gated

            stuck_lines = []
            for name in sorted(genuinely_stuck):
                waiting = unmet[name]
                stuck_lines.append(f"{name}: {', '.join(waiting) if waiting else '(none)'}")
            fail("dependency cycle or missing dependency; stuck classes waiting on:\n" + "\n".join(stuck_lines))

        # dependencies first (schedulable), then production use (step 4.3), then the plan scores
        chosen = sorted(schedulable, key=lambda row: (-prod.get(row.name, 0), *row.sort_key))[0]
        ordered.append(chosen)
        pending.remove(chosen.name)
        placed.add(chosen.name)

    return ordered, set()


def gated_wait_chains(
    name: str,
    rows: dict[str, ClassRow],
    gated: set[str],
    blocked: set[str],
    memo: dict[str, tuple[tuple[str, ...], ...]],
) -> tuple[tuple[str, ...], ...]:
    if name in memo:
        return memo[name]

    chains: list[tuple[str, ...]] = []
    for dep in rows[name].internal_deps:
        if dep in blocked:
            chains.append((dep,))
        elif dep in gated:
            chains.extend((dep, *chain) for chain in gated_wait_chains(dep, rows, gated, blocked, memo))

    memo[name] = tuple(chains)
    return memo[name]


def format_gated_reason(
    name: str,
    rows: dict[str, ClassRow],
    gated: set[str],
    blocked: set[str],
    memo: dict[str, tuple[tuple[str, ...], ...]],
) -> str:
    formatted: list[str] = []
    for chain in gated_wait_chains(name, rows, gated, blocked, memo):
        steps = [f"`{PREFIX}{dep}`" for dep in chain[:-1]]
        steps.append(f"blocked `{PREFIX}{chain[-1]}`")
        formatted.append(" → ".join(steps))
    return "; ".join(formatted)


def table_row(index: int | str, row: ClassRow, prod: dict[str, int] | None = None) -> str:
    deps = ",".join(row.internal_deps)
    return (
        f"| {index} | `{PREFIX}{row.name}` | {(prod or {}).get(row.name, 0)} | {row.complexity} | {row.dep_score} | "
        f"{row.p8_surface} | {row.self_contained} | {deps} |"
    )


def render(
    rows: dict[str, ClassRow],
    done: set[str],
    blocked: dict[str, str],
    flagged: set[str],
    pending_order: list[ClassRow],
    gated: set[str],
    owner_validated: set[str],
    tracker: dict[str, TrackerEntry] | None = None,
    prod: dict[str, int] | None = None,
    remigrations: list[tuple[str, str]] | None = None,
) -> str:
    prod = prod or {}
    remigrations = remigrations or []
    found_done = sorted((done & set(rows)) - owner_validated, key=lambda name: rows[name].sort_key)
    unknown_done = sorted(done - set(rows))
    found_blocked = sorted(
        (blocked.keys() & set(rows)) - owner_validated,
        key=lambda name: rows[name].sort_key,
    )
    unknown_blocked = sorted(blocked.keys() - set(rows))
    found_gated = sorted((gated & set(rows)) - owner_validated, key=lambda name: rows[name].sort_key)
    found_owner_validated = sorted(owner_validated & set(rows), key=lambda name: rows[name].sort_key)
    needs_verification = sorted(
        ((flagged - set(blocked)) & set(rows)) - owner_validated,
        key=lambda name: rows[name].sort_key,
    )
    unknown_flagged = sorted(((flagged - set(blocked)) - set(rows)) - owner_validated)
    total = len(rows)
    done_count = len((done & set(rows)) - owner_validated)
    blocked_count = len((blocked.keys() & set(rows)) - owner_validated)
    gated_count = len(found_gated)
    owner_validated_count = len(found_owner_validated)
    pending_count = len(pending_order)
    next_class = next_class_name(pending_order, remigrations)
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Puppet Class Migration Order",
        "",
        f"Generated: {generated}",
        "",
        "DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. "
        "MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.",
        "",
        "Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). "
        f"The `[from: {baseline_name()}]` annotation lives in migrated_classes.txt, not here.",
        "",
        f"Status summary: {done_count} done / {owner_validated_count} owner_validated / "
        f"{blocked_count} blocked / {gated_count} gated / "
        f"{len(needs_verification)} needs verification / {pending_count} pending / {total} total.",
        "",
        f"Next class: `{next_class}`" if next_class != "all migrated" else "Next class: all migrated",
        "",
        "Order (step 4.3): HQ re-migrations marked `first`, then the pending queue — dependencies first, then "
        "`prod` (production node statements from `.codex_state/diagnosis/fleet_class_usage.md`, composites "
        "propagated) descending, then cx/dep/p8 — then re-migrations marked `sink`. prod 0 = no production "
        "declaration: those sink until the CTO rules.",
        "",
        "## RE-MIGRATION QUEUE (gate-v1 done, reconciliation pending; HQ ck1 order, `.codex_state/rules/remigration_order.txt`)",
        "",
        "| # | class | when |",
        "|---:|---|---|",
    ]
    if remigrations:
        lines.extend(f"| {i} | `{PREFIX}{name}` | {when} |" for i, (name, when) in enumerate(remigrations, start=1))
    else:
        lines.append("| - | - | - |")
    lines.extend([
        "",
        "## DONE (git-derived)",
        "",
        "| # | class | prod | cx | dep | p8 | sc | internal_deps |",
        "|---:|---|---:|---:|---:|---:|---|---|",
    ])

    if found_done:
        lines.extend(table_row(index, rows[name], prod) for index, name in enumerate(found_done, start=1))
    else:
        lines.append("| - | - | - | - | - | - | - | - |")

    lines.extend(["", "## OWNER-VALIDATED", "", "| # | class | owner |", "|---:|---|---|"])
    if found_owner_validated:
        for index, name in enumerate(found_owner_validated, start=1):
            owner = rows[name].owner_validated
            lines.append(f"| {index} | `{PREFIX}{name}` | `{PREFIX}{owner}` |")
    else:
        lines.append("| - | - | - |")

    lines.extend(["", "## BLOCKED", "", "| # | class | reason |", "|---:|---|---|"])
    if found_blocked:
        for index, name in enumerate(found_blocked, start=1):
            lines.append(f"| {index} | `{PREFIX}{name}` | {blocked[name]} |")
    else:
        lines.append("| - | - | - |")

    lines.extend(["", "## TRANSITIVELY GATED", ""])
    if found_gated:
        memo: dict[str, tuple[tuple[str, ...], ...]] = {}
        for name in found_gated:
            reason = format_gated_reason(name, rows, gated, set(blocked), memo)
            lines.append(f"- `{PREFIX}{name}` — gated by {reason}")
    else:
        lines.append("- None")

    if needs_verification:
        lines.extend(["", "## NEEDS VERIFICATION", ""])
        for name in needs_verification:
            migration = f"`{PREFIX}{name}`"
            lines.append(
                f"- NEEDS VERIFICATION: {migration} — manifest touched after its P8: migrate commit; "
                "confirm whether still migrated or should be blocked."
            )

    lines.extend(
        [
            "",
            "## PENDING QUEUE",
            "",
            "| # | class | prod | cx | dep | p8 | sc | internal_deps |",
            "|---:|---|---:|---:|---:|---:|---|---|",
        ]
    )
    if pending_order:
        lines.extend(table_row(index, row, prod) for index, row in enumerate(pending_order, start=1))
    else:
        lines.append("| - | - | - | - | - | - | - | - |")

    defects = sorted((name, entry) for name, entry in (tracker or {}).items() if entry.defect_fixed)
    if defects:
        lines.extend(["", "## UPSTREAM DEFECTS FIXED LOCALLY (tracker markers, for the CTO batch)", ""])
        lines.extend(
            f"- `{PREFIX}{name}` [from: {entry.from_ref}] — {entry.defect_fixed}" for name, entry in defects
        )

    lines.extend(["", "## KNOWN GAPS", "", KNOWN_GAP, ""])

    if unknown_done:
        lines.extend(
            [
                "<!--",
                "Git-DONE classes not found in migration_plan.md:",
                *[f"- {PREFIX}{name}" for name in unknown_done],
                "-->",
                "",
            ]
        )

    if unknown_blocked:
        lines.extend(
            [
                "<!--",
                "Blocked classes not found in migration_plan.md:",
                *[f"- {PREFIX}{name}" for name in unknown_blocked],
                "-->",
                "",
            ]
        )

    if unknown_flagged:
        lines.extend(
            [
                "<!--",
                "Possibly superseded migrated classes not found in migration_plan.md:",
                *[f"- {PREFIX}{name}" for name in unknown_flagged],
                "-->",
                "",
            ]
        )

    return "\n".join(lines)


def next_class_name(pending_order: list[ClassRow], remigrations: list[tuple[str, str]]) -> str:
    first = [name for name, when in remigrations if when == "first"]
    if first:
        return f"{PREFIX}{first[0]} (re-migration)"
    if pending_order:
        return f"{PREFIX}{pending_order[0].name}"
    sink = [name for name, when in remigrations if when == "sink"]
    return f"{PREFIX}{sink[0]} (re-migration)" if sink else "all migrated"


def classify(class_name: str) -> None:
    rows = parse_plan()
    name = class_name.removeprefix(PREFIX)
    row = rows.get(name)
    if row is None:
        fail(f"class not found in migration_plan.md: {class_name}")

    print(
        json.dumps(
            {
                "name": row.name,
                "resource_type": row.resource_type,
                "title": row.title,
                "required_base": row.required_base,
                "required_external": row.required_external,
                "owner_validated": row.owner_validated,
                "node_fixture": row.node_fixture,
            }
        )
    )


def main() -> None:
    args = sys.argv[1:]
    if args:
        if len(args) == 2 and args[0] == "--classify":
            classify(args[1])
            return
        fail(f"usage: {Path(sys.argv[0]).name} [--classify <class_short_name>]")

    rows = parse_plan()
    migrations = git_migrations()
    blocked = read_blocked()
    flagged = find_flagged_migrations(migrations)
    owner_validated = {name for name, row in rows.items() if row.owner_validated}
    conflicting = sorted(owner_validated & set(blocked))
    if conflicting:
        fail("owner_validated classes must not also be blocked: " + ", ".join(conflicting))
    done = set(migrations) - set(blocked) - owner_validated
    prod = read_prod_nodes()
    pending_order, gated = topological_pending(rows, done, set(blocked), owner_validated, prod)
    tracker = read_tracker()
    remigrations = remigration_queue(migrations, flagged)
    output = render(rows, done, blocked, flagged, pending_order, gated, owner_validated, tracker, prod, remigrations)
    ORDER_PATH.write_text(output, encoding="utf-8")

    unknown_done = sorted(done - set(rows))
    unknown_blocked = sorted(set(blocked) - set(rows))
    needs_verification = sorted(
        ((flagged - set(blocked)) & set(rows)) - owner_validated,
        key=lambda name: rows[name].sort_key,
    )
    done_count = len((done & set(rows)) - owner_validated)
    blocked_count = len((set(blocked) & set(rows)) - owner_validated)
    gated_count = len((gated & set(rows)) - owner_validated)
    owner_validated_count = len(owner_validated & set(rows))
    next_class = next_class_name(pending_order, remigrations)
    print(
        f"{done_count} done / {owner_validated_count} owner_validated / "
        f"{blocked_count} blocked / {gated_count} gated / "
        f"{len(needs_verification)} needs verification / {len(pending_order)} pending / "
        f"{len(rows)} total"
    )
    print(f"next pending class: {next_class}")
    if unknown_done:
        print("git-DONE classes not found in plan table:")
        for name in unknown_done:
            print(f"- {PREFIX}{name}")
    else:
        print("git-DONE classes not found in plan table: none")
    if unknown_blocked:
        print("blocked classes not found in plan table:")
        for name in unknown_blocked:
            print(f"- {PREFIX}{name}")
    else:
        print("blocked classes not found in plan table: none")
    untracked_done, stale_done = tracker_mismatches(tracker, done)
    print(f"git-DONE classes not Done in migrated_classes.txt: {', '.join(untracked_done) or 'none'}")
    print(f"migrated_classes.txt Done classes not git-DONE: {', '.join(stale_done) or 'none'}")
    defects = [name for name, entry in tracker.items() if entry.defect_fixed]
    print(f"upstream defects fixed locally (tracker markers): {', '.join(sorted(defects)) or 'none'}")


if __name__ == "__main__":
    main()
