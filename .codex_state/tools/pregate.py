#!/usr/bin/env python3
"""Pre-VM gate (ruling 4, amended 2026-10-26): cheap checks before a class touches the node.

  pregate.py <class>             report on one class (exit 0 CLEAN, 1 FINDINGS, 2 ERROR)
  pregate.py --json <class>      same, plus one PREGATE_JSON line
  pregate.py --staged            pre-commit mode: syntax + NEW lint findings of staged puppet files

Laptop side (no puppet here: the laptop is a production Puppet 5 node): baseline drift of manifest
+ templates + files, template legacy-fact grep, static hazard scanner (CLAUDE.md items 1, 2, 5, 6, 9).
Master side, one ssh round trip (puppet8master, OpenVox): `puppet parser validate`, allowlisted
puppet-lint (never --fix), `puppet epp validate`, ERB syntax via the agent ruby, and the inventory of
installed module types/classes. Lint runs on the local AND the baseline copy so inherited upstream
findings are told apart from new ones. Tool versions are printed on every run.
"""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
import baseline  # noqa: E402

REPO = baseline.REPO
MASTER_HOST = "puppet8master"
LINT_CHECKS = "legacy_facts,top_scope_facts,variable_scope,duplicate_params,unquoted_resource_title,parameter_order"

CORE_TYPES = {
    "augeas", "cron", "exec", "file", "filebucket", "group", "host", "k5login", "mailalias", "mount",
    "notify", "package", "resources", "schedule", "scheduled_task", "selboolean", "selmodule", "service",
    "ssh_authorized_key", "sshkey", "stage", "tidy", "user", "yumrepo", "zfs", "zone", "zpool",
}
KEYWORDS = {"class", "define", "node", "if", "elsif", "else", "unless", "case", "default", "and", "or", "in"}
STDLIB4_REMOVED = re.compile(
    r"\b(validate_[a-z0-9_]+|is_(?:absolute_path|array|bool|domain_name|email_address|float|function_available|"
    r"hash|integer|ip_address|ipv4_address|ipv6_address|mac_address|numeric|string)|has_key|private|type3x|"
    r"sprintf_hash|size)\s*\("
)
OS_EXEC = re.compile(r"\b(dnf|yum|rpm|subscription-manager|zypper|apt-get|dpkg|snap)\b")
OS_GUARD = re.compile(r"\$facts\[['\"]os['\"]\]|\$::osfamily|\$osfamily|\$::operatingsystem|os\.family")
EXEC_GUARDS = re.compile(r"(?<![\w$])(unless|onlyif|creates|refreshonly)\s*=>")
LEGACY_FACT_NAMES = (
    r"architecture|domain|fqdn|hardwaremodel|hostname|ipaddress\w*|is_virtual|kernel\w*|lsbdist\w*|"
    r"macaddress\w*|manufacturer|memorysize\w*|netmask\w*|network\w*|operatingsystem\w*|osfamily|"
    r"processorcount|productname|serialnumber|timezone|uptime\w*|virtual"
)
ERB_LEGACY = re.compile(rf"@({LEGACY_FACT_NAMES})\b|scope\.lookupvar\(\s*['\"]::(\w+)|scope\[\s*['\"]::(\w+)")
EPP_LEGACY = re.compile(r"\$::([a-z]\w*)")

