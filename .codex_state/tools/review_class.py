#!/usr/bin/env python3
"""Reviewer v2 evidence tool (step 1.4). Independent: it reads git, the files, the pinned baseline, the
master's module inventory and its own harness run. It never reads logs/runs/transcripts and never
prints commit authors or commit bodies (rule 9: the reviewer does not learn who authored a change).

  review_class.py check <class> [--no-harness] [--fresh]
      Mechanical checks + the two diffs. Writes a draft to .codex_state/logs/reviews/ (untracked).
      --fresh: the migrate commit must be at HEAD or under at most 3 record/regenerate commits.
  review_class.py verdict <class> --faithful ok|fail --evidence TEXT [--evidence TEXT ...]
                                  [--justify-run1 TEXT]
      Combines the latest draft with the reviewer's faithfulness judgement and writes the persisted
      verdict .codex_state/reviews/<class>/<UTC>.json (tracked, append-only). Prints the report.

Verdict PASS = every mechanical check ok AND faithful ok. Checks: git, scope, provenance, records,
header_modules, comments_preserved, syntax, fixtures, idempotent.
"""

from __future__ import annotations

import datetime as dt
import difflib
import json
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


def show(ref: str, path: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None


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
        for m in re.finditer(r"\b([a-z0-9]+)-([a-z][a-z0-9_]*)\b(?:\s+v?(\d+\.\d+\.\d+))?", line):
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


def node_identities() -> tuple[set[str], set[str]]:
    """(real NIC names, human accounts) on the node — values a fixture must never use."""
    proc = subprocess.run(["timeout", "30", "ssh", "puppet8node",
                           "ls /sys/class/net; echo ---; getent passwd | awk -F: '$3>=1000 && $3<65534 {print $1}'"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        raise RuntimeError("cannot read NICs/accounts from puppet8node")
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

    def visit(name: str):
        if name in seen:
            return
        seen.add(name)
        data = json.loads(subprocess.run([sys.executable, str(STATE / "gen_migration_order.py"), "--classify", name],
                                         capture_output=True, text=True, check=True).stdout)
        for b in data["required_base"]:
            visit(b)
        order.append((name, data))
    visit(cls)
    return order


# ----------------------------------------------------------------------------- checks

def run_checks(cls: str, harness: bool, fresh: bool) -> dict:
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
    if fresh and (len(later) > 3 or any(not s.startswith(RECORD_SUBJECTS) for s in later)):
        problems.append(f"--fresh: migrate commit is under {len(later)} later commits: {later[:5]}")
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
    for path in paths:
        upstream = baseline.git_show(base.upstream, base.commit, path)
        up = upstream.decode("utf-8", "replace") if upstream is not None else None
        pre, mig, now = show(parent, path), show(commit, path), show("HEAD", path)
        if pre != up:
            pre_drift.append(path)
        if pre != mig:
            migrate_diff.append(unified(pre, mig, path, "pre-migrate", "migrate-commit"))
        if now != up:
            final_diff.append(unified(up, now, path, base.name, "HEAD"))
            a, r = diff_lines(up, now)
            added_all += a
            removed_all += r
            removed_comments += [f"{path}: {l.strip()}" for l in r if is_comment(l)]
            changed_manifest |= path.endswith(".pp")
    out["diffs"] = {"final_vs_baseline": "".join(final_diff) or "(identical to baseline)",
                    "migrate_commit": "".join(migrate_diff) or "(the migrate commit changed no class file)"}
    code_changes = [l for l in added_all + removed_all if not is_comment(l)]
    out["diff_summary"] = {"added": len(added_all), "removed": len(removed_all), "non_comment_changes": len(code_changes),
                           "header_only": not code_changes}
    prov, prov_ok = provenance_problems(migrate_diff, pre_drift, remigration)
    c["provenance"] = result("fail" if prov else "ok", prov or prov_ok)
    c["comments_preserved"] = result("fail" if removed_comments else "ok",
                                     removed_comments or "no baseline comment line removed")

    # records
    rec = []
    tracker = [l for l in (STATE / "migrated_classes.txt").read_text().splitlines() if cls in l.split()]
    if len(tracker) != 1:
        rec.append(f"tracker has {len(tracker)} lines for the class")
    else:
        entry = generator.parse_tracker_line(tracker[0])
        if entry is None or not entry.done or entry.from_ref != base.name:
            rec.append(f"tracker line {tracker[0]!r} lacks `Done [from: {base.name}...]`")
        elif entry.defect_fixed:
            out["defect_fixed"] = entry.defect_fixed
            ruled = defect_entry(cls)
            if ruled is None:
                rec.append(f"marker says `upstream defect fixed: {entry.defect_fixed}` but "
                           ".codex_state/upstream_defects.md has no entry for the class")
            elif not ruled["status"].startswith(("ruled", "applied")):
                rec.append(f"upstream defect fix not authorized: registry status `{ruled['status']}`")
            else:
                out["ruled_change"] = ruled["change"]
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
        nics, users = node_identities()
        fx = []
        for name, data in expanded_classes(cls):
            if data["title"] and data["title"] in nics | users:
                fx.append(f"{name}: plan title {data['title']!r} is a real node identity")
            pfile = PARAMS_DIR / f"puppet_infrastructure::{name}.json"
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
                          "log": str(log.relative_to(REPO))}
        tail = [l for l in text.splitlines() if l.startswith(("ERROR", "GREEN", "Run 2 events", "Notice:"))][-6:]
        if proc.returncode != 0 or "GREEN: run 2 exited 0" not in text:
            c["idempotent"] = result("fail", tail)
        elif not run1 or int(run1.group(1)) == 0:
            c["idempotent"] = result("needs-justification", "GREEN, but run 1 after a revert applied 0 catalog events")
        else:
            c["idempotent"] = result("ok", f"GREEN; run 1 {run1.group(1)} catalog events; {'; '.join(coverage)}")
    else:
        c["idempotent"] = result("skipped", "--no-harness")
    return out


# ----------------------------------------------------------------------------- CLI

def latest_draft(cls: str) -> Path:
    drafts = sorted(DRAFTS.glob(f"{cls}.*.draft.json"))
    if not drafts:
        raise SystemExit(f"ERROR: no draft for {cls}; run `check` first")
    return drafts[-1]


def decide(checks: dict, faithful: str, justify_run1: str | None) -> str:
    for name in CHECKS:
        status = checks.get(name, {}).get("status")
        if status == "ok":
            continue
        if name == "idempotent" and status == "needs-justification" and justify_run1:
            continue
        return "FAIL"
    return "PASS" if faithful == "ok" else "FAIL"


def cmd_check(argv: list[str]) -> int:
    cls = argv[0]
    started = dt.datetime.now(dt.timezone.utc)
    data = run_checks(cls, harness="--no-harness" not in argv, fresh="--fresh" in argv)
    data["check_s"] = round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 1)
    data["checked_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = DRAFTS / f"{cls}.{data['checked_at'].replace(':', '').replace('-', '')}.draft.json"
    draft.write_text(json.dumps(data, indent=1))
    print(f"REVIEW CHECKS {cls} (baseline {data['baseline']}; migrate commit {data.get('migrate_commit')}: "
          f"{data.get('migrate_subject')})")
    for name in CHECKS:
        if name in data["checks"]:
            ch = data["checks"][name]
            detail = ch["detail"] if isinstance(ch["detail"], str) else " | ".join(map(str, ch["detail"]))
            print(f"  {name}={ch['status']}: {detail[:600]}")
    print(f"  diff_summary: {data.get('diff_summary')}")
    if data.get("ruled_change"):
        print(f"  RULED UPSTREAM-DEFECT CHANGE (tracker: {data.get('defect_fixed')}): {data['ruled_change']}")
    print("---- DIFF A: final content vs baseline (what the tracker marker claims) ----")
    print(data["diffs"].get("final_vs_baseline", "")[:12000])
    print("---- DIFF B: the migrate commit itself (what the migration changed) ----")
    print(data["diffs"].get("migrate_commit", "")[:12000])
    print(f"DRAFT {draft.relative_to(REPO)}")
    return 0


def cmd_verdict(argv: list[str]) -> int:
    cls, rest = argv[0], argv[1:]
    faithful, evidence, justify = None, [], None
    i = 0
    while i < len(rest):
        if rest[i] == "--faithful":
            faithful = rest[i + 1]
        elif rest[i] == "--evidence":
            evidence.append(rest[i + 1])
        elif rest[i] == "--justify-run1":
            justify = rest[i + 1]
        else:
            raise SystemExit(f"ERROR: unknown argument {rest[i]}")
        i += 2
    if faithful not in ("ok", "fail") or not evidence:
        raise SystemExit("ERROR: verdict needs --faithful ok|fail and at least one --evidence")
    draft = json.loads(latest_draft(cls).read_text())
    checks = draft["checks"]
    verdict = decide(checks, faithful, justify)
    record = {"schema": 1, "class": cls, "verdict": verdict, "reviewer": "reviewer-v2",
              "reviewed_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "baseline": draft["baseline"], "migrate_commit": draft.get("migrate_commit"),
              "migrate_subject": draft.get("migrate_subject"), "checks": checks,
              "faithful": {"status": faithful, "evidence": evidence}, "justify_run1": justify,
              "diff_summary": draft.get("diff_summary"), "header": draft.get("header"),
              "harness": draft.get("harness"), "pregate_versions": draft.get("pregate_versions")}
    VERDICTS.joinpath(cls).mkdir(parents=True, exist_ok=True)
    path = VERDICTS / cls / f"{record['reviewed_at'].replace(':', '').replace('-', '')}.json"
    path.write_text(json.dumps(record, indent=1) + "\n")
    print(f"VERDICT: {verdict}")
    print(f"class: {cls}")
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
    print(f"persisted: {path.relative_to(REPO)}")
    # step 3.4: metrics event (the reviewer never reads .codex_state/runs/ or the event log)
    failed = [n for n in CHECKS if checks.get(n, {}).get("status") != "ok"] + ([] if faithful == "ok" else ["faithful"])
    subprocess.run([sys.executable, str(TOOLS / "metrics.py"), "event", cls, "review",
                    json.dumps({"verdict": verdict, "failed_checks": failed, "check_s": draft.get("check_s"),
                                "file": str(path.relative_to(REPO))})], capture_output=True)
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
