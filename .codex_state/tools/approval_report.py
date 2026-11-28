#!/usr/bin/env python3
"""The behaviour approval report (HQ 2026-11-18 ruling C3; HQ after batch 20, item 5): one row per done class (purpose,
what the checks prove, the open rows, stand-ins, findings, local changes), generated from the recorded state only: the
plan, the tracker, git's migrations, the check sets (.codex_state/checks), their latest results and reviews,
rules/local_changes.md and the escalations. It is a derived file (P2): regenerate it, never edit it.

  approval_report.py            write .codex_state/approval_report.md
  approval_report.py --check    exit 1 when the written report differs from a fresh render (nothing written)
  approval_report.py --stdout   print the render instead of writing it
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS.parent))
sys.path.insert(1, str(TOOLS))
import gen_migration_order as generator  # noqa: E402
import phase3  # noqa: E402
import status  # noqa: E402
import yaml  # noqa: E402

REPO = TOOLS.parents[1]
OUT = REPO / ".codex_state" / "approval_report.md"
LOCAL_CHANGES = REPO / ".codex_state" / "rules" / "local_changes.md"
ESCALATIONS = REPO / ".codex_state" / "escalations"
# HQ after batch 20, item 6: the stand-ins to lift with small lab additions, and the two that stay and go to Salatiel
# for explicit acceptance; any other stand-in is in neither list
LIFT_STANDINS = {
    "user_lock": "the master-role node's hashman database",
    "mount_shares_desktop": "the desktop login",
    "node_base_desktop": "a harness mode that tolerates a running agent",
    "node_base_domain_desktop": "a harness mode that tolerates a running agent",
}
ACCEPTANCE_STANDINS = {"user_samba", "user_sysmon", "letsencrypt_certificate", "openvpn_server", "network_vpn"}
# What a real lift would need, said with the acceptance (HQ 2026-11-23 rulings 3 and 4; documentation list rows 8, 9).
ACCEPTANCE_NOTES = {
    "letsencrypt_certificate": "a real lift needs a sandbox DNS zone and an API token against Let's Encrypt staging "
                               "(documentation list, cutover row 8)",
    "openvpn_server": "the first VPN gateway is migrated as a recreated test gateway before any live one "
                      "(documentation list, cutover row 9)",
    "network_vpn": "the first VPN gateway is migrated as a recreated test gateway before any live one "
                   "(documentation list, cutover row 9)",
}


DECISIONS = REPO / ".codex_state" / "rules" / "salatiel_decisions.yml"
USAGE = REPO / ".codex_state" / "diagnosis" / "fleet_variant_usage.md"
# HQ 2026-11-27 item 6, the corrected production count: a conditional include counts only where it is turned on, and a
# class on one OS family's branch says so. One place: (how node_base includes the class, the switch, its default).
SWITCHED = {"firewall_secure_extra": ("firewall_secure_extra", False), "puppet_boot_run": ("run_puppet_on_boot", False),
            "filesystem_sec": ("filesystem_security", True)}
REDHAT_ONLY = {"extra_packages_el", "filesystem_yum"}  # node_base's / packages_base's RedHat branch
DEBIAN_BRANCH = {"filesystem_apt", "filesystem_lib64"}  # node_base's non-RedHat branch
# Why the verified count of an earlier report differed (HQ 2026-11-27 item 6: name the class and why).
VERIFIED_NOTES = ["user_lock was shown unverified until 2026-11-27 (89 of 90): a later `P8: migrate` commit "
                  "(3731d97) changed only the tracker, and the order generator took it as the class's migration while "
                  "the reviewer, by HQ 2026-11-23 ruling 1, judged the one that changed the class (a795d98, PASS); the "
                  "generator now applies the same ruling"]


def decisions() -> dict:
    """Salatiel's recorded decisions, merged over every dated block (rules/salatiel_decisions.yml)."""
    out = {"findings": {}, "gaps": {}, "not_accepted": {}, "standins": {}}
    for block in (yaml.safe_load(DECISIONS.read_text()) if DECISIONS.is_file() else []) or []:
        for c in block.get("findings_accepted_as_known") or []:
            out["findings"][c] = block["date"]
        for c, params in (block.get("accepted_gaps") or {}).items():
            out["gaps"].setdefault(c, {}).update({p: block["date"] for p in params})
        for c, why in (block.get("accepted_gaps_not_accepted") or {}).items():
            out["not_accepted"].setdefault(c, {}).update(why)
        for c, note in (block.get("standins_accepted") or {}).items():
            out["standins"][c] = (block["date"], note)
    return out


