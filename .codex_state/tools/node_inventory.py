#!/usr/bin/env python3
"""Path inventory of the CLEAN node baseline (HQ 2026-11-11 ruling 4), for pregate's dynamic prerequisite probe.

  node_inventory.py [--node KIND] --refresh   revert the node to its baseline snapshot, then record every directory, symlink and
                                  file on its root filesystem (find -xdev) into the untracked cache
  node_inventory.py [--node KIND] --show      cache path, age and counts

The probe answers "does this path exist on the freshly reverted node?" from this cache instead of reverting the node
for every pregate run. The cache is keyed by the node snapshot name; refresh it whenever the snapshot changes.
P8_NODE_INVENTORY overrides the cache path (tests).
"""

from __future__ import annotations

import datetime as dt
import gzip
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
import nodes  # noqa: E402  (the lab node inventory: one cache per node, keyed by its baseline snapshot)
FIND = ("sudo -n find / -xdev \\( -path /proc -o -path /sys -o -path /run -o -path /tmp -o -path /var/tmp "
        "-o -path '/home/*/.cache' \\) -prune -o -printf '%y %p\\n'")


def node(kind: str | None = None, cls: str | None = None) -> dict:
    return nodes.select(nodes.load(), kind, cls)


def cache_path(kind: str | None = None, cls: str | None = None) -> Path:
    snapshot = node(kind, cls)["baseline_snapshot"]
    return Path(os.environ.get("P8_NODE_INVENTORY") or
                REPO / ".codex_state" / "logs" / "node_baseline" / f"{snapshot}.paths.gz")


def load(path: Path | None = None, kind: str | None = None, cls: str | None = None) -> dict[str, str] | None:
    """{path: type} with type d (dir), l (symlink), f (file) ...; None when no inventory exists."""
    path = path or cache_path(kind, cls)
    if not path.is_file():
        return None
    out: dict[str, str] = {}
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or len(line) < 3:
                continue
            kind, _, p = line.rstrip("\n").partition(" ")
            out[p] = kind
    return out


def refresh(kind: str | None = None) -> int:
    n = node(kind)
    revert = subprocess.run([str(TOOLS / "revert_node.sh"), "--node", n["kind"]], capture_output=True, text=True)
    if revert.returncode != 0:
        print(f"ERROR: revert failed: {revert.stderr.strip()[-300:]}", file=sys.stderr)
        return 2
    env = dict(os.environ, PATH=f"{TOOLS / 'sshmux'}:{os.environ['PATH']}")
    proc = subprocess.run(["timeout", "300", "ssh", n["alias"], FIND], capture_output=True, text=True, env=env)
    if proc.returncode not in (0, 1) or not proc.stdout:
        print(f"ERROR: find on the node failed (rc {proc.returncode}): {proc.stderr.strip()[-300:]}", file=sys.stderr)
        return 2
    path = cache_path(n["kind"])
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write(f"# {n['baseline_snapshot']} clean-node inventory of {n['kind']} {stamp} (find -xdev, after revert_node.sh)\n")
        f.write(proc.stdout)
    inv = load(path)
    print(f"INVENTORY {n['kind']} {n['baseline_snapshot']}: {len(inv)} paths ({sum(1 for k in inv.values() if k == 'd')} dirs, "
          f"{sum(1 for k in inv.values() if k == 'l')} symlinks) -> {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")
    return 0


def main(argv: list[str]) -> int:
    kind = argv[argv.index("--node") + 1] if "--node" in argv else None
    rest = [a for i, a in enumerate(argv) if a != "--node" and (i == 0 or argv[i - 1] != "--node")]
    if rest == ["--refresh"]:
        return refresh(kind)
    if rest == ["--show"]:
        inv = load(kind=kind)
        print(f"{cache_path(kind)}: " + ("missing — run --refresh" if inv is None else f"{len(inv)} paths"))
        return 0 if inv is not None else 1
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
