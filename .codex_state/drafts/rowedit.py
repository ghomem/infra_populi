"""Draft helper (not a tool): replace one `outcomes:` row of a check set, as text, with new rows (HQ 2026-11-27 item 1).

    from rowedit import replace_row
    replace_row("spec/behaviour/checks/x.yml", "<the row's outcome text, its start>", [row, ...])

Each row is a dict (outcome, from, checks | uncovered); it is dumped as YAML at the list's indentation. Comments and
formatting elsewhere in the file are kept. Refuses unless exactly one row starts with the given text.
"""
import re
from pathlib import Path

import yaml


def dump_row(row: dict) -> str:
    text = yaml.safe_dump([row], sort_keys=False, width=120, allow_unicode=True)
    return text


def replace_row(path: str, start: str, rows: list[dict]) -> None:
    p = Path(path)
    lines = p.read_text().split("\n")
    o = next(i for i, l in enumerate(lines) if l == "outcomes:")
    end_list = next(i for i in range(o + 1, len(lines)) if lines[i] and not lines[i].startswith((" ", "-")))
    starts = [i for i in range(o + 1, end_list) if lines[i].startswith("- ")]
    hits = []
    for k, i in enumerate(starts):
        j = starts[k + 1] if k + 1 < len(starts) else end_list
        block = yaml.safe_load("\n".join(lines[i:j]))[0]
        if str(block.get("outcome", "")).startswith(start):
            hits.append((i, j))
    if len(hits) != 1:
        raise SystemExit(f"{path}: {len(hits)} rows start with {start!r}")
    i, j = hits[0]
    new = "".join(dump_row(r) for r in rows).rstrip("\n").split("\n")
    lines[i:j] = new
    p.write_text("\n".join(lines))
    data = yaml.safe_load(p.read_text())
    assert isinstance(data, dict) and data.get("outcomes"), path
