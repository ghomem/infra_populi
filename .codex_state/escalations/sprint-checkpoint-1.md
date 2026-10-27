# Sprint checkpoint 1 — after 1.5 (2026-10-27). The sprint WAITS here for HQ.

Per-step detail and measures: `.codex_state/sprint/2026-10-26-engine-sprint.md`.

## Done (all committed and pushed)
| step | commit | measure |
|---|---|---|
| 0a rulings → DESIGN_DECISIONS (+ amendment 31b8282) | c875425 | supersessions marked |
| 0b pin 5 Puppetfile lines; export | 7e7a338 | module list unchanged, 0 invalid |
| 0c puppet_boot_run escalation | b95f8a9 | no intent conflict with 4ae2e35 |
| 0d baseline → release-0.9.10 = cf477c6; re-annotate | 76f347f | 15 re-annotated by byte identity; docker_container kept |
| 0e explicit .gitignore; diagnosis committed | fe986ad | passwd names → count |
| 3.1 tier-0 revert, NIC2, P8NODE_BASELINE_GREEN_v2 | 5ed7e89 (+fix 6947198) | revert ~120 s → 22–31 s; ~34 s median with the apt refresh |
| 1.1 gate v2 + timeouts | e5c33f8 (+fix 90a8a44) | unguarded-exec fixture RED on the real lab; guarded control GREEN |
| 1.2 revert-first | 7d1c4d3 | reviewer run 1 shows creations (puppet_backup: 9 catalog events) |
| 1.3 coverage | 9efbad7 | target resources listed from the node; 0 → RED |
| 2.1 pregate | 889e617 | 87 classes in 264 s; versions printed; hook live-tested |
| 2.2 compile-only + composites | b90eab3 | standing check; measured node_base/ntp, filesystem_yum duplicate on RedHat, filesystem_sec default branch |
| 1.4 reviewer v2 | 1d69607 | the 6 predicted FAILs fail for the documented reasons |
| 1.5 sweep | this commit | **8 PASS / 23 FAIL**; list: `escalations/2026-10-27-done-class-reconciliation.md` |

## Decisions — RULED (HQ 2026-10-27; rewritten per the "production facts" ruling 8 so no session re-asks)
1. Sweep accepted (8 verified); derived "verified (gate v2)" state in status.py; groups A/B advisor-direct (one-off,
   DONE: 16/16 PASS → 24 verified); C/D/E normal loop, first in the queue: rsyslog_base → rsyslog_client →
   docker_container → filesystem_yum (→ backup_rsnapshot_pre); firewall and sysmon_puppet_cert_status sink.
2. Unguarded execs at the baseline: fixed per class with a guard testing the command's post-condition, marker
   `upstream defect fixed` — fixed in infra_populi only, no escalation (production-facts ruling 2); list in
   `.codex_state/upstream_defects.md`. mysql_server: 874f854 moves the exec unguarded into mariadb_server.
3. Marker approved and generalised: `[from: <ref>; upstream defect fixed: <short>]` (+ `; mock-apply: <short>`).
4. Master snapshot: Salatiel takes it at checkpoint 2.
5. Old node snapshot P8NODE_BASELINE_GREEN kept through checkpoint 2.
6. filesystem_sec: fixed locally (applied 929062b, reviewer PASS); no upstream escalation.
7. Reviewer: a fresh session uses `subagent_type: reviewer` (the sweep used general-purpose agents with reviewer.md).

## Facts HQ should know
- Two engine defects were found by the sweep and fixed in place (apt lists frozen by the v2 snapshot;
  Resource-API events not counted); the affected classes were re-reviewed. Earlier verdicts stand.
- One process slip (31b8282 committed with unrelated work in the tree) and one 6a incident (a catalog with
  an empty Passwd_common echoed to the advisor terminal) are recorded in the sprint file and
  DESIGN_DECISIONS; neither exposed passwd content.
- Next after the ruling: 3.2 orientation packet + record_green.sh, 3.3, 3.4, 3.5, then 4.1–4.3 → checkpoint 2.
