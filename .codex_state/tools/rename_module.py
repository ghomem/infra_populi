#!/usr/bin/env python3
"""The module rename, applied (Phase 2 rename plan, mechanics 1; HQ review of the behaviour suite, ruling 8).

  rename_module.py plan  <new name>    every tracked file it would change, with its count per form; changes nothing
  rename_module.py apply <new name>    rewrites those files and metadata.json's name; prints every replaced line as
                                       `<path>:<line>: <old>  =>  <new>`

Every live reference in every form becomes the new name's: `puppet_infrastructure` -> `<new>`, `Puppet_infrastructure`
-> `<New>`, `puppet-infrastructure` -> `<new, hyphenated>` (paths such as /opt/puppet-infrastructure, unit and instance
names, prose). The scope (.codex_state/rules/rename_scope.txt) keeps history and references to the old repository
as a source as written: excluded files, protected spans, and everything under `derived_from` in the check sets (the
baseline's quotations). Its `also` entries are the approved plan's declared changes beside the rename.
rename_check.py proves the result independently. Exit 0 done, 1 refused, 2 usage.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCOPE = REPO / ".codex_state" / "rules" / "rename_scope.txt"
OLD = "puppet_infrastructure"
NAME = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
SETS = "spec/behaviour/checks/*.yml"


def forms(name: str) -> list[str]:
    return [name, name[:1].upper() + name[1:], name.replace("_", "-")]


def scope(path: Path = SCOPE) -> dict:
    out = {"exclude": [], "protect": [], "keep_yaml": [], "also": []}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split(" -- ", 1)[0].rstrip()
        if not line or line.startswith("#"):
            continue
        kind, _, rest = line.partition(" ")
        rest = rest.strip()
        if kind == "exclude":
            out["exclude"].append(rest)
        elif kind == "protect":
            out["protect"].append(re.compile(rest))
        elif kind == "keep-yaml":
            out["keep_yaml"].append(rest)
        elif kind == "also":
            p, old, new = (x.strip() for x in rest.split("|"))
            out["also"].append((p, old, new))
        else:
            raise SystemExit(f"rename_scope.txt: unknown entry {kind!r}")
    return out


def excluded(path: str, sc: dict) -> bool:
    return any(fnmatch.fnmatchcase(path, g.replace("**", "*")) for g in sc["exclude"])


def rename_text(text: str, pairs: list[tuple[str, str]], protect: list[re.Pattern]) -> str:
    """Each old form replaced outside the protected spans."""
    spans = sorted((m.start(), m.end()) for p in protect for m in p.finditer(text))
    out, pos = [], 0
    for a, b in spans + [(len(text), len(text))]:
        if a < pos:
            continue
        chunk = text[pos:a]
        for old, new in pairs:
            chunk = chunk.replace(old, new)
        out += [chunk, text[a:b]]
        pos = b
    return "".join(out)


def yaml_kept_lines(lines: list[str], keys: list[str]) -> set[int]:
    """Indexes of the lines inside a kept key's block (the key line, its list items and deeper lines)."""
    kept, inside, indent = set(), False, 0
    for i, line in enumerate(lines):
        stripped = line.lstrip(" ")
        ind = len(line) - len(stripped)
        if inside:
            if not stripped.strip() or ind > indent or (ind == indent and stripped.startswith("- ")):
                kept.add(i)
                continue
            inside = False
        m = re.match(r"(?:- )?([A-Za-z_]+):", stripped)
        if m and m.group(1) in keys:
            inside, indent = True, ind + (2 if stripped.startswith("- ") else 0)
            kept.add(i)
    return kept


def new_content(path: str, text: str, new: str, sc: dict) -> str:
    pairs = list(zip(forms(OLD), forms(new)))
    lines = text.split("\n")
    kept = yaml_kept_lines(lines, sc["keep_yaml"]) if fnmatch.fnmatchcase(path, SETS) else set()
    out = [line if i in kept else rename_text(line, pairs, sc["protect"]) for i, line in enumerate(lines)]
    for p, old, newline in sc["also"]:
        if p == path:
            out = [l.replace(old, newline) if l.strip() == old else l for l in out]
    return "\n".join(out)


def tracked() -> list[str]:
    return subprocess.run(["git", "-C", str(REPO), "ls-files"], capture_output=True, text=True,
                          check=True).stdout.splitlines()


def changes(new: str) -> list[tuple[str, str, str]]:
    sc = scope()
    out = []
    for path in tracked():
        if excluded(path, sc):
            continue
        try:
            text = (REPO / path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        after = new_content(path, text, new, sc)
        if after != text:
            out.append((path, text, after))
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("plan", "apply") or not NAME.fullmatch(argv[1]) or argv[1] == OLD:
        print(__doc__)
        return 2
    new = argv[1]
    found = changes(new)
    for path, before, after in found:
        counts = {f: before.count(f) - after.count(f) for f in forms(OLD) if before.count(f) != after.count(f)}
        if argv[0] == "plan":
            print(f"{path} {counts}")
            continue
        (REPO / path).write_text(after, encoding="utf-8")
        for n, (a, b) in enumerate(zip(before.split("\n"), after.split("\n")), 1):
            if a != b:
                print(f"{path}:{n}: {a.strip()}  =>  {b.strip()}")
    print(f"{'would change' if argv[0] == 'plan' else 'changed'} {len(found)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
