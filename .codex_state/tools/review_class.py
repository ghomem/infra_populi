#!/usr/bin/env python3
"""Reviewer v2 evidence tool (step 1.4). Independent: it reads git, the files, the pinned baseline, the
master's module inventory and its own harness run. It never reads logs/runs/transcripts and never
prints commit authors or commit bodies (rule 9: the reviewer does not learn who authored a change).

  review_class.py check <class> [--no-harness] [--fresh]
      Mechanical checks + the two diffs. Writes a draft to .codex_state/logs/reviews/ (untracked).
      --fresh: the post-migration mode. Valid only while the migrate commit is HEAD or followed by nothing but the
      record/regenerate commits record_green makes (at most 3); anything else is a USAGE ERROR (HQ 2026-11-16):
      exit 2 before any check or harness run, no draft, and `verdict` refuses until a new `check` runs.
  review_class.py verdict <class> --faithful ok|fail --evidence TEXT [--evidence TEXT ...]
                                  [--justify-run1 TEXT] [--fixture-scope TEXT]
      Combines the latest draft with the reviewer's faithfulness judgement and writes the persisted
      verdict .codex_state/reviews/<class>/<UTC>.json (tracked, append-only). Prints the report.
      --fixture-scope is required when the class went GREEN on a mock-apply node fixture (HQ batch-7 ruling 2).
  check <class> --node KIND / verdict <class> --node KIND ... (HQ batch-8 ruling 6: a verdict per node, the RedHat
      branches on rhel9): the same review on another lab node of nodes.yml. Refused when the plan pins the class to a
      different node. The harness, the fixtures check (per-node params first) and the node identities follow KIND
      (P8_NODE); the draft records the node and the verdict must use a draft of the same node. The verdict goes to
      .codex_state/reviews/<class>/nodes/<KIND>/<UTC>.json, beside (never replacing) the class's own verdicts.

Verdict PASS = every mechanical check ok AND faithful ok. Checks: git, scope, provenance, records,
header_modules, comments_preserved, syntax, fixtures, idempotent.
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(TOOLS.parent))
import baseline  # noqa: E402
import gen_migration_order as generator  # noqa: E402
import pregate  # noqa: E402

REPO = baseline.REPO
STATE = REPO / ".codex_state"
DRAFTS = STATE / "logs" / "reviews"
VERDICTS = STATE / "reviews"
HARNESS = TOOLS / "test_class.sh"
PARAMS_DIR = Path.home() / ".config" / "infra_populi" / "params"
STATE_FILES = {".codex_state/migrated_classes.txt", ".codex_state/migration_order.md",
               ".codex_state/migration_plan.md", ".codex_state/blocked.txt", ".codex_state/DESIGN_DECISIONS.md",
               ".codex_state/lab/Puppetfile"}
RECORD_SUBJECTS = ("P8: regenerate migration order", "P8: record")
FORGE_AUTHORS = {"puppetlabs", "puppet", "saz", "thias", "leinaddm", "citrin", "camptocamp", "voxpupuli"}
CHECKS = ("git", "scope", "provenance", "records", "header_modules", "comments_preserved", "syntax",
          "fixtures", "idempotent")

INVENTORY_REMOTE = r'''
for dir in /etc/puppetlabs/code/environments/production/modules/*/ /opt/puppetlabs/puppet/vendor_modules/*/; do
  m="$(basename "$dir")"; [ "$m" = puppet_infrastructure ] && continue
  case "$dir" in /opt/*) kind=vendored ;; *) kind=env ;; esac
  meta="$(/opt/puppetlabs/puppet/bin/ruby -rjson -e 'j=JSON.parse(File.read(ARGV[0])); print j["name"], " ", j["version"]' "$dir/metadata.json" 2>/dev/null)"
  echo "MODULE $m $kind $meta"
  for t in "$dir"lib/puppet/type/*.rb; do [ -f "$t" ] && echo "TYPE $m $(basename "$t" .rb)"; done
  (cd "$dir" && find manifests -name '*.pp' 2>/dev/null) | while read -r p; do
    p="${p#manifests/}"; p="${p%.pp}"
    if [ "$p" = init ]; then echo "CLASS $m $m"; else echo "CLASS $m $m::${p//\//::}"; fi
  done
done
'''


def git(*args: str, check: bool = True) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                          check=check, stdin=subprocess.DEVNULL).stdout


def show_bytes(ref: str, path: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def as_text(data: bytes | None) -> str | None:
    """The file as text, or None if it is binary (not UTF-8): class trees may hold images (hashman_web, batch 5)."""
    try:
        return None if data is None else data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def show(ref: str, path: str) -> str | None:
    return as_text(show_bytes(ref, path))


def is_binary(*blobs: bytes | None) -> bool:
    return any(b is not None and as_text(b) is None for b in blobs)


def change(a: bytes | None, b: bytes | None, path: str, label_a: str, label_b: str) -> str:
    """A unified diff for text, one line for a binary file (compared byte for byte)."""
    if is_binary(a, b):
        return f"Binary file {path} differs ({label_a} -> {label_b}; {len(a or b'')} -> {len(b or b'')} bytes)\n"
    return unified(as_text(a), as_text(b), path, label_a, label_b)


def result(status: str, detail: str | list) -> dict:
    return {"status": status, "detail": detail}


# ----------------------------------------------------------------------------- inventory

def master_inventory() -> dict:
    proc = subprocess.run(["timeout", "60", "ssh", "-T", "puppet8master", "bash -s"], input=INVENTORY_REMOTE,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"master inventory failed: {proc.stderr.strip()}")
    return parse_inventory(proc.stdout)


def parse_inventory(text: str) -> dict:
    inv = {"modules": {}, "types": {}, "classes": {}}
    for line in text.splitlines():
        parts = line.split()
        if parts[:1] == ["MODULE"] and len(parts) >= 3:
            forge = parts[3] if len(parts) > 3 else parts[1]
            inv["modules"][parts[1]] = {"kind": parts[2], "forge": forge,
                                        "version": parts[4] if len(parts) > 4 else None}
        elif parts[:1] == ["TYPE"] and len(parts) == 3:
            inv["types"][parts[2]] = parts[1]
        elif parts[:1] == ["CLASS"] and len(parts) == 3:
            inv["classes"][parts[2]] = parts[1]
    return inv


# ----------------------------------------------------------------------------- pieces

def migrate_commits(cls: str) -> list[tuple[str, str]]:
    """Every `P8: migrate puppet_infrastructure::<cls>` commit, newest first."""
    pattern = re.compile(rf"^P8: migrate puppet_infrastructure::{re.escape(cls)}$")
    found = []
    for line in git("log", "--format=%H%x09%s").splitlines():
        commit, _, subject = line.partition("\t")
        if pattern.match(subject):
            found.append((commit, subject))
    return found


def migrate_commit(cls: str) -> tuple[str, str] | None:
    found = migrate_commits(cls)
    return found[0] if found else None


def provenance_problems(migrate_diff: list[str], pre_drift: list[str], remigration: bool) -> tuple[list[str], str]:
    """A first migration must start from baseline content. A RE-migration (an earlier migrate commit exists)
    starts from the previous migration by definition: its pre-existing drift is what it replaces, and DIFF A
    (final vs baseline) carries the whole claim."""
    prov = []
    if not migrate_diff:
        prov.append("the migrate commit changed no class file (manifest/templates/files)")
    if pre_drift and not remigration:
        prov.append(f"pre-migrate content differed from the baseline (drift predates the migration): {pre_drift}")
    if prov:
        return prov, ""
    if remigration:
        return [], ("re-migration: the newest migrate commit replaced earlier migrated content"
                    + (f" that differed from the baseline in {pre_drift}" if pre_drift else "")
                    + "; DIFF A is judged in full")
    return [], "migration started from baseline content; the migrate commit changed class files"


def class_paths(cls: str, base: baseline.Baseline) -> list[str]:
    paths = set(baseline.class_paths(cls, base.commit, base.upstream))
    if (REPO / f"manifests/{cls}.pp").is_file():
        paths.update(pregate.local_class_files(cls))
    return sorted(paths)


def test_asset_fixtures(path: Path | None = None) -> set[str]:
    """Node fixtures that are test assets, not stand-ins (HQ 2026-11-18 ruling 9): a GREEN with one is no mock-apply."""
    path = path or STATE / "rules" / "test_asset_fixtures.txt"
    if not path.is_file():
        return set()
    return {l.split()[0] for l in path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}


def local_change_entry(cls: str, path: Path | None = None) -> str | None:
    """The class's rows in rules/local_changes.md (policy B purpose fixes), joined; None when it has none."""
    path = path or STATE / "rules" / "local_changes.md"
    if not path.is_file():
        return None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 3 and cells[1] == cls:
            rows.append(f"#{cells[0]}: {cells[2]}")
    return " | ".join(rows) or None