REMOTE = r'''set -u
d="$1"; checks="$2"; inventory="$3"
P=/opt/puppetlabs/bin/puppet; L=/opt/puppetlabs/puppet/bin/puppet-lint; R=/opt/puppetlabs/puppet/bin
echo "@@VERSION puppet $($P --version 2>&1)"
echo "@@VERSION puppet-lint $($L --version 2>&1 | awk '{print $2}')"
echo "@@VERSION ruby $($R/ruby -e 'print RUBY_VERSION' 2>&1)"
emit() { printf '@@BEGIN %s %s %s %s\n%s\n@@END\n' "$1" "$2" "$3" "$4" "$5"; }
for side in local base; do
  [ -d "$d/$side" ] || continue
  (cd "$d/$side" && find . -type f | sort) | while read -r f; do
    rel="${f#./}"; path="$d/$side/$rel"
    case "$side:$rel" in
      local:*.pp)
        out="$($P parser validate "$path" 2>&1)"; emit parse "$side" "$rel" "$?" "$out"
        out="$($L --json --only-checks "$checks" "$path" 2>&1)"; emit lint "$side" "$rel" "$?" "$out" ;;
      base:*.pp) out="$($L --json --only-checks "$checks" "$path" 2>&1)"; emit lint "$side" "$rel" "$?" "$out" ;;
      local:templates/*.epp) out="$($P epp validate "$path" 2>&1)"; emit epp "$side" "$rel" "$?" "$out" ;;
      local:templates/*) out="$($R/erb -P -x -T - "$path" | $R/ruby -c 2>&1)"; emit erb "$side" "$rel" "$?" "$out" ;;
    esac
  done
done
if [ "$inventory" = 1 ]; then
  M=/etc/puppetlabs/code/environments/production/modules
  for m in "$M"/*/; do m="$(basename "$m")"; [ "$m" = puppet_infrastructure ] || echo "@@MODULE $m"; done
  for t in "$M"/*/lib/puppet/type/*.rb /opt/puppetlabs/puppet/vendor_modules/*/lib/puppet/type/*.rb; do
    [ -f "$t" ] && echo "@@TYPE $(basename "$t" .rb)"
  done
  for m in "$M"/*/; do
    mod="$(basename "$m")"; [ "$mod" = puppet_infrastructure ] && continue
    (cd "$m" && find manifests -name '*.pp' 2>/dev/null) | while read -r p; do
      p="${p#manifests/}"; p="${p%.pp}"
      if [ "$p" = init ]; then echo "@@DEFINE $mod"; else echo "@@DEFINE $mod::${p//\//::}"; fi
    done
  done
fi
'''


@dataclass
class Report:
    target: str
    lines: list[tuple[str, str, str]] = field(default_factory=list)  # (level, check, detail)
    versions: dict[str, str] = field(default_factory=dict)

    def add(self, level: str, check: str, detail: str) -> None:
        self.lines.append((level, check, detail))

    @property
    def status(self) -> str:
        levels = {lvl for lvl, _, _ in self.lines}
        return "ERROR" if "ERROR" in levels else "FINDINGS" if "FINDING" in levels else "CLEAN"


# ---------------------------------------------------------------- laptop-side analysis

def strip_comments(manifest: str) -> str:
    return re.sub(r"(?m)#.*$", "", manifest)


def local_vars(manifest: str) -> set[str]:
    return set(re.findall(r"\$([a-z_][a-z0-9_]*)\s*(?:=|,|\))", manifest))


def resource_types(manifest: str) -> set[str]:
    code = strip_comments(manifest)
    found = set(re.findall(r"(?<![\w:$])([a-z][a-z0-9_]*(?:::[a-z][a-z0-9_]*)*)\s*\{\s*(?=['\"$\[]|[a-z])", code))
    return {t for t in found if t not in KEYWORDS}


def declared_classes(manifest: str) -> set[str]:
    code = strip_comments(manifest)
    names = set(re.findall(r"class\s*\{\s*['\"](?:::)?([a-z][\w:]*)['\"]\s*:", code))
    for stmt in re.findall(r"(?m)^\s*(?:include|contain)\s+([^\n]+)", code):
        names.update(n.strip().lstrip(":") for n in stmt.split(",") if re.fullmatch(r"\s*(?:::)?[a-z][\w:]*\s*", n))
    return names


def exec_blocks(manifest: str) -> list[tuple[str, str, bool]]:
    """(title, body, os_guarded) of every exec resource, by brace matching.

    os_guarded: some enclosing block opens with if/elsif/unless/case on an OS fact
    (a case branch such as `'RedHat': {` counts through its enclosing `case`).
    """
    code = strip_comments(manifest)
    out = []
    for m in re.finditer(r"(?<![\w:])exec\s*\{", code):
        depth, i = 1, m.end()
        while i < len(code) and depth:
            depth += {"{": 1, "}": -1}.get(code[i], 0)
            i += 1
        body = code[m.end():i - 1]
        title = body.split(":", 1)[0].strip()
        out.append((title, body, enclosed_by_os_guard(code, m.start())))
    return out


def enclosed_by_os_guard(code: str, pos: int) -> bool:
    openers = []
    for i, ch in enumerate(code[:pos]):
        if ch == "{":
            openers.append(i)
        elif ch == "}" and openers:
            openers.pop()
    for opener in openers:
        start = max(code.rfind("{", 0, opener), code.rfind("}", 0, opener), 0)
        header = code[start:opener]
        if re.search(r"\b(if|elsif|unless|case)\b", header) and OS_GUARD.search(header):
            return True
    return False