def switch_usage(param: str) -> int:
    for line in (USAGE.read_text().splitlines() if USAGE.is_file() else []):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) == 5 and cells[1] == "node_base" and cells[2] == param:
            return int(cells[3]) if cells[3].isdigit() else 0
    return 0


def production(cls: str, raw: int) -> str:
    """Production machines under the corrected rule, with what limits the number."""
    if cls in REDHAT_ONLY:
        return "RedHat-only (the fleet's RHEL servers are not counted by name)"
    if cls in DEBIAN_BRANCH:
        return f"at most {raw} (the non-RedHat branch; the RHEL servers are not subtracted)"
    if cls in SWITCHED:
        param, default = SWITCHED[cls]
        n = switch_usage(param)
        if default:
            return f"{raw} (node_base's {param} defaults on" + (f" and is set on {n} node statement(s))" if n else
                                                                  " and no node statement sets it)")
        if not n:
            return f"0 (only where node_base's {param} is turned on; it defaults off and no node statement sets it)"
        return f"at most {n} (only where node_base's {param} is turned on; it defaults off and {n} node statement(s) set it)"
    return str(raw)


def standin_plan(cls: str) -> str:
    decided = decisions()["standins"].get(cls)
    if decided:
        return f"{decided[1]} (Salatiel, {decided[0]})"
    if cls in ACCEPTANCE_NOTES:
        return f"stays; for Salatiel's explicit acceptance: {ACCEPTANCE_NOTES[cls]} (HQ 2026-11-23)"
    if cls in LIFT_STANDINS:
        return f"to be lifted: {LIFT_STANDINS[cls]} (HQ after batch 20, item 6)"
    if cls in ACCEPTANCE_STANDINS:
        return "stays; for Salatiel's explicit acceptance (HQ after batch 20, item 6)"
    return "not in HQ's lift list (item 6): stays as it is, for Salatiel's attention"


def one_line(text) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def local_changes(path: Path = LOCAL_CHANGES) -> dict[str, list[tuple[str, str]]]:
    """class -> [(number, the change's first sentence)] from the table rows whose class cell is that class."""
    out: dict[str, list[tuple[str, str]]] = {}
    for line in path.read_text().splitlines() if path.is_file() else []:
        cells = [c.strip() for c in line.split("|")]
        if len(cells) < 4 or not re.fullmatch(r"\d+", cells[1]):
            continue
        change = cells[3]
        first = re.split(r"(?<=[.;])\s", change, maxsplit=1)[0]
        out.setdefault(cells[2], []).append((cells[1], first))
    return out


def set_of(cls: str) -> dict:
    """The class's set as the engine reads it (the public template rendered with the lab's values), or {}."""
    if not phase3.set_path(cls).is_file():
        return {}
    try:
        data, _ = phase3.load_set(cls)
    except (SystemExit, yaml.YAMLError):
        data = None
    return data if isinstance(data, dict) else {}


def class_row(cls: str, plan_row, tracker_entry, prod: int, standin: tuple[str, str] | None,
              changes: list[tuple[str, str]]) -> dict:
    data = set_of(cls)
    state = phase3.behaviour_state(cls)
    proven, open_rows = [], []
    for r in data.get("outcomes") or []:
        if not isinstance(r, dict):
            continue
        if "uncovered" in r:
            u = r["uncovered"] or {}
            open_rows.append({"outcome": one_line(r.get("outcome")), "why": one_line(u.get("why")),
                              "lifted_by": one_line(u.get("lifted_by")),
                              "accepted_gap": list(u.get("accepted_gap") or [])})
        else:
            proven.append({"outcome": one_line(r.get("outcome")), "checks": list(r.get("checks") or [])})
    escalation = ESCALATIONS / f"{cls}.behaviour.md"
    return {
        "class": cls,
        "node": (plan_row.node if plan_row and plan_row.node else "ubuntu"),
        "peer": ((data.get("peer") or {}).get("kind") or ""),
        "prod": prod,
        "purpose": one_line(data.get("purpose")) or one_line((data.get("deferred") or {}).get("why")),
        "behaviour": state["state"],
        "detail": state["detail"],
        "deferred": data.get("deferred"),
        "proven": proven,
        "open": open_rows,
        "standin": standin,
        "finding_file": (f"escalations/{escalation.name}" if state["state"] == "finding" and escalation.is_file()
                         else ""),
        "local_changes": changes,
        "marker": status.marker(tracker_entry),
    }