def local_change_numbers(cls: str, path: Path | None = None) -> list[int]:
    """The numbers of the class's rows in rules/local_changes.md, in file order (HQ batch-12 ruling 4)."""
    path = path or STATE / "rules" / "local_changes.md"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 3 and cells[1] == cls and cells[0].isdigit():
            out.append(int(cells[0]))
    return out


# HQ 2026-11-22 ruling 2: an upstream comment line a local change replaces or removes is accepted by comments_preserved
# only when the class's local-change row lists that exact line and its replacement:
#   comment `<old line>` -> `<new line>`      or      comment `<old line>` -> (removed)
COMMENT_CHANGE_RE = re.compile(r"comment `([^`]+)` -> (?:`([^`]+)`|\(removed\))")


def listed_comment_changes(cls: str, path: Path | None = None) -> list[tuple[str, str | None]]:
    """(old line, replacement line or None) for each comment change the class's local-change rows list (stripped)."""
    entry = local_change_entry(cls, path) or ""
    return [(m.group(1).strip(), None if m.group(2) is None else m.group(2).strip())
            for m in COMMENT_CHANGE_RE.finditer(entry)]


def unlisted_comment_removals(removed: list[tuple[str, str]], listed: list[tuple[str, str | None]],
                              final_lines: set[str]) -> tuple[list[str], list[str]]:
    """Split removed baseline comment lines [(path, line)] into (unlisted, accepted). A line is accepted only when a
    listed change names it exactly (stripped) and, for a replacement, the replacement line is in the final files."""
    unlisted, accepted = [], []
    for path, line in removed:
        old = line.strip()
        ok = any(o == old and (new is None or new in final_lines) for o, new in listed)
        (accepted if ok else unlisted).append(f"{path}: {old}")
    return unlisted, accepted


AFTER_RE = re.compile(r"PASS after \((?:checks/)?results/([a-z0-9_]+)/(\d{8}T\d{6}Z)-(author|reviewer)")


