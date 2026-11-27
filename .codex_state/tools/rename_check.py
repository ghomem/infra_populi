#!/usr/bin/env python3
"""The rename's proof (Phase 2 rename plan, mechanics 1: "the rename's equivalent of DIFF A"; HQ review of the behaviour
suite, ruling 8: over the whole tree). Independent of rename_module.py: it reads the same scope file but shares no
code with the tool that applied it.

  rename_check.py <ref> <new name>     compare the tree at <ref> (the `pre-rename` tag) with the working tree

PASS only if, over every tracked file:
  - the set of files is the same (a rename renames no file: none is named after the module);
  - an excluded file (history, sources) is byte-identical;
  - a check set (spec/behaviour/checks/*.yml), read as YAML, has the same structure; everything under a kept key
    (derived_from: the baseline's quotations) is identical and every other string is its old value with each form of
    the old name replaced;
  - every other file has the same lines, each equal to its old line with each form of the old name replaced outside
    the protected spans, or to the scope's declared `also` change;
  - no form of the old name is left outside the protected spans and kept keys.
Prints each problem; exit 0 PASS, 1 FAIL, 2 usage.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
OLD_FORMS = ("puppet_infrastructure", "Puppet_infrastructure", "puppet-infrastructure")
SETS = re.compile(r"spec/behaviour/checks/[^/]+\.yml")


def git(*args: str, text: bool = True):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=text, check=True).stdout


def read_scope(raw: str) -> dict:
    sc = {"exclude": [], "protect": [], "keep_yaml": set(), "also": {}}
    for line in raw.splitlines():
        body = line.split(" -- ", 1)[0].strip()
        if not body or body.startswith("#"):
            continue
        word, _, rest = body.partition(" ")
        rest = rest.strip()
        if word == "exclude":
            sc["exclude"].append(re.compile(re.escape(rest).replace(r"\*\*", ".*").replace(r"\*", "[^/]*") + r"\Z"))
        elif word == "protect":
            sc["protect"].append(re.compile(rest))
        elif word == "keep-yaml":
            sc["keep_yaml"].add(rest)
        elif word == "also":
            path, old, new = [x.strip() for x in rest.split("|")]
            sc["also"].setdefault(path, {})[old] = new
    return sc


def new_forms(new: str) -> tuple[str, str, str]:
    return (new, new[0].upper() + new[1:], new.replace("_", "-"))


def mapped(old_line: str, sc: dict, news: tuple[str, ...]) -> str:
    """The old line as the rename must leave it: forms replaced, protected spans untouched."""
    keep = [False] * len(old_line)
    for p in sc["protect"]:
        for m in p.finditer(old_line):
            keep[m.start():m.end()] = [True] * (m.end() - m.start())
    out, i = [], 0
    while i < len(old_line):
        for o, n in zip(OLD_FORMS, news):
            if old_line.startswith(o, i) and not any(keep[i:i + len(o)]):
                out.append(n)
                i += len(o)
                break
        else:
            out.append(old_line[i])
            i += 1
    return "".join(out)


def leftovers(text: str, sc: dict) -> int:
    clean = text
    for p in sc["protect"]:
        clean = p.sub("", clean)
    return sum(clean.count(o) for o in OLD_FORMS)


def check_set(path: str, old: str, new: str, sc: dict, news) -> list[str]:
    a, b = yaml.safe_load(old), yaml.safe_load(new)
    problems = []

    def walk(x, y, where, kept):
        if kept:
            if x != y:
                problems.append(f"{path}: {where} is kept as written ({'/'.join(sorted(sc['keep_yaml']))}) but changed")
            return
        if isinstance(x, dict) and isinstance(y, dict) and list(x) == list(y):
            for k in x:
                walk(x[k], y[k], f"{where}.{k}", k in sc["keep_yaml"])
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, f"{where}[{i}]", False)
        elif isinstance(x, str) and isinstance(y, str):
            if y != mapped(x, sc, news) or leftovers(y, sc):
                problems.append(f"{path}: {where} is not its old value renamed")
        elif x != y:
            problems.append(f"{path}: {where} changed beyond the rename")
    walk(a, b, "", False)
    return problems


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    ref, new = argv
    news = new_forms(new)
    sc = read_scope(git("show", f"{ref}:.codex_state/rules/rename_scope.txt"))  # excluded: the same at both
    before = set(git("ls-tree", "-r", "--name-only", ref).splitlines())
    after = set(git("ls-files").splitlines())
    problems = [f"file added: {p}" for p in sorted(after - before)] + [f"file removed: {p}" for p in sorted(before - after)]
    checked = 0
    for path in sorted(before & after):
        old = git("show", f"{ref}:{path}", text=False)
        now = (REPO / path).read_bytes()
        if any(e.match(path) for e in sc["exclude"]):
            if old != now:
                problems.append(f"{path}: excluded (kept as written) but changed")
            continue
        try:
            old_t, now_t = old.decode("utf-8"), now.decode("utf-8")
        except UnicodeDecodeError:
            if old != now:
                problems.append(f"{path}: binary file changed")
            continue
        checked += 1
        ol, nl = old_t.split("\n"), now_t.split("\n")
        if len(ol) != len(nl):
            problems.append(f"{path}: {len(ol)} lines before, {len(nl)} after")
            continue
        if SETS.fullmatch(path):
            # each line kept or renamed (a kept derived_from line stays as written), comments renamed; the YAML
            # check below decides which values had to be renamed
            for n, (a, b) in enumerate(zip(ol, nl), 1):
                if b not in (a, mapped(a, sc, news)) or (a.lstrip().startswith("#") and b != mapped(a, sc, news)):
                    problems.append(f"{path}:{n}: not the rename of its old line")
            problems += check_set(path, old_t, now_t, sc, news)
            continue
        also = sc["also"].get(path, {})
        for n, (a, b) in enumerate(zip(ol, nl), 1):
            want = a.replace(a.strip(), also[a.strip()]) if a.strip() in also else mapped(a, sc, news)
            if b != want:
                problems.append(f"{path}:{n}: not the rename of its old line")
        if leftovers(now_t, sc):
            problems.append(f"{path}: {leftovers(now_t, sc)} form(s) of the old name left outside protected spans")
    for p in problems:
        print(p)
    print(f"RENAME_CHECK {'PASS' if not problems else 'FAIL'}: {checked} files checked against {ref}, "
          f"{len(problems)} problem(s)")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
