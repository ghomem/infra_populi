# Pre-migration hazard checklist — SINGLE SOURCE (step 3.5)
<!-- Consumed by CLAUDE.md (@-import), the migrate-next skill (step 2) and the Codex prompt (the wrapper
appends this file to the runbook). Edit only here. Items 1-8: CLAUDE.md before 2026-10-27; items 9-13:
diagnosis G, approved by HQ ruling 12 (2026-10-26). -->

Run on EVERY class before the generation path starts — the plan cannot predict these.
`.codex_state/tools/pregate.sh <class>` mechanises items 1, 2, 5, 6, 8 and 9 (plus parse, lint, templates);
the rest are read from the manifest, its templates and the plan.

1. External custom types from modules whose Puppet-8/OpenVox compatibility is unverified. Check the module's
   declared Puppet compatibility on the Forge BEFORE installing: three blockers so far (puppet-network /
   puppet-filemapper, sysctl, leinaddm-htpasswd) declared Puppet 3.x-7.x and called APIs removed in Puppet 8
   (e.g. `Puppet.newtype`) — treat such a module as a category-1 candidate, do not install hopefully.
2. Anything altering node→master connectivity: OUTPUT chain policy/purge, default-drop, NEW-outbound
   to master:8140.
3. Class comments claiming a dependency or base — verify against code.
4. Undeclared runtime prerequisites: an absolute path consumed by file/cron/template/exec whose parent
   dir the manifest never declares.
5. OS-specific EXECUTION (exec/dnf/rpm/subscription-manager) without an OS guard. Note the guard
   inversion: an `unless`/`onlyif` whose command doesn't exist makes Puppet RUN the command.
6. stdlib-4-era functions removed in stdlib 9 (`validate_*`, `is_*`, ...).
7. Variables read from another class's scope with no local assignment/param/lookup (legacy dynamic
   scoping — compile failure on Puppet 8, "Unknown variable"). Repository-standard fix: `lookup()` of the
   matching Hiera key (found in user_samba's `$localdir`); the plan's risks column notes known carriers.
8. Baseline drift: local manifest (or a template/file it uses) differs from release-0.9.10
   (`.codex_state/tools/baseline.py drift <class>`). Baseline-sync it verbatim in its own
   `P8: baseline-sync <class> to release-0.9.10` commit first; escalate only if a synced template
   is shared with an already-Done class or the baseline needs newer dep content.
9. Exec idempotency: every `exec` needs `unless`/`onlyif`/`creates`/`refreshonly`, and the guard must be
   runnable on the node. Gate v2 holds an unguarded exec RED by design; one that is unguarded AT THE
   BASELINE is an upstream defect — escalate per class (HQ ck1 ruling 2), never add a guard silently.
10. Define params fixture present: `test_class.sh --render-only <class>` must succeed before any agent
    run (`classify_path.py` reports a missing one as context-gap).
11. Shared template/file: list every `template()`/`epp()`/`source =>` the class uses and whether another
    class consumes it (`git grep` in the baseline); a change to a shared one is beyond-target.
12. Package/service side effects on the node: a class that installs packages or restarts services
    (ssh, nginx, mysql, networking) must not cut the harness's own SSH path — say how it stays alive.
13. Runtime-baseline drift of the node itself (apt lists, timers): the revert refreshes apt lists; anything
    else a class depends on that is not in P8NODE_BASELINE_GREEN_v2 is a fixture to declare, not to assume.

Also known (each cost a cycle):
- `internal_deps` in migration_plan.md is an Ubuntu-node projection, not universal (see the plan header).
- `r10k --force` purges the `puppet_infrastructure` module (r10k owns the moduledir the harness deploys into).
  The next harness run redeploys it; anything needing a catalog before that fails with the module missing.