def scan_hazards(manifest: str, inventory: dict | None, report: Report) -> None:
    code = strip_comments(manifest)
    # 1. external custom types / classes from modules that are not installed
    if inventory is not None:
        known = CORE_TYPES | inventory["types"] | inventory["defines"]
        for t in sorted(resource_types(manifest)):
            if t.startswith("puppet_infrastructure::") or t in known:
                continue
            report.add("FINDING", "hazard1-types", f"resource type `{t}` is not core and no installed module provides it")
        for c in sorted(declared_classes(manifest)):
            top = c.split("::")[0]
            if top != "puppet_infrastructure" and c not in inventory["defines"]:
                report.add("FINDING", "hazard1-types", f"class `{c}` is declared but module `{top}` does not provide it on the master")
    # 2. node->master connectivity
    if re.search(r"chain\s*=>\s*['\"]OUTPUT|firewallchain\s*\{\s*['\"]OUTPUT", code):
        report.add("FINDING", "hazard2-connectivity", "touches the OUTPUT chain (can sever the agent's connection to master:8140)")
    if re.search(r"policy\s*=>\s*['\"]?drop", code, re.I):
        report.add("FINDING", "hazard2-connectivity", "sets a default-drop chain policy")
    # 5 and 9. execs
    for title, body, guarded in exec_blocks(manifest):
        command = re.search(r"command\s*=>\s*([^\n]+)", body)
        text = (command.group(1) if command else title) + " " + title
        if OS_EXEC.search(text):
            if guarded:
                report.add("INFO", "hazard5-os-exec", f"exec {title} runs an OS-specific command inside an OS conditional")
            else:
                report.add("FINDING", "hazard5-os-exec", f"exec {title} runs an OS-specific command with no enclosing OS conditional")
        if not EXEC_GUARDS.search(body):
            report.add("FINDING", "hazard9-exec-guard", f"exec {title} has no unless/onlyif/creates/refreshonly (runs every agent run)")
        for guard in re.findall(r"(?:unless|onlyif)\s*=>\s*['\"]([^'\"]+)", body):
            report.add("INFO", "hazard9-exec-guard", f"exec {title} guard command `{guard.split()[0]}` must exist on the node (a missing guard binary RUNS the command)")
    # 6. stdlib-4 functions removed in stdlib 9
    for fn in sorted(set(STDLIB4_REMOVED.findall(code))):
        report.add("FINDING", "hazard6-stdlib", f"calls `{fn}()`, removed in stdlib 9")


def scan_template(path: str, text: str, manifest_vars: set[str], report: Report) -> None:
    """template() is ERB whatever the file is called; epp() templates end in .epp."""
    hits: dict[str, int] = {}
    if not path.endswith(".epp"):
        for m in ERB_LEGACY.finditer(text):
            name = next(g for g in m.groups() if g)
            if m.group(1) and name in manifest_vars:
                continue  # @name is a class variable, not a fact
            hits[m.group(0)] = hits.get(m.group(0), 0) + 1
        why = "renders EMPTY on Puppet 8 (legacy fact)"
    else:
        for name in EPP_LEGACY.findall(text):
            if name not in ("facts", "trusted", "settings"):
                hits[f"$::{name}"] = hits.get(f"$::{name}", 0) + 1
        why = "top-scope/legacy fact"
    for expr, count in sorted(hits.items()):
        report.add("FINDING", "template-legacy-fact", f"{path}: `{expr}` x{count} {why}")


def local_class_files(cls: str) -> list[str]:
    """Manifest + templates/files the LOCAL manifest references (prefix references globbed)."""
    manifest_path = f"manifests/{cls}.pp"
    manifest = (REPO / manifest_path).read_text(encoding="utf-8")
    paths = [manifest_path]
    for path, is_prefix in baseline.referenced_paths(manifest):
        if is_prefix:
            root = REPO / path.rsplit("/", 1)[0]
            paths += sorted(str(p.relative_to(REPO)) for p in root.rglob("*")
                            if p.is_file() and str(p.relative_to(REPO)).startswith(path)) if root.is_dir() else []
        elif (REPO / path).is_dir():
            paths += sorted(str(p.relative_to(REPO)) for p in (REPO / path).rglob("*") if p.is_file())
        elif (REPO / path).is_file():
            paths.append(path)
    return paths


