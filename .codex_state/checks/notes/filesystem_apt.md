# filesystem_apt: authoring notes (the comments of .codex_state/checks/filesystem_apt.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::filesystem_apt (class; node ubuntu; Ubuntu 24.04). Fixture: defaults
# (server_mode true, relevant_updates_method 2, relevant_updates_no_kernel false; no Hiera prio/hour/minute keys, so
# High at 00:00). The class installs update helper scripts, openscap-scanner (24.04) and a daily cron that keeps the
# list of updates of priority >= High in /var/lib/apt-check-updates/list. Probes read the node's own files; mutating
# checks run the helpers as an operator or the cron would, against the Ubuntu archive and Canonical's OVAL data.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the desktop mode, relevant_updates_method 0, no_kernel and a custom
# surface list are checks in the variant runs `desktop`, `method0` and `custom` (composites pass them); the Hiera
# keys name what is missing.
# 2026-11-23 correction round 1 (review FAIL 42b65dd, purpose): relevant_updates_no_kernel's effect, the daily list
# leaving out kernel packages, was checked only as the rendered NO_KERNEL line; the custom variant now runs the job and,
# for contrast, a copy without --no-kernel (check the-no-kernel-job-lists-no-kernel-package). Its first run (20261123T160957Z)
# left it not run behind the custom list's finding; it moved to its own variant `nokernel` (relevant_updates_no_kernel only).
# Its second run (20261123T162415Z) showed the copy without --no-kernel listing no kernel package either: measured the same
# day, the reverted node has 9 kernel-related packages upgradable, but Canonical's OVAL data marks none of them at any
# priority (68 packages listed at Negligible, none kernel-related), so real data cannot show the filter. The check now
# traces the installed job (it hands --no-kernel to the tool) and runs the installed tool on a p8test results fixture.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2); the set-level uncovered list moved into it.
  # 2026-11-19 correction round 1 (review 20261119T025241Z): the list could be empty and still pass; the reverted node
  # has pending upgrades, so the job's list must now be non-empty with every listed package installed below its
  # candidate, and the next check installs the job's own list (the job, list and install chain end to end).
  # 2026-11-18 purpose correction (review 20261118T121418Z): apt-update-relevant.sh (manifest lines 183-191), the
  # script that installs the updates on the daily list, was missing from the purpose and the checks; it is in both now.
  # 2026-11-18 derivation correction (after filesystem_yum's review 20261118T131226Z, same pattern): the run checks
  # computed their evidence (versions after the run, the pending-upgrade count) inside the action; the actions now
  # record only what they changed and what the wrapper reported, and each effect reads the node's state itself.
  # 2026-11-18 purpose correction (review 20261118T122159Z): the surface, kernel and full update scripts were checked
  # as installed files only; the next three checks run each one (the full update last, as it upgrades everything).
  # 2026-11-25 authoring correction (after run 20261125T224123Z-author, local change #24): the probe strips SURFACE=
  # with sed, but the expectation kept it, so the check could not pass; the node rendered "vim less", as the fixed
  # code makes it. The expectation now matches the probe's output.
```

2026-11-28 (the re-verification after the rename, results/filesystem_apt/20261128T035659Z-author), authoring correction
round 1: the-daily-job-lists-relevant-updates assumed "the reverted node has pending security updates". P8NODE_BASELINE_GREEN_v6
(option A, ruled 2026-11-26) is up to date, so the High list was empty (job rc 0) and the check and the one after it
failed. Measured on a fresh v6 node: with wget and libexpat1 at their noble release versions the job lists both at
Medium and neither at High (Canonical rates their fixes Medium); five more candidates (libtiff6, libarchive13t64,
libssh-4, libsqlite3-0; libgs10 would not downgrade) gave no High entry either. The set now makes the two packages
pending itself: the-high-job-leaves-medium-updates-out (a run at High, the cron's default, lists neither although both
are behind) and the-daily-job-lists-relevant-updates at Medium (both listed, each behind its candidate); the script that
installs the job's list follows unchanged. The dist-upgrade check passed on v6 (option A lifted that item).
