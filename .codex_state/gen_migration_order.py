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

    @property
    def sort_key(self) -> tuple[int, int, int, str]:
        return (self.complexity, self.dep_score, self.p8_surface, self.name)


@dataclass(frozen=True)
class MigrationCommit:
    commit: str
    date: str


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
        )

    if not rows:
        fail("migration_plan.md class table contains no class rows")
    return rows


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
        output = run_git(["log", "--format=%H", f"{migration.commit}..HEAD", "--", manifest])
        if output.strip():
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
    rows: dict[str, ClassRow], done: set[str], blocked: set[str]
) -> tuple[list[ClassRow], set[str]]:
    pending = set(rows) - done - blocked
    placed: set[str] = set()
    ordered: list[ClassRow] = []

    while pending:
        schedulable = [
            rows[name]
            for name in pending
            if all(dep in done or dep in placed for dep in rows[name].internal_deps)
        ]
        if not schedulable:
            unmet = {
                name: tuple(
                    dep
                    for dep in rows[name].internal_deps
                    if dep not in done and dep not in placed
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

        chosen = sorted(schedulable, key=lambda row: row.sort_key)[0]
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


def table_row(index: int | str, row: ClassRow) -> str:
    deps = ",".join(row.internal_deps)
    return (
        f"| {index} | `{PREFIX}{row.name}` | {row.complexity} | {row.dep_score} | "
        f"{row.p8_surface} | {row.self_contained} | {deps} |"
    )


def render(
    rows: dict[str, ClassRow],
    done: set[str],
    blocked: dict[str, str],
    flagged: set[str],
    pending_order: list[ClassRow],
    gated: set[str],
) -> str:
    found_done = sorted(done & set(rows), key=lambda name: rows[name].sort_key)
    unknown_done = sorted(done - set(rows))
    found_blocked = sorted(blocked.keys() & set(rows), key=lambda name: rows[name].sort_key)
    unknown_blocked = sorted(blocked.keys() - set(rows))
    found_gated = sorted(gated & set(rows), key=lambda name: rows[name].sort_key)
    needs_verification = sorted((flagged - set(blocked)) & set(rows), key=lambda name: rows[name].sort_key)
    unknown_flagged = sorted((flagged - set(blocked)) - set(rows))
    total = len(rows)
    done_count = len(done & set(rows))
    blocked_count = len(blocked.keys() & set(rows))
    gated_count = len(found_gated)
    pending_count = len(pending_order)
    next_class = f"{PREFIX}{pending_order[0].name}" if pending_order else "all migrated"
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
        "The `[from: release-0.9.8]` annotation lives in migrated_classes.txt, not here.",
        "",
        f"Status summary: {done_count} done / {blocked_count} blocked / {gated_count} gated / "
        f"{len(needs_verification)} needs verification / {pending_count} pending / {total} total.",
        "",
        f"Next class: `{next_class}`" if next_class != "all migrated" else "Next class: all migrated",
        "",
        "## DONE (git-derived)",
        "",
        "| # | class | cx | dep | p8 | sc | internal_deps |",
        "|---:|---|---:|---:|---:|---|---|",
    ]

    if found_done:
        lines.extend(table_row(index, rows[name]) for index, name in enumerate(found_done, start=1))
    else:
        lines.append("| - | - | - | - | - | - | - |")

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
            "| # | class | cx | dep | p8 | sc | internal_deps |",
            "|---:|---|---:|---:|---:|---|---|",
        ]
    )
    if pending_order:
        lines.extend(table_row(index, row) for index, row in enumerate(pending_order, start=1))
    else:
        lines.append("| - | - | - | - | - | - | - |")

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
    done = set(migrations) - set(blocked)
    pending_order, gated = topological_pending(rows, done, set(blocked))
    output = render(rows, done, blocked, flagged, pending_order, gated)
    ORDER_PATH.write_text(output, encoding="utf-8")

    unknown_done = sorted(done - set(rows))
    unknown_blocked = sorted(set(blocked) - set(rows))
    needs_verification = sorted((flagged - set(blocked)) & set(rows), key=lambda name: rows[name].sort_key)
    done_count = len(done & set(rows))
    blocked_count = len(set(blocked) & set(rows))
    gated_count = len(gated & set(rows))
    next_class = f"{PREFIX}{pending_order[0].name}" if pending_order else "all migrated"
    print(
        f"{done_count} done / {blocked_count} blocked / {gated_count} gated / "
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


if __name__ == "__main__":
    main()
