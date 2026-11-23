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
    "letsencrypt_certificate": "a lab ACME endpoint",
    "network_vpn": "an extra network card on a gateway node",
    "openvpn_server": "an extra network card on a gateway node",
    "node_base_desktop": "a harness mode that tolerates a running agent",
    "node_base_domain_desktop": "a harness mode that tolerates a running agent",
}
ACCEPTANCE_STANDINS = {"user_samba", "user_sysmon"}


# A lift that needs a design choice or a new VM is escalated in escalations/<file> (2026-11-23).
LIFT_ESCALATIONS = {"letsencrypt_certificate": "letsencrypt_certificate.standin.md",
                    "openvpn_server": "openvpn_server.standin.md", "network_vpn": "openvpn_server.standin.md"}


def standin_plan(cls: str) -> str:
    if cls in LIFT_STANDINS and (ESCALATIONS / LIFT_ESCALATIONS.get(cls, "-")).is_file():
        return (f"lift escalated: {LIFT_STANDINS[cls]} needs a design choice (escalations/{LIFT_ESCALATIONS[cls]}; "
                "HQ after batch 20, item 6)")
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
    path = phase3.phase3_dir() / f"{cls}.yml"
    try:
        data = yaml.safe_load(path.read_bytes()) if path.is_file() else None
    except yaml.YAMLError:
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
                              "lifted_by": one_line(u.get("lifted_by"))})
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
    out = [class_row(c, rows.get(c), tracker.get(c), prod.get(c, 0), standins.get(c), changes.get(c, []))
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
         "- Behaviour (Phase 3): " + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())) + ".",
         f"- Open rows (outcomes no check probes): {sum(len(r['open']) for r in rows)} in "
         f"{sum(1 for r in rows if r['open'])} classes.",
         f"- Stand-ins: {len(standins)}. Local changes: "
         f"{sum(len(r['local_changes']) for r in rows)} (in {sum(1 for r in rows if r['local_changes'])} classes).",
         ""]
    L += ["## For Salatiel's decision", "", "### Behaviour findings", ""]
    L += [f"- **{r['class']}** — {r['detail']} ({r['finding_file'] or 'no escalation file'})" for r in findings] or ["- none"]
    L += ["", "### Stand-ins", ""]
    for r in standins:
        fixture, lifted = r["standin"]
        L.append(f"- **{r['class']}** — fixture `{fixture}`; lifted by: {lifted}. *{standin_plan(r['class'])}*")
    if not standins:
        L.append("- none")
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
            L += [f"  - {o['outcome']} — why: {o['why']} — lifted by: {o['lifted_by']}" for o in r["open"]]
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
            and not line.startswith("### Stand-ins") and not line.startswith("### Open escalations")]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