def local_change_after_problems(cls: str, class_files: list[str], path: Path | None = None,
                                results: Path | None = None, changed=None) -> list[str]:
    """HQ batch-15 ruling 2: a class carrying a local change gets its Phase 1 PASS only once the change's after-check has
    passed. Each of the class's rows must name its after result, that result must exist with every check the row names
    passed, and the class's latest result (author or reviewer) must have run on the current code (no class file changed
    between its runner commit and HEAD) with those checks passed too: a later change may not ride on an earlier after
    result. `changed(runner, files)` says whether any of the files differ from HEAD (git by default)."""
    path = path or STATE / "rules" / "local_changes.md"
    results = results or STATE / "checks" / "results"
    if changed is None:
        def changed(runner: str, files: list[str]) -> bool:
            return subprocess.run(["git", "-C", str(REPO), "diff", "--quiet", runner, "HEAD", "--", *files],
                                  capture_output=True).returncode != 0
    problems = []
    if not path.is_file():
        return problems
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not (line.startswith("|") and len(cells) >= 4 and cells[1] == cls and cells[0].isdigit()):
            continue
        n, check_col = cells[0], cells[3]
        m = AFTER_RE.search(check_col)
        if not m:
            problems.append(f"local change #{n} names no after result (`PASS after (results/...)`): its after-check "
                            "must pass before the Phase 1 PASS (HQ batch-15 ruling 2)")
            continue
        ids = [i.strip() for i in re.split(r"\s+and\s+|,\s*", check_col.split(":", 1)[0]) if i.strip()]
        res = results / m.group(1) / f"{m.group(2)}-{m.group(3)}.json"
        if not res.is_file():
            problems.append(f"local change #{n}: its after result results/{m.group(1)}/{res.name} does not exist")
            continue
        data = json.loads(res.read_text(encoding="utf-8"))
        passed = {r["id"]: r.get("passed") for r in data.get("applied", [])}
        for check_id in ids:
            if passed.get(check_id) is not True:
                problems.append(f"local change #{n}: check {check_id} did not pass in {res.name}")
        latest = max((p for p in res.parent.glob("*.json") if p.stem.endswith(("-author", "-reviewer"))),
                     key=lambda p: p.name[:16])
        last = json.loads(latest.read_text(encoding="utf-8"))
        runner = last.get("runner")
        if not runner:
            problems.append(f"local change #{n}: the latest result {latest.name} records no runner commit")
        elif changed(runner, class_files):
            problems.append(f"local change #{n}: the latest result {latest.name} ran on {runner}, and the class's files "
                            "changed since: run the after-check on the current code")
        else:
            now = {r["id"]: r.get("passed") for r in last.get("applied", [])}
            for check_id in ids:
                if now.get(check_id) is not True:
                    problems.append(f"local change #{n}: check {check_id} did not pass in the latest result "
                                    f"{latest.name} on the current code")
    return problems


def defect_entry(cls: str, path: Path | None = None) -> dict | None:
    """The class's entry in .codex_state/upstream_defects.md: {'status', 'change'} or None."""
    path = path or STATE / "upstream_defects.md"
    if not path.is_file():
        return None
    for block in path.read_text(encoding="utf-8").split("\n## ")[1:]:
        head, _, body = block.partition("\n")
        if cls not in [n.strip() for n in head.split("(", 1)[0].split(",")]:  # "## a, b (note)"
            continue
        fields: dict[str, str] = {}
        key = None
        for line in body.splitlines():
            # "- Key: value" or "- Key (provenance, may span lines): value"
            m = re.match(r"^- ([A-Z][\w -]*?)(?: \(|:)", line)
            if m:
                key = m.group(1).strip().lower()
                fields[key] = line
            elif key and line.startswith("  "):
                fields[key] += " " + line.strip()
        for key, text in fields.items():  # value = text after the first ": " that closes the key part
            text = text[2:]
            depth, cut = 0, None
            for i, ch in enumerate(text):
                depth += ch == "("
                depth -= ch == ")"
                if ch == ":" and depth == 0:
                    cut = i
                    break
            fields[key] = text[cut + 1:].strip() if cut is not None else ""
        return {"status": fields.get("status", ""), "change": fields.get("ruled change", "")}
    return None


def run2_justification_problems(cls: str, manifest: str) -> list[str]:
    """HQ 2026-11-10 ruling 1: every plan expected_run2_events entry is justified in the class header, and a header
    justification line exists only when the plan has entries."""
    row = generator.parse_plan().get(cls)
    expected = row.expected_run2_events if row else ()
    lines = [l for l in header_block(manifest) if re.match(r"^#\s*Expected run-2 events:", l)]
    if expected and not lines:
        return [f"plan expected_run2_events {list(expected)} but no `# Expected run-2 events: <refs> — <why>` header line"]
    missing = [ref for ref in expected if not any(ref in l for l in lines)]
    if missing:
        return [f"header justification does not name {missing}"]
    if lines and not expected:
        return ["header has an `Expected run-2 events` line but the plan lists none for the class"]
    if lines and not any(re.search(r"\S\s+[—-]+\s+\S", l.split(":", 1)[1]) for l in lines):
        return ["`Expected run-2 events` line gives no justification after the refs (`<refs> — <why>`)"]
    return []


