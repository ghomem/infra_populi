#!/usr/bin/env python3
"""Orientation packet (step 3.2): a compact block of FACTS about one class for the Codex prompt, so the
executor does not rediscover them. Facts only, no instructions beyond the record recipe.

  orientation.py <class>      prints the packet (exit 0; a source that cannot be read is shown as such)

Sources: migration_plan.md (via the generator), baseline drift (baseline.py), pregate (laptop +
puppet8master), the params fixture's KEYS (never its values), the master's module inventory.
"""

from __future__ import annotations

import json
import re
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

PARAMS_DIR = Path.home() / ".config" / "infra_populi" / "params"
RULINGS = TOOLS.parent / "rules" / "class_rulings.txt"
MAX_FINDINGS = 12


def plan_line(row: generator.ClassRow) -> str:
    fields = [f"resource_type={row.resource_type}"]
    if row.title:
        fields.append(f"title={row.title}")
    fields += [f"internal_deps={','.join(row.internal_deps) or '-'}",
               f"required_base={','.join(f'{n} [{o}]' if o else n for n, o in row.required_base_spec) or '-'}",
               f"required_external={','.join(row.required_external) or '-'}"]
    if row.owner_validated:
        fields.append(f"owner_validated={row.owner_validated}")
    return " ".join(fields)


def params_line(cls: str, params_dir: Path = PARAMS_DIR) -> str:
    path = params_dir / f"puppet_infrastructure::{cls}.json"  # same name test_class.sh reads
    if not path.is_file():
        return "none (class: rendered as `include`; define: the harness dies without one)"
    try:
        keys = list(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        return f"{path} UNREADABLE ({exc})"
    return f"~/.config/infra_populi/params/{path.name} keys: {', '.join(keys) or '(empty)'}"


def ruling_lines(cls: str, path: Path = RULINGS) -> list[str]:
    """HQ rulings that name a change in this class (rules/class_rulings.txt: `<class> <ruled change> — <ref>`)."""
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        name, _, ruling = line.partition(" ")
        if name == cls and ruling.strip():
            out.append(ruling.strip())
    return out


def module_lines(manifest: str, inv: dict) -> list[str]:
    used = set()
    for name in pregate.resource_types(manifest) | pregate.declared_classes(manifest):
        mod = inv["types"].get(name) or inv["classes"].get(name)
        if mod:
            used.add(mod)
    out = []
    for mod in sorted(used):
        meta = inv["modules"].get(mod, {})
        kind = "vendored" if meta.get("kind") == "vendored" else "Puppetfile"
        out.append(f"{meta.get('forge', mod)} {meta.get('version') or '?'} ({kind})")
    return out


def first_migrate_commit(cls: str) -> str | None:
    """The class's first `P8: migrate puppet_infrastructure::<cls>` commit, or None for a class never migrated."""
    out = generator.run_git(["log", "--reverse", "--format=%H%x09%s"])
    for line in out.splitlines():
        commit, _, subject = line.partition("\t")
        if re.fullmatch(rf"P8: migrate puppet_infrastructure::{cls}\b.*", subject):
            return commit
    return None


def pre_migration_drift(cls: str, base: "baseline.Baseline", first: str) -> list[str]:
    """Class paths whose content just before `first` differs from the baseline (hazard 8 for a re-migration)."""
    drift = []
    for path in baseline.class_paths(cls, base.commit, base.upstream):
        before = generator.run_git(["show", f"{first}^:{path}"]) if path_in(first + "^", path) else None
        upstream = baseline.git_show(base.upstream, base.commit, path)
        if (before.encode() if before is not None else None) != upstream:
            drift.append(path)
    return drift


def path_in(ref: str, path: str) -> bool:
    return bool(generator.run_git(["ls-tree", "--name-only", ref, "--", path]).strip())


def packet(cls: str) -> str:
    base = baseline.for_class(cls)
    rows = generator.parse_plan()
    lines = [f"ORIENTATION PACKET puppet_infrastructure::{cls} (facts gathered before you started)"]
    row = rows.get(cls)
    lines.append(f"plan: {plan_line(row)}" if row else "plan: CLASS NOT IN migration_plan.md")
    first = first_migrate_commit(cls)
    if first is None:
        drift = baseline.local_drift(cls, base)
        lines.append(f"baseline: {base.name} ({base.commit[:7]}); drift: "
                     + ("none (manifest + templates/files identical)" if not drift else
                        f"DIFFERS in {', '.join(drift)} (not yours to sync: stop and report)"))
    else:
        # 2026-11-17 (mysql_server): for a done class the local content IS its earlier migration; hazard-8 drift is
        # what the content looked like just before the first migrate commit
        drift = pre_migration_drift(cls, base, first)
        lines.append(f"baseline: {base.name} ({base.commit[:7]}); RE-MIGRATION of a done class (first migrate commit "
                     f"{first[:7]}): the local manifest is that earlier migration, and its differences from the baseline "
                     "are expected — keep them and apply only the HQ ruling below on top; drift before the first "
                     "migration: " + ("none" if not drift else
                                      f"DIFFERS in {', '.join(drift)} (not yours to sync: stop and report)"))
    report = pregate.pregate_class(cls)
    findings = [f"{check}: {detail}" for level, check, detail in report.lines if level in ("FINDING", "ERROR")]
    lines.append(f"pregate: {report.status}" + (f" ({len(findings)})" if findings else ""))
    lines += [f"  - {f}" for f in findings[:MAX_FINDINGS]]
    if len(findings) > MAX_FINDINGS:
        lines.append(f"  - ... {len(findings) - MAX_FINDINGS} more: run .codex_state/tools/pregate.sh {cls}")
    lines.append(f"params fixture: {params_line(cls)}")
    lines += [f"HQ ruling for this class: {r}" for r in ruling_lines(cls)]
    manifest = (baseline.REPO / f"manifests/{cls}.pp").read_text(encoding="utf-8")
    try:
        mods = module_lines(manifest, review_class.master_inventory())
        lines.append("modules on puppet8master used by the class: " + ("; ".join(mods) or "none"))
    except RuntimeError as exc:
        lines.append(f"modules: master inventory unavailable ({exc})")
    lines.append(f"harness: ~/.local/bin/infra_populi_tools/test_class.sh {cls} (clean node again: --revert-first)")
    lines.append(f"record (the only way): .codex_state/tools/record_green.sh {cls} — checks the GREEN stamp, the "
                 f"2-line header (purpose or '{base.name} manifest validated unchanged' + every module dependency "
                 "with its version), the composites; writes the tracker marker; commits; regenerates the "
                 "order file; pushes. Never edit migrated_classes.txt or migration_order.md yourself.")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    print(packet(re.sub(r"^puppet_infrastructure::", "", argv[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
