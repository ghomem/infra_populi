#!/usr/bin/env python3
"""Consumer conversion for the module rename, applied at the cutover (Phase 2 rename plan, mechanics 4; HQ rulings on
round 9 "E. Phase 2 rename": prepared and tested on synthetic fixtures, applied at cutover, with a check that fails on
any leftover old name; HQ review of the behaviour suite, ruling 8). Never run here against a real consumer: the
fleet's repositories and the production master are converted by their owners at the cutover.

  convert_consumers.py convert <dir> [--to <name>] [--dry-run]
      every text file under <dir> (node definitions of puppet-nodes or meaningful_puppet, Hiera data with its
      automatic parameter keys and values, Hashman's generated user declarations, the operator's params directory):
      each form of the old name becomes the new one's (`puppet_infrastructure::` -> `infra_populi::`,
      `Puppet_infrastructure::` -> `Infra_populi::`, `puppet-infrastructure` -> `infra-populi`, e.g. a localdir path);
      then every file or directory named with the old name is renamed (params files `puppet_infrastructure::x.json`).
      Prints each changed line and each renamed path.
  convert_consumers.py check <dir>
      exit 1 and list every leftover of the old name (content and names); exit 0 when none is left.

<name> defaults to metadata.json's (module_name.py). Symlinks are not followed; binary files are left alone (and
reported by `check` if their bytes name the module). Exit 0 done/clean, 1 leftovers, 2 usage.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import module_name  # noqa: E402

OLD = module_name.OLD


def pairs(new: str) -> list[tuple[str, str]]:
    return list(zip(module_name.forms(OLD), module_name.forms(new)))


def walk(root: Path):
    """Every path under root, deepest first (so a renamed directory's contents are renamed before it)."""
    for d, dirs, files in os.walk(root, topdown=False, followlinks=False):
        for f in files:
            yield Path(d) / f
        for s in dirs:
            yield Path(d) / s


def renamed(path: Path, new: str) -> Path:
    name = path.name
    for a, b in pairs(new):
        name = name.replace(a, b)
    return path.with_name(name)


def convert(root: Path, new: str, dry: bool) -> int:
    for path in walk(root):  # every collision refused before anything is written
        target = renamed(path, new)
        if target != path and target.exists():
            raise SystemExit(f"REFUSED: {target.relative_to(root)} exists; nothing converted")
    changed = 0
    for path in walk(root):
        if path.is_file() and not path.is_symlink():
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            after = text
            for a, b in pairs(new):
                after = after.replace(a, b)
            if after != text:
                changed += 1
                for n, (x, y) in enumerate(zip(text.split("\n"), after.split("\n")), 1):
                    if x != y:
                        print(f"{path.relative_to(root)}:{n}: {x.strip()}  =>  {y.strip()}")
                if not dry:
                    path.write_text(after, encoding="utf-8")
    for path in walk(root):
        target = renamed(path, new)
        if target != path:
            print(f"rename {path.relative_to(root)}  =>  {target.relative_to(root)}")
            changed += 1
            if not dry:
                path.rename(target)
    return changed


def leftovers(root: Path) -> list[str]:
    out = []
    forms = [f.encode() for f in module_name.forms(OLD)]
    for path in walk(root):
        rel = path.relative_to(root)
        if any(f in path.name for f in module_name.forms(OLD)):
            out.append(f"{rel}: named with the old name")
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            for n, line in enumerate(data.split(b"\n"), 1):
                if any(f in line for f in forms):
                    out.append(f"{rel}:{n}: names the old module")
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("convert", "check") or not Path(argv[1]).is_dir():
        print(__doc__)
        return 2
    root = Path(argv[1])
    if argv[0] == "check":
        found = leftovers(root)
        for line in found:
            print(line)
        print(f"CONVERSION CHECK {'FAIL' if found else 'PASS'}: {len(found)} leftover(s) of {OLD} under {root}")
        return 1 if found else 0
    new = argv[argv.index("--to") + 1] if "--to" in argv else module_name.MODULE
    if new == OLD:
        print(f"REFUSED: the target name is the old one ({OLD}); give --to <new name> before the rename")
        return 2
    n = convert(root, new, "--dry-run" in argv)
    print(f"{'would change' if '--dry-run' in argv else 'changed'} {n} file(s) or name(s) under {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