def collect() -> tuple[list[dict], dict]:
    rows = generator.parse_plan()
    migrations = generator.git_migrations()
    blocked = generator.read_blocked()
    tracker = generator.read_tracker()
    owner_validated = {name for name, row in rows.items() if row.owner_validated}
    retired = generator.retired_classes(tracker, rows, blocked)
    done = sorted(set(migrations) - set(blocked) - owner_validated - set(retired))
    flagged = generator.find_flagged_migrations(migrations)
    verified = [n for n in done if status.verification_state(n, migrations[n], flagged)[0] == status.VERIFIED]
    standins = {c: (f, lifted) for c, f, lifted in status.standins(rows, verified)}
    prod = generator.read_prod_nodes()
    changes = local_changes()
    out = [class_row(c, rows.get(c), tracker.get(c), production(c, prod.get(c, 0)), standins.get(c), changes.get(c, []))
           for c in done]
    meta = {"done": len(done), "verified": len(verified), "owner_validated": sorted(owner_validated),
            "blocked": sorted(blocked), "retired": sorted(retired)}
    return out, meta


def open_escalations() -> list[str]:
    """Escalation files whose first line says OPEN (check sets and behaviour findings awaiting a ruling)."""
    found = []
    for p in sorted(ESCALATIONS.glob("*.md")):
        first = p.read_text().splitlines()[:1]
        if first and "OPEN" in first[0] and not p.name.startswith("batch-"):
            found.append(f"escalations/{p.name}: {first[0].lstrip('# ').strip()}")
    return found


