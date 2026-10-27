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
MAX_FINDINGS = 12


def plan_line(row: generator.ClassRow) -> str:
    fields = [f"resource_type={row.resource_type}"]
    if row.title:
        fields.append(f"title={row.title}")
    fields += [f"internal_deps={','.join(row.internal_deps) or '-'}",
               f"required_base={','.join(row.required_base) or '-'}",
               f"required_external={','.join(row.required_external) or '-'}"]
    if row.owner_validated:
        fields.append(f"owner_validated={row.owner_validated}")
    return " ".join(fields)


def params_line(cls: str, params_dir: Path = PARAMS_DIR) -> str:
    path = params_dir / f"{cls}.json"
    if not path.is_file():
        return "none (class: rendered as `include`; define: the harness dies without one)"
    try:
        keys = list(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        return f"{path} UNREADABLE ({exc})"
    return f"~/.config/infra_populi/params/{cls}.json keys: {', '.join(keys) or '(empty)'}"


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


def packet(cls: str) -> str:
    base = baseline.load()
    rows = generator.parse_plan()
    lines = [f"ORIENTATION PACKET puppet_infrastructure::{cls} (facts gathered before you started)"]
    row = rows.get(cls)
    lines.append(f"plan: {plan_line(row)}" if row else "plan: CLASS NOT IN migration_plan.md")
    drift = baseline.local_drift(cls, base)
    lines.append(f"baseline: {base.name} ({base.commit[:7]}); drift: "
                 + ("none (manifest + templates/files identical)" if not drift else
                    f"DIFFERS in {', '.join(drift)} (not yours to sync: stop and report)"))
    report = pregate.pregate_class(cls)
    findings = [f"{check}: {detail}" for level, check, detail in report.lines if level in ("FINDING", "ERROR")]
    lines.append(f"pregate: {report.status}" + (f" ({len(findings)})" if findings else ""))
    lines += [f"  - {f}" for f in findings[:MAX_FINDINGS]]
    if len(findings) > MAX_FINDINGS:
        lines.append(f"  - ... {len(findings) - MAX_FINDINGS} more: run .codex_state/tools/pregate.sh {cls}")
    lines.append(f"params fixture: {params_line(cls)}")
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
