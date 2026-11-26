# puppet_boot_run: authoring notes (the comments of .codex_state/checks/puppet_boot_run.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::puppet_boot_run (class, no parameters: no params file; required_base
# filesystem_base). Migrated with HQ ruling 8's upstream-defect fix (`ensure => running` dropped from the oneshot unit,
# upstream_defects.md). The class installs puppet_boot_run.sh and a oneshot unit wanted by multi-user.target, so a boot
# makes one agent run.
# 2026-11-20 (backfill batch 6): first set. A run does not reboot the node, so the exercise starts the unit as the boot
# does (`systemctl start`), once with another agent run's lockfile present (the script must skip and exit 0 without
# competing) and once without (the unit's script makes the agent run). That agent run is the class's own behaviour,
# not a probe's: the catalog is the one the harness applied, whose second run was clean.
# Correction round 1, 2026-11-20 (review 20261120T123521Z, purpose gap): the lock wait's 120 s bound is exercised
# (a lock held 150 s), and the 900 s time limit is an uncovered row with its evidence. The same review reproduced the
# finding that the lock wait never waits (lsof given three files exits 1 unless all three are held).
# Local change #13, 2026-11-20: the wait uses lsof -t. Authoring error in the first run after it (20261120T124321Z):
# script-and-unit-installed still expected the baseline script's sha256; it now expects the module's file as changed.
```
