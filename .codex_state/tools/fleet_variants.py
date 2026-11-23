#!/usr/bin/env python3
"""Which class parameters production sets (HQ 2026-11-23 ruling 1c): names and counts only, never a value.

  fleet_variants.py [--write]     print (or write .codex_state/diagnosis/fleet_variant_usage.md) the table
  fleet_variants.py count <class> <param>
                                  the production node statements that set <param> on <class>, or `undeterminable`

A parameter counts for a production node statement when the node file sets it on the class, or a `meaningful_puppet`
class the node declares sets it, or a puppet_infrastructure composite the node (or such a class) declares forwards a
parameter the node sets to it (`component_param => $composite_param`). Only parameter NAMES are read; values are
never recorded. Production = every group of the fleet except deleted/ and tests/; the passwd/ layer is never read
(off-limits), so a class whose production declarations live there (the diagnosis's list) is `undeterminable`, not 0.
Sources: P8_FLEET_DIR (default ~/work/puppet-nodes), P8_COMPANY_DIR (default ~/work/meaningful_puppet), the
repository's own manifests (composites).
"""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / ".codex_state" / "diagnosis" / "fleet_variant_usage.md"
SKIP_GROUPS = {"deleted", "tests", "passwd"}
# Declared mostly in the passwd/ layer, which the engine never reads (diagnosis 2026-10-26, fleet_class_usage.md).
PASSWD_LAYER = {"user_base", "user", "user_sudoer", "users_sudoers", "user_lock", "user_samba", "user_sysmon",
                "sftp_only", "backup", "backup_rsnapshot", "backup_rsnapshot_pre", "sync", "letsencrypt_certificate"}
DECL = re.compile(r"(?:\bclass\s*\{\s*['\"](?:::)?(puppet_infrastructure|meaningful_puppet)::(\w+)['\"]\s*:"
                  r"|(?<![\w:])(?:::)?(puppet_infrastructure)::(\w+)\s*\{\s*['\"\$])")
INCLUDE = re.compile(r"\b(?:include|require|contain)\s+['\"]?(?:::)?(puppet_infrastructure|meaningful_puppet)::(\w+)")
PARAM = re.compile(r"(?:^|[,;{\s])(\w+)\s*=>")


def fleet_dir() -> Path:
    return Path(os.environ.get("P8_FLEET_DIR") or Path.home() / "work" / "puppet-nodes")


def company_dir() -> Path:
    return Path(os.environ.get("P8_COMPANY_DIR") or Path.home() / "work" / "meaningful_puppet")


def strip_comments(text: str) -> str:
    out = []
    for line in text.splitlines():
        cut, quote = len(line), ""
        for i, ch in enumerate(line):
            if quote:
                quote = "" if ch == quote and line[i - 1] != "\\" else quote
            elif ch in "'\"":
                quote = ch
            elif ch == "#":
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


def body_at(text: str, start: int) -> str:
    """The text inside the braces that open at or after `start`, matched outside strings."""
    i = text.index("{", start)
    depth, quote, j = 0, "", i
    while j < len(text):
        ch = text[j]
        if quote:
            if ch == quote and text[j - 1] != "\\":
                quote = ""
        elif ch in "'\"":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
        j += 1
    return text[i + 1:]


def top_level_params(body: str) -> set[str]:
    """Parameter names at the body's top level (after each `title:`), skipping nested hashes, arrays and strings."""
    flat, depth, quote = [], 0, ""
    for i, ch in enumerate(body):
        if quote:
            if ch == quote and body[i - 1] != "\\":
                quote = ""
            continue
        if ch in "'\"":
            quote = ch
            flat.append(" ")
            continue
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        flat.append(ch if depth == 0 else " ")
    return set(PARAM.findall("".join(flat)))