# ---------------------------------------------------------------- master-side batch

def build_tar(local: dict[str, bytes], base: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for side, files in (("local", local), ("base", base)):
            for rel, data in files.items():
                info = tarfile.TarInfo(f"{side}/{rel}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        script = REMOTE.encode()
        info = tarfile.TarInfo("remote.sh")
        info.size = len(script)
        tar.addfile(info, io.BytesIO(script))
    return buf.getvalue()


def run_remote(tar_bytes: bytes, inventory: bool) -> str:
    cmd = ('d=$(mktemp -d /tmp/pregate.XXXXXX) && tar -C "$d" -xf - && '
           f'bash "$d/remote.sh" "$d" {LINT_CHECKS} {1 if inventory else 0}; rc=$?; rm -rf "$d"; exit $rc')
    proc = subprocess.run(["timeout", "120", "ssh", "-T", MASTER_HOST, cmd], input=tar_bytes,
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"master batch failed (exit {proc.returncode}): {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout.decode(errors="replace")


def parse_remote(output: str) -> tuple[dict, list[dict], dict]:
    versions, results = {}, []
    inventory = {"modules": set(), "types": set(), "defines": set()}
    lines, i = output.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("@@VERSION "):
            _, tool, ver = line.split(" ", 2)
            versions[tool] = ver
        elif line.startswith("@@MODULE "):
            inventory["modules"].add(line.split(" ", 1)[1])
        elif line.startswith("@@TYPE "):
            inventory["types"].add(line.split(" ", 1)[1])
        elif line.startswith("@@DEFINE "):
            inventory["defines"].add(line.split(" ", 1)[1])
        elif line.startswith("@@BEGIN "):
            _, check, side, rel, rc = line.split(" ", 4)
            body = []
            i += 1
            while i < len(lines) and lines[i] != "@@END":
                body.append(lines[i])
                i += 1
            results.append({"check": check, "side": side, "path": rel, "rc": int(rc), "out": "\n".join(body).strip()})
        i += 1
    return versions, results, inventory


def lint_problems(out: str) -> list[dict]:
    try:
        data = json.loads(out) if out else []
    except json.JSONDecodeError:
        return [{"kind": "error", "check": "lint-output", "message": out[:300], "line": 0}]
    flat, stack = [], [data]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, dict) and "check" in item:
            flat.append(item)
    return sorted(flat, key=lambda p: (p.get("line", 0), p["check"]))


def lint_key(problem: dict) -> tuple[str, str]:
    return (problem["check"], re.sub(r"\d+", "N", problem.get("message", "")))


def apply_remote(results: list[dict], report: Report, report_inherited: bool,
                 identical_to_baseline: frozenset[str] = frozenset()) -> None:
    by = {(r["check"], r["side"], r["path"]): r for r in results}
    for r in results:
        if r["side"] != "local":
            continue
        where = r["path"]
        if r["check"] in ("parse", "epp", "erb"):
            if r["rc"] == 0:
                report.add("PASS", r["check"], where)
            else:
                report.add("FINDING", r["check"], f"{where}: {r['out'].splitlines()[-1] if r['out'] else 'failed'}")
        elif r["check"] == "lint":
            base = by.get(("lint", "base", where))
            if base is not None:
                inherited = [lint_key(p) for p in lint_problems(base["out"])]
            elif where in identical_to_baseline:
                inherited = [lint_key(p) for p in lint_problems(r["out"])]
            else:
                inherited = []
            problems = lint_problems(r["out"])
            for p in problems:
                key = lint_key(p)
                if key in inherited:
                    inherited.remove(key)
                    if report_inherited:
                        report.add("FINDING", f"lint:{p['check']}", f"{where}:{p.get('line')}: {p.get('message')} (also in baseline)")
                else:
                    report.add("FINDING", f"lint:{p['check']}", f"{where}:{p.get('line')}: {p.get('message')} (NEW vs baseline)")
            if not problems:
                report.add("PASS", "lint", f"{where} ({LINT_CHECKS})")


# ---------------------------------------------------------------- modes

def is_done(cls: str) -> bool:
    """Git-derived done status (same rule as gen_migration_order: P8: migrate commit, not blocked)."""
    import gen_migration_order as gen  # noqa: PLC0415
    return cls in set(gen.git_migrations()) - set(gen.read_blocked())


def pregate_class(cls: str) -> Report:
    report = Report(cls)
    base = baseline.load()
    report.versions["baseline"] = f"{base.name} ({base.commit[:7]})"
    report.versions["python"] = sys.version.split()[0]
    manifest_path = REPO / f"manifests/{cls}.pp"
    if not manifest_path.is_file():
        report.add("ERROR", "input", f"no local manifest {manifest_path.relative_to(REPO)}")
        return report
    drift = baseline.local_drift(cls, base)
    done = is_done(cls)
    for path in drift:
        report.add("INFO" if done else "FINDING", "drift",
                   f"{path} differs from {base.name} — " + ("migrated class: the diff is the migration, review it"
                                                             if done else "pending class: baseline-sync before migrating"))
    if not drift:
        report.add("PASS", "drift", f"manifest + templates/files identical to {base.name}")
    files = local_class_files(cls)
    local = {p: (REPO / p).read_bytes() for p in files if p.endswith(".pp") or p.startswith("templates/")}
    base_files = {}
    for p in local:
        data = baseline.git_show(base.upstream, base.commit, p)
        if data is not None and p.endswith(".pp") and data != local[p]:
            base_files[p] = data  # identical baseline copies are not re-linted: inherited == local
    manifest = manifest_path.read_text(encoding="utf-8")
    try:
        versions, results, inventory = parse_remote(run_remote(build_tar(local, base_files), inventory=True))
    except RuntimeError as exc:
        report.add("ERROR", "master", str(exc))
        versions, results, inventory = {}, [], None
    report.versions.update(versions)
    identical = frozenset(p for p in local if p.endswith(".pp") and p not in base_files
                          and baseline.git_show(base.upstream, base.commit, p) == local[p])
    apply_remote(results, report, report_inherited=True, identical_to_baseline=identical)
    scan_hazards(manifest, inventory, report)
    variables = local_vars(manifest)
    for p in files:
        if p.startswith("templates/"):
            scan_template(p, (REPO / p).read_text(encoding="utf-8", errors="replace"), variables, report)
    return report


def pregate_staged() -> Report:
    """Pre-commit: staged puppet files whose content differs from the baseline must parse and add no lint findings."""
    report = Report("staged")
    base = baseline.load()
    report.versions["baseline"] = f"{base.name} ({base.commit[:7]})"
    names = subprocess.run(["git", "-C", str(REPO), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                           capture_output=True, text=True, check=True).stdout.split()
    local, base_files = {}, {}
    for name in names:
        if not re.fullmatch(r"(manifests/.+\.pp|templates/.+)", name):
            continue
        staged = subprocess.run(["git", "-C", str(REPO), "show", f":{name}"], capture_output=True, check=True).stdout
        upstream = baseline.git_show(base.upstream, base.commit, name)
        if staged == upstream:
            report.add("PASS", "baseline-verbatim", f"{name} identical to {base.name}; not linted")
            continue
        local[name] = staged
        if upstream is not None:
            base_files[name] = upstream
    if local:
        try:
            versions, results, _ = parse_remote(run_remote(build_tar(local, base_files), inventory=False))
        except RuntimeError as exc:
            report.add("ERROR", "master", f"{exc} — puppet files cannot be committed unchecked")
            return report
        report.versions.update(versions)
        apply_remote(results, report, report_inherited=False)
    return report


def print_report(report: Report, as_json: bool) -> None:
    print("PREGATE versions: " + ", ".join(f"{k} {v}" for k, v in report.versions.items()))
    for level, check, detail in report.lines:
        print(f"{level:7} {check}: {detail}")
    findings = sum(1 for lvl, _, _ in report.lines if lvl == "FINDING")
    print(f"PREGATE {report.target}: {report.status}" + (f" ({findings} findings)" if findings else ""))
    if as_json:
        print("PREGATE_JSON " + json.dumps({"class": report.target, "status": report.status, "versions": report.versions,
                                            "findings": [{"check": c, "detail": d} for lvl, c, d in report.lines if lvl == "FINDING"]}))


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if argv == ["--staged"]:
        report = pregate_staged()
    elif len(argv) == 1 and re.fullmatch(r"(puppet_infrastructure::)?[a-z][a-z0-9_]*", argv[0]):
        report = pregate_class(argv[0].removeprefix("puppet_infrastructure::"))
    else:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    print_report(report, as_json)
    return {"CLEAN": 0, "FINDINGS": 1, "ERROR": 2}[report.status]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
