# Engine sprint 2026-10-26 — progress (resume from this file alone)

Brief: execute `.codex_state/escalations/2026-10-26-engine-rulings.md` §13 in order, items as specified
in `.codex_state/diagnosis/2026-10-26-engine-diagnosis.md` §I. Engine work only: no `/migrate-next`, no
class migration (1.5 re-reviews, migrates nothing). Commits `P8: engine: <step> — <what>`, one per step.
Update this file BEFORE each commit (the commit carries its own line as `this commit`; the next step
backfills the hash).

Stops (wait for HQ): after 1.5 (`escalations/sprint-checkpoint-1.md`), after 4.3 (`-2.md`); any master
change beyond ruling 6; any snapshot deletion; a puppet_boot_run intent conflict.

Baseline pin (advisor, step 0d): `release-0.9.10` == upstream commit
`cf477c6` (2026-09-09, metadata 0.9.10, 90 manifests, what production runs). The upstream
`release-0.9.10` is a BRANCH and moved to 874f854 on 2026-10-06 (Issue #122 mysql merge) — tools pin
the commit, not the branch. Escalated: `escalations/baseline-0.9.10-branch-moved.md`.

Step placement not fixed by §13 (advisor): 0d baseline bump and 0e .gitignore go right after step 0
because rule 7 requires every later tool to name release-0.9.10 and rule 2 relies on plain tracking.
Second NIC (ruling 10) rides with 3.1 so one new node snapshot carries both. extra_files/PKI script
(ruling 6) is in 4.1. Fixture rename (ruling 8) is in 1.4.

| step | status | commit | measure | open issues |
|---|---|---|---|---|
| 0a decisions entry for all rulings | done | c875425 | entry appended, supersessions marked | — |
| 0b pin 5 Puppetfile lines + export | done | 7e7a338 | 5 lines pinned (resolv_conf 8.0.1, stdlib 9.7.0, resource_api 1.1.0, puppetserver_gem 1.1.1, sudo 9.0.2); r10k re-run; `puppet module list` diff before/after = none, 0 invalid (r10k purged puppet_infrastructure as documented, redeployed at once by the harness rsync+mv); export at `.codex_state/lab/Puppetfile`, `export_puppetfile.py --verify` OK; 5 pytest pass | master backup `Puppetfile.bak.<ts>` left on master |
| 0c puppet_boot_run escalation | done | b95f8a9 | `escalations/puppet_boot_run.md` with unit template, script, 4ae2e35 message; intent check: no conflict (message = make boot run work on 22.04; ordering+provider serve it, `ensure` does not) → proceed, no HQ stop | marker for the one-line divergence → checkpoint 1 question |
| 0d baseline bump → release-0.9.10 + re-annotation | done | 76f347f | pin `baseline.env` (cf477c6) read by `tools/baseline.py`; `reannotate_baseline.py --apply`: 15 reannotated, docker_container kept (manifest differs); re-run = 0 changes; self-check: only marker text changed; CLAUDE.md, reviewer.md, wrapper, generator header, UPSTREAM_BASELINE.md and the (off-repo) runbook now name release-0.9.10; `~/.local/bin/codex_migrate_class` is now a symlink to the tracked wrapper; 15 pytest pass | branch moved → `escalations/baseline-0.9.10-branch-moved.md`; filesystem_yum re-annotated mechanically although its provenance is known-false (D.3) — the 1.5 sweep owns that |
| 0e .gitignore replaces info/exclude; diagnosis committed | done | this commit | `.gitignore` ignores logs/, necessary_modules.txt, `__pycache__`, `*.bak`; `.codex_state/` line removed from `.git/info/exclude` (local, per-clone); `git status` shows only intended files; passwd list reduced to a count (fleet_class_usage.md:10, diagnosis E.1 user_sysmon row), production passwd_* names grep = 0; wrapper/SKILL no longer say `git add -f` | — |
| 3.1 tier-0 revert + 2nd NIC + v2 snapshot | pending | | revert_s | |
| 1.1 run-2 rc 0, exec/removed fail, timeouts | pending | | known-bad fixture → RED | |
| 1.2 revert-first (wrapper + reviewer) | pending | | reviewer run 1 shows creations | |
| 1.3 coverage signal | pending | | | |
| 2.1 pregate.sh | pending | | | |
| 2.2 compile-only + composites | pending | | | |
| 1.4 reviewer v2 | pending | | | |
| 1.5 re-review sweep (31) → checkpoint 1 | pending | | | |
| 3.2 orientation packet + record_green.sh | pending | | | |
| 3.3 advisor-direct path | pending | | | |
| 3.4 metrics JSONL | pending | | | |
| 3.5 single sources | pending | | | |
| 4.1 plan fixes, pins, syncs/imports, extra_files | pending | | | |
| 4.2 escalation files | pending | | | |
| 4.3 prod_nodes sort key → checkpoint 2 | pending | | | |
