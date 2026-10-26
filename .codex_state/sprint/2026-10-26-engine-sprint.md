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

HQ amendment (31b8282): laptop is a production Puppet 5 node — no ruby/Puppet 8/gems there; parser
validate + puppet-lint run on puppet8master; puppet-lint installed by the master-fixtures script
(created in 2.1 for puppet-lint, extended in 4.1 for extra_files/PKI/Hiera); pregate prints versions.
Baseline cf477c6 confirmed.

Process slip (recorded, not repaired): commit 31b8282 was made while the uncommitted 3.1 files were in
the worktree (it staged only its own two files). Rule 2 forbids that; no force-push to undo it. Out-of-
band commits from now on stash unrelated work first.

| step | status | commit | measure | open issues |
|---|---|---|---|---|
| 0a decisions entry for all rulings | done | c875425 | entry appended, supersessions marked | — |
| 0b pin 5 Puppetfile lines + export | done | 7e7a338 | 5 lines pinned (resolv_conf 8.0.1, stdlib 9.7.0, resource_api 1.1.0, puppetserver_gem 1.1.1, sudo 9.0.2); r10k re-run; `puppet module list` diff before/after = none, 0 invalid (r10k purged puppet_infrastructure as documented, redeployed at once by the harness rsync+mv); export at `.codex_state/lab/Puppetfile`, `export_puppetfile.py --verify` OK; 5 pytest pass | master backup `Puppetfile.bak.<ts>` left on master |
| 0c puppet_boot_run escalation | done | b95f8a9 | `escalations/puppet_boot_run.md` with unit template, script, 4ae2e35 message; intent check: no conflict (message = make boot run work on 22.04; ordering+provider serve it, `ensure` does not) → proceed, no HQ stop | marker for the one-line divergence → checkpoint 1 question |
| 0d baseline bump → release-0.9.10 + re-annotation | done | 76f347f | pin `baseline.env` (cf477c6) read by `tools/baseline.py`; `reannotate_baseline.py --apply`: 15 reannotated, docker_container kept (manifest differs); re-run = 0 changes; self-check: only marker text changed; CLAUDE.md, reviewer.md, wrapper, generator header, UPSTREAM_BASELINE.md and the (off-repo) runbook now name release-0.9.10; `~/.local/bin/codex_migrate_class` is now a symlink to the tracked wrapper; 15 pytest pass | branch moved → `escalations/baseline-0.9.10-branch-moved.md`; filesystem_yum re-annotated mechanically although its provenance is known-false (D.3) — the 1.5 sweep owns that |
| 0e .gitignore replaces info/exclude; diagnosis committed | done | fe986ad | `.gitignore` ignores logs/, necessary_modules.txt, `__pycache__`, `*.bak`; `.codex_state/` line removed from `.git/info/exclude` (local, per-clone); `git status` shows only intended files; passwd list reduced to a count (fleet_class_usage.md:10, diagnosis E.1 user_sysmon row), production passwd_* names grep = 0; wrapper/SKILL no longer say `git add -f` | — |
| 3.1 tier-0 revert + 2nd NIC + v2 snapshot | done | 5ed7e89 | GRUB cause confirmed by console screenshots of the OLD baseline: GRUB 2.12 menu 'executed automatically in 26s' at +8 s, '4s' at +30 s, kernel at ~+34 s, SSH at 46.2 s. Node changes: GRUB_RECORDFAIL_TIMEOUT=2 + update-grub (grub.cfg recordfail branch `timeout=2`), apt-daily.timer/apt-daily-upgrade.timer/unattended-upgrades.service disabled, clean shutdown, host `vboxnet0` created (192.168.56.1/24, DHCP off), NIC2 hostonly vboxnet0 (guest `enp0s8`, DOWN, unconfigured), offline snapshot `P8NODE_BASELINE_GREEN_v2` (child of the old one; old kept). revert_node.sh: node hard poweroff, v2 snapshot, post-restore snapshot-name check, `REVERT_METRICS` line. revert_s: 31.3 cold / 29.4 / 22.4 warm (was ~120 nominal). 6 pytest stub tests pass (master only ever started; never powered off/restored); shellcheck 0.11.0 clean (SC2029 annotated: intended client-side expansion) | old snapshot P8NODE_BASELINE_GREEN kept until checkpoint 1; host interface vboxnet0 now exists on the laptop (a production Puppet 5 node — its agent could in principle manage it) |
| 1.1 run-2 rc 0, exec/removed fail, timeouts | done | e5c33f8 | REAL LAB: `test_class.sh --fixture unguarded_exec` → RED (run 2: `Exec[p8test unguarded exec]/returns: executed successfully (corrective)`; gate v1 would have passed: no regex match, rc 2 accepted); control `--fixture guarded_exec` → GREEN; node reverted after. Harness: `timeout -k 15 ${AGENT_TIMEOUT_SECONDS:-600}` per agent run, run 2 must exit 0, run-2 regex adds `executed successfully` and `removed`, exit code reported per run. Wrapper: `timeout -k 30 ${CODEX_TIMEOUT_SECONDS:-1800}` around `codex exec`, `CODEX_TIMEOUT` marker, rc propagated. SKILL ad-hoc `codex exec` now `timeout -k 30 900 ... </dev/null`. 11 new stub tests (8 gate, 3 wrapper), 32 total pass; shellcheck clean on test_class.sh and wrapper | timeout kills the local ssh only; a remote agent run may continue until the next revert (acceptable: revert-first, 1.2) |
| 1.2 revert-first (wrapper + reviewer) | done | this commit | REAL LAB, reviewer's prescribed command `test_class.sh --revert-first puppet_infrastructure::puppet_backup`: revert 23.6 s, `RUN1_EVENTS: 9 catalog, 116 pluginsync` (7 filesystem_base dirs/files + backup-puppet.sh + Cron[cron_puppet_backup] created), run 2 GREEN. Wrapper reverts before `codex exec` (REVERT_FAILED → exit 3, Codex not started); reviewer.md check 5 uses --revert-first and fails `RUN1_EVENTS: 0` unless justified; SKILL step 3 delegates revert to the wrapper. Run-1 count excludes pluginsync (first attempt counted 125 incl. pluginsync — fixed + regression test). 7 new stub tests, 39 total; shellcheck clean | baseline's plugin cache is empty: every revert re-syncs 116 plugin files (seconds, not minutes) — candidate for the post-sprint snapshot refresh |
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
