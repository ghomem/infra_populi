"""Draft helper (not a tool): add a variant and its checks to a check set (HQ 2026-11-27 item 1), written back through
the converter's dumper (behaviour_move.dump), as the sets were written.

    from setedit import add_variant
    add_variant("caching_nameserver", {"name": "rhel", "node": "rhel9", "why": "..."}, [check, ...],
                cover={"<outcome text start>": ["check-id", ...]})

`cover` maps an outcome row (by the start of its text) to the checks that now probe it: an uncovered row becomes a
covered one with those checks (its `from` kept). A variant on a node of another OS family gets that family's catalog
from the plan (behaviour_move.apply_block), and the block's expected run-2 events take that family's too.
"""
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".codex_state" / "tools"))
import behaviour_move as bm  # noqa: E402

CHECKS = REPO / "spec" / "behaviour" / "checks"


def add_variant(cls: str, variant: dict, checks: list[dict], cover: dict) -> None:
    path = CHECKS / f"{cls}.yml"
    data = yaml.safe_load(path.read_text())
    names = [v["name"] for v in data.get("variants") or []]
    if variant["name"] in names:
        raise SystemExit(f"{cls}: variant {variant['name']} exists")
    data.setdefault("variants", []).append(variant)
    for c in checks:
        c.setdefault("variant", variant["name"])
    data["checks"] += checks
    for start, ids in cover.items():
        rows = [o for o in data["outcomes"] if str(o["outcome"]).startswith(start)]
        if len(rows) != 1:
            raise SystemExit(f"{cls}: {len(rows)} outcome rows start with {start!r}")
        row = rows[0]
        row.pop("uncovered", None)
        row["checks"] = list(dict.fromkeys(list(row.get("checks") or []) + list(ids)))
    kinds = bm.nodes_data()["nodes"]
    family = kinds[variant.get("node", data["apply"]["node"])]["os_family"]
    if family not in data["apply"]["catalog"]:
        ctx = {data["apply"]["node"]: None, variant["node"]: None}
        block = bm.apply_block(cls, data, ctx)
        data["apply"]["catalog"][family] = block["catalog"][family]
        events = list(data["apply"].get("expected_run2_events") or [])
        for e in block.get("expected_run2_events") or []:
            if e not in events:
                events.append(e)
        if events:
            data["apply"]["expected_run2_events"] = events
    # the top-level order the converter writes: apply last
    apply = data.pop("apply")
    data["apply"] = apply
    path.write_text(bm.dump(data))