def declarations(text: str) -> tuple[dict[tuple[str, str], set[str]], set[tuple[str, str]]]:
    """({(namespace, class): parameter names set}, {(namespace, class) declared}) in a manifest."""
    text = strip_comments(text)
    params: dict[tuple[str, str], set[str]] = defaultdict(set)
    declared: set[tuple[str, str]] = set()
    for m in DECL.finditer(text):
        key = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        declared.add(key)
        params[key] |= top_level_params(body_at(text, m.start()))
    for m in INCLUDE.finditer(text):
        declared.add((m.group(1), m.group(2)))
    return params, declared


def forwards() -> dict[str, dict[str, set[tuple[str, str]]]]:
    """composite -> {its parameter: {(component, component parameter)}} from the repository's manifests."""
    out: dict[str, dict[str, set[tuple[str, str]]]] = defaultdict(lambda: defaultdict(set))
    for path in sorted((REPO / "manifests").glob("*.pp")):
        text = strip_comments(path.read_text(errors="replace"))
        for m in DECL.finditer(text):
            if (m.group(1) or m.group(3)) != "puppet_infrastructure":
                continue
            comp = m.group(2) or m.group(4)
            body = body_at(text, m.start())
            for pm in re.finditer(r"(\w+)\s*=>\s*\$(\w+)\b", body):
                out[path.stem][pm.group(2)].add((comp, pm.group(1)))
    return out


def node_files() -> list[tuple[str, Path]]:
    root = fleet_dir()
    found = []
    for path in sorted(root.rglob("*.pp")):
        rel = path.relative_to(root).parts
        if ".git" in rel or rel[0] in SKIP_GROUPS or len(rel) < 2:
            continue  # deleted/, tests/, the passwd/ layer, and top-level variable files (common.pp)
        found.append((rel[0], path))
    return found


def usage() -> dict[str, dict[str, set[str]]]:
    """class -> {parameter: {node file (relative)}} over production node statements."""
    company = {}
    for path in sorted((company_dir() / "manifests").glob("*.pp")):
        company[path.stem] = declarations(path.read_text(errors="replace"))
    fwd = forwards()
    used: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    def add(cls: str, param: str, node: str, seen: frozenset = frozenset()) -> None:
        used[cls][param].add(node)
        for comp, cparam in fwd.get(cls, {}).get(param, ()):
            if (comp, cparam) not in seen:
                add(comp, cparam, node, seen | {(cls, param)})

    for group, path in node_files():
        node = str(path.relative_to(fleet_dir()))
        params, declared = declarations(path.read_text(errors="replace"))
        layers = [params] + [company[c][0] for ns, c in declared if ns == "meaningful_puppet" and c in company]
        for layer in layers:
            for (ns, cls), names in layer.items():
                if ns == "puppet_infrastructure":
                    for name in names:
                        add(cls, name, node)
    return used


def count(cls: str, param: str) -> str:
    if cls in PASSWD_LAYER:
        return "undeterminable"
    return str(len(usage().get(cls, {}).get(param, set())))


def render() -> str:
    used = usage()
    lines = [
        "# Fleet variant usage — which class parameters production sets (names and counts only)",
        "",
        "Generated by `.codex_state/tools/fleet_variants.py --write` (HQ 2026-11-23 ruling 1c). A derived file: regenerate it,",
        "never edit it. Counts are production node statements (every fleet group but deleted/ and tests/; the desktops/",
        "regex statement counts 1 and stands for about 20 laptops) that set the parameter on the class directly, through a",
        "meaningful_puppet class they declare, or through a composite that forwards it. No value is read into this file.",
        f"The passwd/ layer is never read: for {', '.join(sorted(PASSWD_LAYER))} the count is undeterminable.",
        "",
        "| class | parameter | production node statements |",
        "|---|---|---:|",
    ]
    for cls in sorted(used):
        for param in sorted(used[cls]):
            n = "undeterminable" if cls in PASSWD_LAYER else str(len(used[cls][param]))
            lines.append(f"| {cls} | {param} | {n} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    if argv[:1] == ["count"] and len(argv) == 3:
        print(count(argv[1], argv[2]))
        return 0
    if argv in ([], ["--write"]):
        text = render()
        if argv:
            OUT.write_text(text)
            print(f"wrote {OUT.relative_to(REPO)}")
        else:
            print(text, end="")
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
