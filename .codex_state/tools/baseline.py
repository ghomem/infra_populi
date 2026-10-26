#!/usr/bin/env python3
"""Declared upstream baseline: one reader for .codex_state/baseline.env.

  baseline.py name                  -> release-0.9.10
  baseline.py commit                -> full upstream commit the baseline is pinned to
  baseline.py label                 -> "release-0.9.10 (cf477c6)" for headers and prompts
  baseline.py show <path>           -> file content at the baseline (exit 1 if absent)
  baseline.py paths <class>         -> manifest + templates/files the baseline class references
  baseline.py drift <class>         -> local manifest/templates/files vs baseline; exit 1 on drift

Never reads upstream HEAD or a branch name: the release-0.9.10 branch moved after the pin.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[2]
ENV_FILE = REPO / ".codex_state" / "baseline.env"

# template('puppet_infrastructure/x'), epp(...), file(...), puppet:///modules/puppet_infrastructure/x
REF_RE = re.compile(
    r"""(?P<fn>template|epp|file)\(\s*['"]puppet_infrastructure/(?P<fpath>[^'"]+)['"]"""
    r"""|puppet:///modules/puppet_infrastructure/(?P<spath>[^'"\s,)\]]+)"""
)


@dataclass(frozen=True)
class Baseline:
    name: str
    commit: str
    upstream: Path


def load(env_file: Path = ENV_FILE) -> Baseline:
    values = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    missing = {"BASELINE_NAME", "BASELINE_COMMIT", "UPSTREAM_REPO"} - values.keys()
    if missing:
        raise SystemExit(f"ERROR: {env_file} lacks {', '.join(sorted(missing))}")
    if not re.fullmatch(r"[0-9a-f]{40}", values["BASELINE_COMMIT"]):
        raise SystemExit("ERROR: BASELINE_COMMIT must be a full 40-hex commit id")
    return Baseline(values["BASELINE_NAME"], values["BASELINE_COMMIT"],
                    Path(os.path.expanduser(values["UPSTREAM_REPO"])))


def git_show(upstream: Path, ref: str, path: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(upstream), "show", f"{ref}:{path}"],
                          capture_output=True, stdin=subprocess.DEVNULL)
    return proc.stdout if proc.returncode == 0 else None


def git_tree_paths(upstream: Path, ref: str, prefix: str) -> list[str]:
    proc = subprocess.run(["git", "-C", str(upstream), "ls-tree", "-r", "--name-only", ref, "--", prefix],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
    return [p for p in proc.stdout.splitlines() if p]


def referenced_paths(manifest: str) -> list[tuple[str, bool]]:
    """(repo path, is_prefix) for every template/file the manifest references.

    An interpolated reference (`${x}`) becomes a prefix: everything under the literal part counts.
    """
    out = []
    for m in REF_RE.finditer(manifest):
        if m.group("fpath") is not None:
            root = "files/" if m.group("fn") == "file" else "templates/"
            rel = m.group("fpath")
        else:
            root, rel = "files/", m.group("spath")
        if "$" in rel:
            out.append((root + rel.split("$", 1)[0], True))
        else:
            out.append((root + rel, False))
    return sorted(set(out))


def expand(upstream: Path, ref: str, refs: list[tuple[str, bool]]) -> list[str]:
    """Resolve references to concrete paths present at ref (a directory source counts recursively)."""
    paths = set()
    for path, is_prefix in refs:
        under = [p for p in git_tree_paths(upstream, ref, path.rsplit("/", 1)[0] if is_prefix else path)
                 if p == path or p.startswith(path if is_prefix else path.rstrip("/") + "/")]
        paths.update(under or [path])
    return sorted(paths)


def class_paths(cls: str, ref: str, upstream: Path) -> list[str]:
    manifest_path = f"manifests/{cls}.pp"
    manifest = git_show(upstream, ref, manifest_path)
    if manifest is None:
        return [manifest_path]
    return [manifest_path] + expand(upstream, ref, referenced_paths(manifest.decode("utf-8", "replace")))


def identical_between(cls: str, ref_a: str, ref_b: str, upstream: Path) -> tuple[bool, list[str]]:
    """Byte-identity of a class's manifest+templates+files between two upstream refs."""
    paths = sorted(set(class_paths(cls, ref_a, upstream)) | set(class_paths(cls, ref_b, upstream)))
    differing = [p for p in paths if git_show(upstream, ref_a, p) != git_show(upstream, ref_b, p)]
    return (not differing, differing)


def local_drift(cls: str, base: Baseline, repo: Path = REPO) -> list[str]:
    """Paths of the class whose local content differs from the baseline (missing counts as drift)."""
    drift = []
    for path in class_paths(cls, base.commit, base.upstream):
        local = repo / path
        if git_show(base.upstream, base.commit, path) != (local.read_bytes() if local.is_file() else None):
            drift.append(path)
    return drift


def main(argv: list[str]) -> int:
    base = load()
    if argv == ["name"]:
        print(base.name)
    elif argv == ["commit"]:
        print(base.commit)
    elif argv == ["label"]:
        print(f"{base.name} ({base.commit[:7]})")
    elif len(argv) == 2 and argv[0] == "show":
        data = git_show(base.upstream, base.commit, argv[1])
        if data is None:
            print(f"ERROR: {argv[1]} not present at {base.name}", file=sys.stderr)
            return 1
        sys.stdout.buffer.write(data)
    elif len(argv) == 2 and argv[0] == "paths":
        print("\n".join(class_paths(argv[1], base.commit, base.upstream)))
    elif len(argv) == 2 and argv[0] == "drift":
        drift = local_drift(argv[1], base)
        for path in drift:
            print(f"DRIFT {path}")
        if not drift:
            print(f"OK {argv[1]} identical to {base.name}")
        return 1 if drift else 0
    else:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
