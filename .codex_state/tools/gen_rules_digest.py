#!/usr/bin/env python3
"""Generated "current rules" digest of DESIGN_DECISIONS.md (HQ ruling 12, step 3.5). P2: the decision log stays
the append-only source; this file is DERIVED and never hand-edited.

  gen_rules_digest.py            write .codex_state/rules/CURRENT_RULES.md
  gen_rules_digest.py --check    exit 1 if the digest is stale
  gen_rules_digest.py --staged   same, on the INDEX (the engine pre-commit hook: both files staged together)

Mechanics: one block per dated entry, newest first, with its rule lines (numbered items, `Rule:`/`Decision:`/
`Fact:`/`Ruling` lines — first line each, truncated). A `supersedes <date> "<title words>"` reference marks the
matching older entry SUPERSEDED (in whole or part — read both); references that match no entry are listed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / ".codex_state" / "DESIGN_DECISIONS.md"
DIGEST = REPO / ".codex_state" / "rules" / "CURRENT_RULES.md"
HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) — (.+)$")
RULE_LINE = re.compile(r"^(?:\d+\.\s|(?:Rule|Decision|Fact|Ruling)\b[^:]{0,40}:)")
SUPERSEDES = re.compile(r"supersed\w*\s+(?:its |the |as to \w+ )?(\d{4}-\d{2}-\d{2})?[^\"\n]{0,40}\"([^\"]+)\"",
                        re.IGNORECASE)
MAX = 170


@dataclass
class Entry:
    index: int
    date: str
    title: str
    lines: list[str]
    superseded_by: list[str] = field(default_factory=list)


def parse(text: str) -> list[Entry]:
    entries: list[Entry] = []
    for line in text.splitlines():
        m = HEADING.match(line)
        if m:
            entries.append(Entry(len(entries), m.group(1), m.group(2).strip(), []))
        elif entries:
            entries[-1].lines.append(line)
    return entries


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def resolve(entries: list[Entry]) -> list[str]:
    unresolved = []
    for e in entries:
        body = " ".join(e.lines)
        for m in SUPERSEDES.finditer(body):
            date, words = m.group(1), norm(m.group(2))
            targets = [t for t in entries if t.index < e.index and (date is None or t.date == date)
                       and words and (words[:30] in norm(t.title) or norm(t.title)[:30] in words)]
            if targets:
                for t in targets:
                    ref = f"{e.date} — {e.title}"
                    if ref not in t.superseded_by:
                        t.superseded_by.append(ref)
            else:
                unresolved.append(f"{e.date} — {e.title}: supersedes {date or '(no date)'} \"{m.group(2)}\"")
    return unresolved


def rule_lines(e: Entry) -> list[str]:
    out = []
    for line in e.lines:
        s = line.strip()
        if RULE_LINE.match(s):
            out.append(s if len(s) <= MAX else s[:MAX - 1] + "…")
    return out


def render(text: str) -> str:
    entries = parse(text)
    unresolved = resolve(entries)
    superseded = sum(1 for e in entries if e.superseded_by)
    out = ["# Current rules digest", "",
           "DERIVED from `.codex_state/DESIGN_DECISIONS.md` — never hand-edit; regenerate with "
           "`python3 .codex_state/tools/gen_rules_digest.py`. The log is authoritative: read the full entry before "
           "acting on a line here. SUPERSEDED marks are mechanical (from `supersedes <date> \"<title>\"` references) "
           "and may be partial.", "",
           f"{len(entries)} entries; {superseded} marked superseded (in whole or part); newest first.", ""]
    for e in reversed(entries):
        mark = f" — **SUPERSEDED (whole or part) by** {'; '.join(e.superseded_by)}" if e.superseded_by else ""
        out.append(f"## {e.date} — {e.title}{mark}")
        out += [f"- {l}" for l in rule_lines(e)] or ["- (no numbered/Rule/Decision lines; read the entry)"]
        out.append("")
    if unresolved:
        out += ["## Supersession references that match no earlier entry heading", ""]
        out += [f"- {u}" for u in unresolved]
        out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    digest = render(SOURCE.read_text(encoding="utf-8"))
    if argv == ["--check"]:
        current = DIGEST.read_text(encoding="utf-8") if DIGEST.is_file() else ""
        if current != digest:
            print(f"STALE: {DIGEST.relative_to(REPO)} — run python3 .codex_state/tools/gen_rules_digest.py",
                  file=sys.stderr)
            return 1
        print("rules digest current")
        return 0
    if argv == ["--staged"]:
        def staged(path: Path) -> str:
            proc = subprocess.run(["git", "-C", str(REPO), "show", f":{path.relative_to(REPO)}"],
                                  capture_output=True, text=True)
            return proc.stdout if proc.returncode == 0 else ""
        if render(staged(SOURCE)) != staged(DIGEST):
            print(f"STALE (staged): {DIGEST.relative_to(REPO)} does not match the staged DESIGN_DECISIONS.md — run "
                  "python3 .codex_state/tools/gen_rules_digest.py and stage it", file=sys.stderr)
            return 1
        return 0
    if argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    DIGEST.parent.mkdir(parents=True, exist_ok=True)
    DIGEST.write_text(digest, encoding="utf-8")
    print(f"wrote {DIGEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