def header_block(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        if re.match(r"\s*(class|define)\s", line):
            break
        lines.append(line)
    return lines


def is_comment(line: str) -> bool:
    return line.strip().startswith("#")


def diff_lines(a: str | None, b: str | None) -> tuple[list[str], list[str]]:
    """(added, removed) lines from a to b, ignoring pure whitespace lines."""
    added, removed = [], []
    for line in difflib.ndiff((a or "").splitlines(), (b or "").splitlines()):
        if line.startswith("+ ") and line[2:].strip():
            added.append(line[2:])
        elif line.startswith("- ") and line[2:].strip():
            removed.append(line[2:])
    return added, removed


def unified(a: str | None, b: str | None, path: str, label_a: str, label_b: str) -> str:
    return "".join(difflib.unified_diff((a or "").splitlines(True), (b or "").splitlines(True),
                                        f"{label_a}:{path}", f"{label_b}:{path}", n=2))


def module_claims(header: list[str], inv: dict) -> list[tuple[str, str | None]]:
    authors = FORGE_AUTHORS | {m["forge"].split("-")[0] for m in inv["modules"].values() if "-" in m["forge"]}
    claims = []
    for line in header:
        # a path segment (/opt/puppet-infrastructure/...) is not a module claim (linux_policies_user, HQ batch-7 ruling 1)
        for m in re.finditer(r"(?<![/\w.-])([a-z0-9]+)-([a-z][a-z0-9_]*)\b(?![/-])(?:\s+v?(\d+\.\d+\.\d+))?", line):
            if m.group(1) in authors:
                claims.append((f"{m.group(1)}-{m.group(2)}", m.group(3)))
    return claims


def modules_used(manifest: str, inv: dict) -> set[str]:
    """Env modules whose types or classes the manifest uses (vendored core modules excluded)."""
    used = set()
    for t in pregate.resource_types(manifest):
        mod = inv["types"].get(t) or inv["classes"].get(t)
        if mod and inv["modules"].get(mod, {}).get("kind") == "env":
            used.add(mod)
    for c in pregate.declared_classes(manifest):
        mod = inv["classes"].get(c)
        if mod and inv["modules"].get(mod, {}).get("kind") == "env":
            used.add(mod)
    return used


def node_kind(cls: str) -> str:
    import nodes  # noqa: PLC0415
    return nodes.select(nodes.load(), cls=cls)["kind"]


def node_identities(cls: str) -> tuple[set[str], set[str]]:
    """(real NIC names, human accounts) on the class's lab node (nodes.yml) — values a fixture must never use.
    A real NIC is a device-backed interface (/sys/class/net/<n>/device): veths, bridges, taps and dummies a class or a
    node fixture creates are not (openvpn_server, 2026-11-17: the check ran before the harness's revert and read the
    previous apply's p8test0 and br0 as real NICs)."""
    import nodes  # noqa: PLC0415
    alias = nodes.select(nodes.load(), cls=cls)["alias"]
    proc = subprocess.run(["timeout", "30", "ssh", alias,
                           "for n in /sys/class/net/*; do [ -e \"$n/device\" ] && echo \"${n##*/}\"; done; echo ---; "
                           "getent passwd | awk -F: '$3>=1000 && $3<65534 {print $1}'"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise RuntimeError(f"cannot read NICs/accounts from {alias}")
    nics, _, users = proc.stdout.partition("---")
    return ({n for n in nics.split() if n != "lo"},
            {u for u in users.split() if not u.startswith("p8test")})


def json_strings(value, path="") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, dict):
        return [x for k, v in value.items() for x in json_strings(v, f"{path}.{k}" if path else k)]
    if isinstance(value, list):
        return [x for i, v in enumerate(value) for x in json_strings(v, f"{path}[{i}]")]
    return []


def expanded_classes(cls: str) -> list[str]:
    seen, order = set(), []

    family = ""  # the reviewed class's node family; its bases are expanded for that node (ruling A2)

    def visit(name: str):
        nonlocal family
        if name in seen:
            return
        seen.add(name)
        data = json.loads(subprocess.run([sys.executable, str(STATE / "gen_migration_order.py"), "--classify", name,
                                          *(["--os-family", family] if family else [])],
                                         capture_output=True, text=True, check=True).stdout)
        family = family or data["required_base_os_family"]
        for b in data["required_base"]:
            visit(b)
        order.append((name, data))
    visit(cls)
    return order


# ----------------------------------------------------------------------------- checks

def fresh_usage_error(cls: str) -> str | None:
    found = migrate_commit(cls)
    if not found:
        return f"--fresh on {cls}: no `P8: migrate puppet_infrastructure::{cls}` commit"
    later = git("log", "--format=%s", f"{found[0]}..HEAD").splitlines()
    if len(later) > 3 or any(not s.startswith(RECORD_SUBJECTS) for s in later):
        return (f"--fresh on {cls}: its migrate commit {found[0][:12]} is not HEAD ({len(later)} later commits, "
                f"latest {later[:3]}); --fresh is only for the review right after a migration. "
                f"Re-run without --fresh to re-verify a recorded class")
    return None


def fresh_node_facts(text: str) -> dict:
    """From the harness output: did run 1 follow its own revert, and was the node still on that revert's boot with
    no agent run since (NODE_FRESH, record_green's rule)? Both are shown in every verdict (HQ 2026-11-16)."""
    return {"revert_first": bool(re.search(r"^RUN1_EVENTS: .*node reverted first", text, re.M)),
            "node_fresh": bool(re.search(r"^NODE_FRESH: yes", text, re.M))}


def run_checks(cls: str, harness: bool) -> dict:
    base = baseline.for_class(cls)
    out: dict = {"class": cls, "baseline": f"{base.name} ({base.commit[:7]})", "checks": {}, "diffs": {}}
    c = out["checks"]
    found = migrate_commit(cls)
    if not found:
        c["git"] = result("fail", f"no `P8: migrate puppet_infrastructure::{cls}` commit")
        return out
    commit, subject = found
    out["migrate_commit"], out["migrate_subject"] = commit[:12], subject
    remigration = len(migrate_commits(cls)) > 1
    out["remigration"] = remigration

    # git
    problems = []
    dirty = [l for l in git("status", "--porcelain").splitlines() if not l.startswith("?? .codex_state/reviews/")]
    if dirty:
        problems.append(f"worktree not clean: {dirty[:5]}")
    head, origin = git("rev-parse", "HEAD", "origin/main").split()
    if head != origin:
        problems.append("HEAD != origin/main")
    later = [s for s in git("log", "--format=%s", f"{commit}..HEAD").splitlines()]
    out["commits_since_migrate"] = len(later)
    c["git"] = result("fail" if problems else "ok", problems or f"migrate commit {commit[:12]}; {len(later)} commits since")

    paths = class_paths(cls, base)
    # scope
    touched = [p for p in git("show", "--name-only", "--format=", commit).splitlines() if p]
    allowed = set(paths) | STATE_FILES
    extra = [p for p in touched if p not in allowed and not p.startswith(f".codex_state/candidates/{cls}.")]
    blocked_delta = [l[1:] for l in git("show", "--format=", commit, "--", ".codex_state/blocked.txt").splitlines()
                     if l[:1] in "+-" and not l.startswith(("+++", "---")) and l[1:].strip() and not l[1:].startswith("#")]
    foreign = [l.split()[0] for l in blocked_delta if l.split()[0] != cls]
    issues = ([f"touches files outside the class and its records: {extra}"] if extra else []) + \
             ([f"blocked.txt delta names other classes: {sorted(set(foreign))}"] if foreign else [])
    c["scope"] = result("fail" if issues else "ok", issues or f"{len(touched)} files, all within scope")

    # provenance + diffs (two-diff method)
    parent = f"{commit}^"
    pre_drift, migrate_diff, final_diff = [], [], []
    added_all, removed_all, removed_comments, changed_manifest = [], [], [], False
    final_lines: set[str] = set()
    for path in paths:
        # byte comparisons: a binary class file (an image) is compared exactly, never through a lossy decode
        up = baseline.git_show(base.upstream, base.commit, path)
        pre, mig, now = show_bytes(parent, path), show_bytes(commit, path), show_bytes("HEAD", path)
        if pre != up:
            pre_drift.append(path)
        if pre != mig:
            migrate_diff.append(change(pre, mig, path, "pre-migrate", "migrate-commit"))
        if now != up:
            final_diff.append(change(up, now, path, base.name, "HEAD"))
            if is_binary(up, now):
                added_all.append(f"<binary {path} changed>")  # counts as a code change, never a comment
            else:
                a, r = diff_lines(as_text(up), as_text(now))
                added_all += a
                removed_all += r
                removed_comments += [(path, l) for l in r if is_comment(l)]
                final_lines |= {l.strip() for l in (as_text(now) or "").splitlines()}
            changed_manifest |= path.endswith(".pp")
    out["diffs"] = {"final_vs_baseline": "".join(final_diff) or "(identical to baseline)",
                    "migrate_commit": "".join(migrate_diff) or "(the migrate commit changed no class file)"}
    code_changes = [l for l in added_all + removed_all if not is_comment(l)]
    out["diff_summary"] = {"added": len(added_all), "removed": len(removed_all), "non_comment_changes": len(code_changes),
                           "header_only": not code_changes}
    prov, prov_ok = provenance_problems(migrate_diff, pre_drift, remigration)
    c["provenance"] = result("fail" if prov else "ok", prov or prov_ok)
    unlisted, accepted = unlisted_comment_removals(removed_comments, listed_comment_changes(cls), final_lines)
    c["comments_preserved"] = result(
        "fail" if unlisted else "ok",
        unlisted or ([f"listed in the local-change row (confirm each is justified): {a}" for a in accepted]
                     or "no baseline comment line removed"))

    # records
    rec = []
    tracker = [l for l in (STATE / "migrated_classes.txt").read_text().splitlines() if cls in l.split()]
    if len(tracker) != 1:
        rec.append(f"tracker has {len(tracker)} lines for the class")
    else:
        entry = generator.parse_tracker_line(tracker[0])
        if entry is None or not entry.done or entry.from_ref != base.name:
            rec.append(f"tracker line {tracker[0]!r} lacks `Done [from: {base.name}...]`")
        else:
            row = generator.parse_plan().get(cls)
            fixture = row.node_fixture if row else ""
            if fixture in test_asset_fixtures():  # a test asset (ruling 9): shown to the reviewer, no mock-apply
                out["node_fixture"] = node_fixture_summary(fixture)
                fixture_is_asset = True
            else:
                fixture_is_asset = False
            if fixture_is_asset:
                if entry.mock_apply:
                    rec.append(f"node fixture {fixture} is a test asset, yet the tracker says mock-apply")
            elif bool(fixture) != bool(entry.mock_apply):
                rec.append(f"plan node_fixture {fixture or '(none)'} vs tracker mock-apply "
                           f"{entry.mock_apply or '(none)'}: a node-fixture GREEN must be labelled mock-apply and only then")
            elif fixture:
                out["mock_apply"] = f"{entry.mock_apply} (node fixture {fixture}: behaviour NOT verified)"
                out["node_fixture"] = node_fixture_summary(fixture)
        if entry is not None and entry.done and entry.local_change:
            out["local_change"] = entry.local_change
            row_text = local_change_entry(cls)
            listed = generator.local_change_numbers(entry.local_change)
            rows = local_change_numbers(cls)
            if row_text is None:
                rec.append(f"marker says `local changes: {entry.local_change}` but rules/local_changes.md has no row "
                           "for the class")
            elif listed != rows:
                rec.append(f"marker lists `{entry.local_change}` but rules/local_changes.md has rows "
                           f"{', '.join(f'#{n}' for n in rows)} for the class (HQ batch-12 ruling 4: generated numbers)")
            else:
                out["local_change_row"] = row_text
                after = local_change_after_problems(cls, class_paths(cls, base))
                rec.extend(after)
                out["local_change_after"] = after or "every row's after-check passed on the current code"
        if entry is not None and entry.done and entry.from_ref == base.name and entry.defect_fixed:
            out["defect_fixed"] = entry.defect_fixed
            ruled = defect_entry(cls)
            if ruled is None:
                rec.append(f"marker says `upstream defect fixed: {entry.defect_fixed}` but "
                           ".codex_state/upstream_defects.md has no entry for the class")
            elif not ruled["status"].startswith(("ruled", "applied")):
                rec.append(f"upstream defect fix not authorized: registry status `{ruled['status']}`")
            else:
                out["ruled_change"] = ruled["change"]
    for problem in run2_justification_problems(cls, show("HEAD", f"manifests/{cls}.pp") or ""):
        rec.append(problem)
    if any(l.split()[:1] == [cls] for l in (STATE / "blocked.txt").read_text().splitlines() if not l.startswith("#")):
        rec.append("class is listed in blocked.txt")
    order = (STATE / "migration_order.md").read_text()
    done_section = order.split("## DONE", 1)[1].split("\n## ", 1)[0] if "## DONE" in order else ""
    if f"`puppet_infrastructure::{cls}`" not in done_section:
        rec.append("migration_order.md DONE section does not list the class")
    manifest_now = show("HEAD", f"manifests/{cls}.pp") or ""
    up_manifest = (baseline.git_show(base.upstream, base.commit, f"manifests/{cls}.pp") or b"").decode("utf-8", "replace")
    header_added = [l for l in diff_lines("\n".join(header_block(up_manifest)), "\n".join(header_block(manifest_now)))[0]
                    if is_comment(l)]
    if not header_added:
        rec.append("no migration header (no comment lines added before the class/define line)")
    elif not any(re.search(r"depend", l, re.I) for l in header_added):
        rec.append("migration header does not state module dependencies (or `none`)")
    c["records"] = result("fail" if rec else "ok", rec or f"tracker `{tracker[0]}`; header present")
    out["header"] = header_added

    # header module claims vs the master
    try:
        inv = master_inventory()
        by_forge = {m["forge"]: (name, m) for name, m in inv["modules"].items()}
        hm = []
        claims = module_claims(header_added, inv)
        for forge, version in claims:
            if forge not in by_forge:
                hm.append(f"header names `{forge}`, which is not installed under that name")
            elif version is None:
                hm.append(f"header names `{forge}` without a version")
            elif by_forge[forge][1]["version"] != version:
                hm.append(f"header says {forge} {version}; installed {by_forge[forge][1]['version']}")
        claimed = {by_forge[f][0] for f, _ in claims if f in by_forge}
        for mod in sorted(modules_used(manifest_now, inv) - claimed):
            hm.append(f"class uses module `{inv['modules'][mod]['forge']}` {inv['modules'][mod]['version']} but the header does not name it")
        c["header_modules"] = result("fail" if hm else "ok", hm or f"claims {claims or 'none'} match the master")
    except RuntimeError as exc:
        c["header_modules"] = result("error", str(exc))

    # syntax (pregate: parse/templates; lint findings NEW vs baseline)
    report = pregate.pregate_class(cls)
    bad = [f"{chk}: {d}" for lvl, chk, d in report.lines
           if lvl in ("FINDING", "ERROR") and (chk in ("parse", "erb", "epp", "master", "input") or d.endswith("(NEW vs baseline)"))]
    c["syntax"] = result("fail" if bad else "ok", bad or "parses; no lint finding beyond the baseline's")
    out["pregate_versions"] = report.versions

    # fixtures
    try:
        nics, users = node_identities(cls)
        fx = []
        for name, data in expanded_classes(cls):
            if data["title"] and data["title"] in nics | users:
                fx.append(f"{name}: plan title {data['title']!r} is a real node identity")
            # as in the harness: a per-target fixture for a base (params/for/<target>/), then the node's own
            # (params/<kind>/), else the shared one
            target_file = PARAMS_DIR / "for" / f"puppet_infrastructure::{cls}" / f"puppet_infrastructure::{name}.json"
            kind_file = PARAMS_DIR / node_kind(cls) / f"puppet_infrastructure::{name}.json"
            pfile = (target_file if name != cls and target_file.is_file() else
                     kind_file if kind_file.is_file() else PARAMS_DIR / f"puppet_infrastructure::{name}.json")
            if pfile.is_file():
                for key, val in json_strings(json.loads(pfile.read_text())):
                    if val in nics | users:
                        fx.append(f"{pfile.name}: {key} = real node identity (NIC/account)")
        c["fixtures"] = result("fail" if fx else "ok", fx or f"no real NIC {sorted(nics)} or account in titles/params")
    except RuntimeError as exc:
        c["fixtures"] = result("error", str(exc))

    # idempotency, revert-first
    if harness:
        DRAFTS.mkdir(parents=True, exist_ok=True)
        log = DRAFTS / f"{cls}.{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%SZ}.harness.log"
        proc = subprocess.run([str(HARNESS), "--revert-first", f"puppet_infrastructure::{cls}"],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=1800)
        text = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout + proc.stderr)
        log.write_text(text)
        run1 = re.search(r"RUN1_EVENTS: (\d+) catalog", text)
        coverage = re.findall(r"^COVERAGE .*$", text, re.M)
        revert = re.search(r"^REVERT_METRICS (.*)$", text, re.M)
        out["harness"] = {"rc": proc.returncode, "run1_catalog_events": int(run1.group(1)) if run1 else None,
                          "coverage": coverage, "revert": json.loads(revert.group(1)) if revert else None,
                          "log": str(log.relative_to(REPO)), **fresh_node_facts(text)}
        tail = [l for l in text.splitlines() if l.startswith(("ERROR", "GREEN", "Run 2 events", "Notice:"))][-6:]
        expected_run2 = re.search(r"^RUN2_EXPECTED_EVENTS: (\d+) from (.*) \(plan", text, re.M)
        out["harness"]["run2_expected_events"] = expected_run2.group(0) if expected_run2 else None
        green = "GREEN: run 2 exited 0" in text or "GREEN: run 2 events limited to the plan's expected_run2_events" in text
        if proc.returncode != 0 or not green:
            c["idempotent"] = result("fail", tail)
        elif not (out["harness"]["revert_first"] and out["harness"]["node_fresh"]):
            c["idempotent"] = result("fail", f"GREEN, but not on a freshly reverted node (revert_first="
                                             f"{out['harness']['revert_first']}, node_fresh={out['harness']['node_fresh']})")
        elif not run1 or int(run1.group(1)) == 0:
            c["idempotent"] = result("needs-justification", "GREEN, but run 1 after a revert applied 0 catalog events")
        else:
            allowed = (f"; run 2: {expected_run2.group(1)} event(s) only from expected_run2_events {expected_run2.group(2)} "
                       "(judge the header justification)") if expected_run2 and expected_run2.group(1) != "0" else ""
            c["idempotent"] = result("ok", f"GREEN; run 1 {run1.group(1)} catalog events{allowed}; {'; '.join(coverage)}")
    else:
        c["idempotent"] = result("skipped", "--no-harness")
    return out


# ----------------------------------------------------------------------------- CLI

def check_started(draft: dict) -> str | None:
    """UTC start of the mechanical check (checked_at is its end) — the start of the review phase in the metrics."""
    try:
        end = dt.datetime.strptime(draft["checked_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        return (end - dt.timedelta(seconds=float(draft.get("check_s") or 0))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    except (KeyError, ValueError):
        return None


def latest_draft(cls: str) -> Path:
    drafts = sorted(DRAFTS.glob(f"{cls}.*.draft.json"))
    if not drafts:
        raise SystemExit(f"ERROR: no draft for {cls}; run `check` first")
    refused = DRAFTS / f"{cls}.refused"
    if refused.exists() and refused.stat().st_mtime >= drafts[-1].stat().st_mtime:
        raise SystemExit(f"ERROR: the last `check` of {cls} was refused ({refused.read_text().strip()}); "
                         "no verdict is recorded — run `check` again in a valid mode")
    return drafts[-1]


NODE_FIXTURES = TOOLS / "tests" / "fixtures" / "node"


def node_fixture_summary(name: str) -> dict:
    """HQ batch-7 ruling 2: the reviewer confirms a mock-apply fixture stays within the stand-in its header states.
    The fixture's header and every resource it declares (type and title), for that judgement."""
    text = (NODE_FIXTURES / f"{name}.pp").read_text(encoding="utf-8")
    header = [line for line in text.splitlines() if line.startswith("#")]
    resources = [f"{m.group(1)}[{m.group(2)}]" for m in
                 re.finditer(r"^\s*([a-z][\w:]*)\s*\{\s*['\"]([^'\"]+)['\"]\s*:", text, re.M)]
    return {"name": name, "header": header, "resources": resources}


def decide(checks: dict, faithful: str, justify_run1: str | None) -> str:
    for name in CHECKS:
        status = checks.get(name, {}).get("status")
        if status == "ok":
            continue
        if name == "idempotent" and status == "needs-justification" and justify_run1:
            continue
        return "FAIL"
    return "PASS" if faithful == "ok" else "FAIL"


def node_option(cls: str, argv: list[str]) -> str | None:
    """`--node KIND`: validated, exported as P8_NODE for every node lookup and the harness; None without it."""
    if "--node" not in argv:
        return None
    i = argv.index("--node")
    kind = argv[i + 1] if i + 1 < len(argv) else ""
    import gen_migration_order as gen  # noqa: PLC0415
    import nodes  # noqa: PLC0415
    inventory = nodes.load()["nodes"]
    if kind not in inventory or inventory[kind]["status"] != "active":
        raise SystemExit(f"ERROR: --node {kind!r} is not an active node kind of nodes.yml")
    planned = (getattr(gen.parse_plan().get(cls), "node", "") or "")
    if planned and planned != kind:
        raise SystemExit(f"ERROR: the plan pins {cls} to node {planned}; --node {kind} would review it elsewhere")
    os.environ["P8_NODE"] = kind
    return kind


def cmd_check(argv: list[str]) -> int:
    cls = argv[0]
    kind = node_option(cls, argv)
    if "--fresh" in argv:
        error = fresh_usage_error(cls)
        if error:
            DRAFTS.mkdir(parents=True, exist_ok=True)
            (DRAFTS / f"{cls}.refused").write_text(f"{dt.datetime.now(dt.timezone.utc):%Y-%m-%dT%H:%M:%SZ} {error}\n")
            print(f"USAGE ERROR: {error}", file=sys.stderr)
            return 2
    started = dt.datetime.now(dt.timezone.utc)
    data = run_checks(cls, harness="--no-harness" not in argv)
    data["node"] = node_kind(cls)
    data["node_option"] = kind
    data["check_s"] = round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 1)
    data["checked_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = DRAFTS / f"{cls}.{data['checked_at'].replace(':', '').replace('-', '')}.draft.json"
    draft.write_text(json.dumps(data, indent=1))
    print(f"REVIEW CHECKS {cls} (baseline {data['baseline']}; migrate commit {data.get('migrate_commit')}: "
          f"{data.get('migrate_subject')}) on node {data['node']}")
    for name in CHECKS:
        if name in data["checks"]:
            ch = data["checks"][name]
            detail = ch["detail"] if isinstance(ch["detail"], str) else " | ".join(map(str, ch["detail"]))
            print(f"  {name}={ch['status']}: {detail[:600]}")
    print(f"  diff_summary: {data.get('diff_summary')}")
    if data.get("mock_apply"):
        print(f"  MOCK-APPLY: {data['mock_apply']}")
    if data.get("node_fixture"):
        fx = data["node_fixture"]
        print(f"  NODE FIXTURE {fx['name']} (read the file; the verdict needs --fixture-scope): resources "
              + ", ".join(fx["resources"]))
    if data.get("ruled_change"):
        print(f"  RULED UPSTREAM-DEFECT CHANGE (tracker: {data.get('defect_fixed')}): {data['ruled_change']}")
    if data.get("local_change_row"):
        print(f"  LOCAL CHANGE, POLICY B (tracker: {data.get('local_change')}): {data['local_change_row']}")
    print("---- DIFF A: final content vs baseline (what the tracker marker claims) ----")
    print(data["diffs"].get("final_vs_baseline", "")[:12000])
    print("---- DIFF B: the migrate commit itself (what the migration changed) ----")
    print(data["diffs"].get("migrate_commit", "")[:12000])
    print(f"DRAFT {draft.relative_to(REPO)}")
    return 0


def cmd_verdict(argv: list[str]) -> int:
    cls, rest = argv[0], argv[1:]
    kind = node_option(cls, rest)
    if kind:
        i = rest.index("--node")
        rest = rest[:i] + rest[i + 2:]
    faithful, evidence, justify, scope = None, [], None, None
    i = 0
    while i < len(rest):
        if rest[i] == "--faithful":
            faithful = rest[i + 1]
        elif rest[i] == "--evidence":
            evidence.append(rest[i + 1])
        elif rest[i] == "--justify-run1":
            justify = rest[i + 1]
        elif rest[i] == "--fixture-scope":
            scope = rest[i + 1]
        else:
            raise SystemExit(f"ERROR: unknown argument {rest[i]}")
        i += 2
    if faithful not in ("ok", "fail") or not evidence:
        raise SystemExit("ERROR: verdict needs --faithful ok|fail and at least one --evidence")
    draft = json.loads(latest_draft(cls).read_text())
    if draft.get("node_option") != kind:
        raise SystemExit(f"ERROR: the latest draft of {cls} was checked with --node {draft.get('node_option')}, not "
                         f"--node {kind}; run `check {cls}{' --node ' + kind if kind else ''}` first")
    if draft.get("node_fixture") and not scope:
        raise SystemExit(f"ERROR: {cls} went GREEN on node fixture {draft['node_fixture']['name']} (mock-apply): the "
                         "verdict needs --fixture-scope \"<what each fixture resource does and that it stays within the "
                         "stand-in its header states>\" (HQ batch-7 ruling 2)")
    checks = draft["checks"]
    verdict = decide(checks, faithful, justify)
    record = {"schema": 1, "class": cls, "verdict": verdict, "reviewer": "reviewer-v2",
              "reviewed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "baseline": draft["baseline"], "migrate_commit": draft.get("migrate_commit"),
              "migrate_subject": draft.get("migrate_subject"), "checks": checks,
              "faithful": {"status": faithful, "evidence": evidence}, "justify_run1": justify,
              "diff_summary": draft.get("diff_summary"), "header": draft.get("header"),
              "harness": draft.get("harness"), "pregate_versions": draft.get("pregate_versions"),
              "node": draft.get("node")}
    if draft.get("node_fixture"):
        record["mock_apply"] = draft.get("mock_apply")
        record["node_fixture"] = {**draft["node_fixture"], "scope_evidence": scope}
    where = VERDICTS / cls / "nodes" / kind if kind else VERDICTS / cls
    where.mkdir(parents=True, exist_ok=True)
    path = where / f"{record['reviewed_at'].replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(record, indent=1) + "\n")
    print(f"VERDICT: {verdict}")
    print(f"class: {cls}" + (f" (node {kind})" if kind else ""))
    print("checks: " + " ".join(f"{n}={checks.get(n, {}).get('status', 'missing')}" for n in CHECKS)
          + f" faithful={faithful}")
    print("evidence:")
    for n in CHECKS:
        ch = checks.get(n, {})
        if ch.get("status") != "ok":
            detail = ch.get("detail")
            print(f"  {n}: {detail if isinstance(detail, str) else ' | '.join(map(str, detail or []))}"[:900])
    for e in evidence:
        print(f"  faithful: {e}"[:900])
    if scope:
        print(f"  fixture-scope: {scope}"[:900])
    print(f"persisted: {path.relative_to(REPO)}")
    if kind:  # a per-node verdict (HQ batch-8 ruling 6) is not a Phase 1 attempt: no metrics event
        return 0
    # step 3.4: metrics event (the reviewer never reads .codex_state/runs/ or the event log)
    failed = [n for n in CHECKS if checks.get(n, {}).get("status") != "ok"] + ([] if faithful == "ok" else ["faithful"])
    subprocess.run([sys.executable, str(TOOLS / "metrics.py"), "event", cls, "review",
                    json.dumps({"verdict": verdict, "failed_checks": failed, "check_s": draft.get("check_s"),
                                "check_started": check_started(draft), "file": str(path.relative_to(REPO))})],
                   capture_output=True)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "check" and re.fullmatch(r"[a-z][a-z0-9_]*", argv[1]):
        return cmd_check(argv[1:])
    if len(argv) >= 2 and argv[0] == "verdict" and re.fullmatch(r"[a-z][a-z0-9_]*", argv[1]):
        return cmd_verdict(argv[1:])
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
