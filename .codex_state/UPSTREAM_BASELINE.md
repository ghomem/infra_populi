# Upstream Baseline & Sync Discipline

## Declared baseline
infra_populi is migrated from **puppet_infrastructure `release-0.9.8`**
(identical to `release-0.9.9` for `manifests/` — 0.9.9 added no manifest
changes over 0.9.8). This is the *reconciliation target* for Phase 1.

Old repo: git@github.com:ghomem/puppet_infrastructure.git
- release-0.9.6  2024-11-12
- release-0.9.7  2025-04-10
- release-0.9.8  2026-05-21  <-- DECLARED BASELINE
- release-0.9.9  2026-06-30  (== 0.9.8 for manifests/)

## Why 0.9.8 (and why the history was confusing)
Migration commits in infra_populi span 2026-02-17 .. 2026-04-29.
During that window the latest *tagged* release was 0.9.7 (0.9.8 was cut
~3 weeks after the last migration commit). BUT classes were migrated from
the old repo's *live development HEAD* on each day, not from a tag — so the
new repo is a TEMPORAL PATCHWORK spanning the 0.9.7 -> 0.9.8 dev period.

Evidence: the logging subsystem was rewritten during that window.
- 0.9.7 had: logfiles.pp, timezone_syslog.pp
- 0.9.8 has: rsyslog_base/client/server/apparmor_exception (+ templates)
- infra_populi already contains the NEW rsyslog_* names -> proves later
  migrations pulled 0.9.8-era (unreleased-at-the-time) content.

0.9.8 is therefore the first stable tag that the newest work aligns with,
and is chosen as the single honest baseline going forward.

## One-time reconciliation (scheduled: END of Phase 1, single pass)
Bring every already-migrated class up to its 0.9.8 CONTENT (syntax already
handled by migration). Do it once, at Phase 1 completion, so diffs show only
content (Axis B), not syntax (Axis A). Re-GREEN each reconciled class via the
harness.

Rough triage (crude line-diff vs 0.9.8, mixes syntax+content — INDICATIVE ONLY,
verify properly during the pass):
- Content-identical (done):        dns_client, caching_nameserver,
                                   nginx_default_removal, backup_rsnapshot_pre,
                                   filesystem_lib64
- Likely syntax-only (quick check): firewall_addon_web, firewall_ipv6_drop,
                                   puppet_reports_cleanup, firewall_ipv6_drop_policy,
                                   firewall_addon_caching_nameserver, firewall_addon_xrdp
- Likely CONTENT drift (review):    firewall, sysmon_puppet_cert_status,
                                   rsyslog_client, rsyslog_base   <-- rsyslog highest
- All migrated classes still exist in 0.9.8 (no upstream deletions among them).

## KNOWN INCONSISTENCY to resolve during reconciliation
`.codex_state/migrated_classes.txt` "Done" markers do NOT fully match the
actual `P8: migrate` git commits. Cross-check `git log --oneline | grep
"P8: migrate"` against the Done markers and correct the tracker as part of
(or just before) the reconciliation pass.

## Ongoing anchor discipline (STARTS NOW, all future migrations)
Every future class migration is done from the DECLARED BASELINE (0.9.8).
When a class is migrated, its migrated_classes.txt line MUST be annotated:
    <class> Done [from: release-0.9.8]
Do NOT retroactively annotate existing entries (true per-class anchors are
unknown — that is the accepted patchwork).

### Ruling B (HQ, forward-only annotation) -- authoritative
The 15 historical migrations (git log: 15x "P8: migrate", all pre-dating the
release-0.9.8 tag of 2026-05-21, migrated from live dev HEAD) STAY as plain
`Done`. They are NOT stamped [from: release-0.9.8], because that provenance
would be factually false. Meaning of the two marker forms going forward:
  - plain `Done`                    = migrated, NOT yet reconciled to 0.9.8
                                      (this is the reconciliation backlog)
  - `Done [from: release-0.9.8]`    = migrated AND confirmed at 0.9.8 content
A historical class EARNS the [from: release-0.9.8] annotation only after it is
reconciled to 0.9.8 during the end-of-Phase-1 reconciliation pass. New forward
migrations get the annotation immediately (they are done from 0.9.8 by rule).
Note: migrated_classes.txt uses two interchangeable marker positions --
`X Done` (later Codex entries) and `Done X` (early hand entries); both mean
migrated. Do NOT normalize the format (cosmetic-only; risks editing errors).

## Future upstream catch-up policy
Do NOT chase new old-repo releases (0.9.10+) mid-phase. Note them, and fold
into a deliberate catch-up at a PHASE BOUNDARY, always diffing
`<current_baseline>..<new_release>` so only content changes appear.

## Note on stale reports
`.codex_state/upstream_sync/*.diff` were generated against 0.9.8 but reflect
the pre-analysis (patchwork) confusion. Treat as SUPERSEDED by this document;
regenerate against the declared baseline when reconciliation begins.
