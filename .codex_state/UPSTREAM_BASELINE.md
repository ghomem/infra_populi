# Upstream Baseline & Sync Discipline

Current-state document. History of how the baseline was chosen lives in DESIGN_DECISIONS.md
(2026-07-01 baseline entry; 2026-10-26 rulings batch, ruling 1).

## Declared baseline
infra_populi is migrated from **puppet_infrastructure `release-0.9.10`**, pinned to upstream commit
**`cf477c638486c169a07ce1110c94424c301471b4`** (2026-09-09, "update release number on metadata",
metadata.json 0.9.10, 90 manifests). This is the content production runs (deployed 2026-09-09).

Single source: `.codex_state/baseline.env`. Read baseline content only through
`.codex_state/tools/baseline.py` (`show <path>`, `paths <class>`, `drift <class>`).

**Never use the upstream branch name or HEAD.** `origin/release-0.9.10` is a branch, not a tag; on
2026-10-06 it moved to 874f854 by merging the Issue #122 MySQL rewrite (mariadb_server.pp, mysql_db.pp,
rewritten mysql_server.pp), which ruling 1 keeps out until the CTO says it is released. The local
upstream clone also sits on an unmerged branch. A `git fetch` must never change what "baseline" means.

Old repo: git@github.com:ghomem/puppet_infrastructure.git
- release-0.9.8   2026-05-21  previous baseline (tag 0.9.8 == origin/release-0.9.8 for manifests/templates/files)
- release-0.9.9   2026-06-30  (== 0.9.8 for manifests/)
- release-0.9.10  2026-09-09  cf477c6  <-- DECLARED BASELINE (pinned commit)

## What changed 0.9.8 -> 0.9.10 (manifests/templates/files)
Only `docker_container.pp` (+2 lines, `$command`) and `rsyslog_server.pp` (+64 lines) with four rsyslog
templates (listener_simple.conf.epp, logrotate.timer.override.epp, rsyslog-hosts-retention.sh.epp,
rsyslog-hosts.logrotate.epp). Consequences (ruling 1):
- Tracker re-annotation `[from: release-0.9.8]` -> `[from: release-0.9.10]` was applied mechanically by
  `.codex_state/tools/reannotate_baseline.py` to the 15 classes whose manifest+templates+files are
  byte-identical between the two refs.
- docker_container keeps `[from: release-0.9.8]` and is re-migrated under the new gate.
- rsyslog_server migrates from 0.9.10 directly.

## Marker semantics
- plain `Done` = historical migration, NOT reconciled to the baseline (reconciliation backlog).
- `Done [from: release-0.9.10]` = migrated and confirmed at baseline content.
- `Done [from: release-0.9.8]` = migrated at the previous baseline; content changed since (docker_container).
- `Done [reimplemented: ...]` = considered, accepted divergence (2026-07-01).
Marker position (`X Done` / `Done X`) is not normalized. Until the 1.5 re-review sweep is done, all
31 done classes are "done under gate v1" (ruling 2).

## Drift discipline
Before any class is worked: `baseline.py drift <class>`. Drift is resolved by a verbatim baseline-sync
commit `P8: baseline-sync <class> to release-0.9.10` (2026-10-01 ruling, baseline name updated by ruling 1).

## Future upstream catch-up policy
A new upstream release is adopted only by an HQ ruling that names the new pinned commit, diffing
`<current pin>..<new pin>` so only content changes appear, and re-annotating mechanically as above.