def render(rows: list[dict], meta: dict) -> str:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["behaviour"]] = counts.get(r["behaviour"], 0) + 1
    standins = [r for r in rows if r["standin"]]
    findings = [r for r in rows if r["behaviour"] == "finding"]
    L = ["# Behaviour approval report (generated)", "",
         "Generated by `.codex_state/tools/approval_report.py` from the recorded state (plan, tracker, git, check sets,",
         "their latest results and reviews, rules/local_changes.md, escalations). Do not edit; regenerate.", "",
         "## Summary", "",
         f"- Done classes: {meta['done']} ({meta['verified']} verified by the Phase 1 reviewer). Owner-validated: "
         f"{', '.join(meta['owner_validated']) or 'none'}. Retired: {', '.join(meta['retired']) or 'none'}. "
         f"Blocked: {', '.join(meta['blocked']) or 'none'}.",
         *[f"- Verified count: {n}." for n in VERIFIED_NOTES],
         "- Production machines follow the corrected rule (HQ 2026-11-27 item 6): a conditional include counts only "
         "where it is turned on, and a class on one OS family's branch says so.",
         "- Behaviour (Phase 3): " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) + ".",
         f"- Open rows (outcomes no check probes): {sum(len(r['open']) for r in rows)} in "
         f"{sum(1 for r in rows if r['open'])} classes.",
         f"- Stand-ins: {len(standins)}. Local changes: "
         f"{sum(len(r['local_changes']) for r in rows)} (in {sum(1 for r in rows if r['local_changes'])} classes).",
         ""]
    L += ["## For Salatiel's decision", "", "### Behaviour findings", ""]
    dec = decisions()
    L += [f"- **{r['class']}** — {r['detail']} ({r['finding_file'] or 'no escalation file'})"
          + (f" — *accepted as known (Salatiel, {dec['findings'][r['class']]})*" if r["class"] in dec["findings"] else "")
          for r in findings] or ["- none"]
    L += ["", "### Stand-ins", ""]
    for r in standins:
        fixture, lifted = r["standin"]
        L.append(f"- **{r['class']}** — fixture `{fixture}`; lifted by: {lifted}. *{standin_plan(r['class'])}*")
    if not standins:
        L.append("- none")
    # HQ 2026-11-23 ruling 1c: parameter variants no production node statement sets, for Salatiel's acceptance
    L += ["", "### Accepted gaps (parameter variants production does not use)", ""]
    gaps = [(r["class"], o) for r in rows for o in r["open"] if o.get("accepted_gap")]
    def gap_state(c: str, params: list[str]) -> str:
        known = dec["gaps"].get(c, {})
        if params and all(p in known for p in params):
            return f" — *accepted (Salatiel, {min(known[p] for p in params)})*"
        return " — *new since Salatiel's review: for acceptance*"
    L += [f"- **{c}** — {', '.join(o['accepted_gap'])}: {o['outcome']} — {o['why']}{gap_state(c, o['accepted_gap'])}"
          for c, o in gaps] or ["- none"]
    for c, why in sorted(dec["not_accepted"].items()):
        L += [f"- **{c}** — {', '.join(why)}: not accepted — {'; '.join(why.values())}"]
    L += ["", "### Open escalations", ""]
    L += [f"- {e}" for e in open_escalations()] or ["- none"]
    L += ["", "## One row per class", "",
          "| class | prod | node | behaviour | proven | open | stand-in | finding | local changes |",
          "|---|---:|---|---|---:|---:|---|---|---|"]
    for r in rows:
        L.append(f"| {r['class']} | {r['prod']} | {r['node']}{(' + ' + r['peer']) if r['peer'] else ''} | "
                 f"{r['behaviour']} | {len(r['proven'])} | {len(r['open'])} | "
                 f"{'yes' if r['standin'] else ''} | {'yes' if r['behaviour'] == 'finding' else ''} | "
                 f"{', '.join('#' + n for n, _ in r['local_changes'])} |")
    L += ["", "## Per class", ""]
    for r in rows:
        L += [f"### {r['class']}", "",
              f"- **Purpose:** {r['purpose'] or '(no purpose recorded)'}",
              f"- **Behaviour:** {r['behaviour']}{(' — ' + r['detail']) if r['detail'] else ''}; node "
              f"{r['node']}{(', peer ' + r['peer']) if r['peer'] else ''}; production machines: {r['prod']}.",
              f"- **Tracker:** `{r['marker']}`"]
        if r["deferred"]:
            d = r["deferred"]
            L.append(f"- **Deferred:** needs {d.get('needs')}, lifted by {one_line(d.get('lifted_by'))}")
        if r["proven"]:
            L.append("- **Proven:**")
            L += [f"  - {p['outcome']} (`{'`, `'.join(p['checks'])}`)" for p in r["proven"]]
        if r["open"]:
            L.append("- **Open rows:**")
            L += [f"  - {o['outcome']} — why: {o['why']} — "
                  + (f"accepted gap (production does not use {', '.join(o['accepted_gap'])})" if o.get("accepted_gap")
                     else f"lifted by: {o['lifted_by']}") for o in r["open"]]
        if r["standin"]:
            L.append(f"- **Stand-in:** `{r['standin'][0]}` — lifted by: {r['standin'][1]}. Plan: "
                     f"{standin_plan(r['class'])}")
        if r["behaviour"] == "finding":
            L.append(f"- **Finding:** {r['detail']} ({r['finding_file'] or 'no escalation file'})")
        if r["local_changes"]:
            L.append("- **Local changes:** " + "; ".join(f"#{n}: {c}" for n, c in r["local_changes"]))
        L.append("")
    return "\n".join(L).rstrip("\n") + "\n"


def main(argv: list[str]) -> int:
    if argv not in ([], ["--check"], ["--stdout"]):
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    text = render(*collect())
    if argv == ["--stdout"]:
        sys.stdout.write(text)
        return 0
    if argv == ["--check"]:
        current = OUT.read_text() if OUT.is_file() else ""
        if current != text:
            print(f"APPROVAL REPORT STALE: {OUT.relative_to(REPO)} differs from a fresh render; run approval_report.py",
                  file=sys.stderr)
            return 1
        print("approval report current")
        return 0
    OUT.write_text(text)
    print(f"wrote {OUT.relative_to(REPO)} ({len(rows_of(text))} class rows)")
    return 0


def rows_of(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("### ") and not line.startswith("### Behaviour")
            and not line.startswith("### Stand-ins") and not line.startswith("### Open escalations")
            and not line.startswith("### Accepted gaps")]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
