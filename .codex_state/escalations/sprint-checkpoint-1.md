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

## Decisions needed from HQ
1. **Sweep result.** Accept 8/31 as the gate-v2-verified count, and the routing in the reconciliation list:
   A (3, records only) and B (13, restore baseline comments/layout keeping only syntax translations) as
   advisor tier; C (4) and D (3) through the normal loop after the sprint (ruling 8). rsyslog_client (57
   servers, missing `forward_auth_log`) is the highest-impact item.
2. **Unguarded execs at the baseline** (pregate, confirmed in the baseline text): `user_base`
   (`${ecryptdir}/wrapped-passphrase`), `user_lock`, `linux_policies_user`, `mysql_server`. Gate v2 holds
   them RED by design (run 2 re-executes). user_base is the required base that creates `p8testuser` for
   the user* defines, so the whole user family is blocked behind it. Options: (a) authorize adding the
   obvious guard as an upstream-defect fix (behaviour-preserving in intent, not in letter); (b) a
   gate-v2 exemption list with evidence; (c) block them category 2 until upstream fixes.
3. **puppet_boot_run marker** for its one-line ruled divergence: `[from: release-0.9.10]` would be false;
   `[reimplemented: ...]` overstates it. Proposal: `Done [from: release-0.9.10; upstream defect fixed: ensure dropped]`.
4. **Master snapshot.** puppet-lint 4.3.0 was installed in the master's agent ruby (ruling 4 amended) —
   the master needs a new snapshot; my settings deny master snapshots, so HQ takes it.
5. **Old node snapshot** P8NODE_BASELINE_GREEN: kept as ruled; delete or keep? (Deletion is HQ's.)
6. **filesystem_sec default branch** cannot compile on Puppet 8 (`Cannot reassign variable
   '$restricted_group'`, upstream reassigns a parameter). Upstream-defect ruling for the CTO batch?
7. **Reviewer agent type.** This session loaded the `reviewer` definition before v2 existed, so the sweep
   ran a general-purpose agent prompted with reviewer.md's verbatim body. A fresh session uses
   `subagent_type: reviewer` directly. No action unless HQ prefers otherwise.

## Facts HQ should know
- Two engine defects were found by the sweep and fixed in place (apt lists frozen by the v2 snapshot;
  Resource-API events not counted); the affected classes were re-reviewed. Earlier verdicts stand.
- One process slip (31b8282 committed with unrelated work in the tree) and one 6a incident (a catalog with
  an empty Passwd_common echoed to the advisor terminal) are recorded in the sprint file and
  DESIGN_DECISIONS; neither exposed passwd content.
- Next after the ruling: 3.2 orientation packet + record_green.sh, 3.3, 3.4, 3.5, then 4.1–4.3 → checkpoint 2.
