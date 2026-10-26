# Baseline: `release-0.9.10` is a moving branch — pinned to cf477c6 (decision needed: confirm)

Raised 2026-10-26 during sprint step 0d. Escalated by file; the sprint continues on the pin below.

## Evidence
- `release-0.9.10` exists upstream only as a branch (`origin/release-0.9.10`); there is no `0.9.10` tag
  (tags stop at 0.9.9).
- The ruling-1 condition was confirmed against the local `origin/release-0.9.10` = **cf477c6**
  (2026-09-09 23:22 +0200, Gustavo Homem, "update release number on metadata"; metadata 0.9.10;
  90 manifests). Production "runs 0.9.10 (deployed 2026-09-09)" per the 2026-09-30 inspection.
- `git fetch --dry-run` today: `cf477c6..874f854 release-0.9.10 -> origin/release-0.9.10`. 874f854 is
  "Merge pull request #123 from ghomem/issue-122-review-mysql-support" (2026-10-06), adding
  `manifests/mariadb_server.pp`, `manifests/mysql_db.pp`, rewriting `manifests/mysql_server.pp`
  (+ templates/mysql/*, node-examples). 92 manifests at that commit.
- Ruling 1: "The mysql rewrite stays out until released (CTO decision 5)"; Done-means: "the 90-class
  universe at baseline release-0.9.10".

## Advisor decision (applied)
The baseline is the commit, not the branch: `.codex_state/baseline.env` pins
`BASELINE_COMMIT=cf477c638486c169a07ce1110c94424c301471b4`. Every tool reads it via
`.codex_state/tools/baseline.py`. This matches the confirmed ruling, the 90-class universe and the
"mysql stays out" clause. The local upstream ref was NOT fast-forwarded.

## Questions for HQ / CTO
1. Confirm cf477c6 as the baseline (recommended), or name another commit.
2. Is the Issue #122 merge into the release-0.9.10 branch a "release" in the sense of CTO decision 5?
   If yes, the bump is a ruling naming the new commit; mysql_server then changes content and two
   classes join the universe (92).
3. Upstream may want a `0.9.10` tag on the deployed commit so the release is immutable.
