# sysmon_fs_health: authoring notes (the comments of .codex_state/checks/sysmon_fs_health.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sysmon_fs_health (define; harness title sysmon_fs_health = the volume name;
# required_base filesystem_base; required_external sudo). Fixture (params, never committed): basedir
# /var/tmp/p8test-fs-health, size_threshold 8 (KB), nfiles 3. bindir = /opt/puppet-infrastructure/bin (lab Hiera).
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1); the CRITICAL side on an empty tree and
# the sudo rule in use (the nagios account, which production's monitoring base creates, made here only if absent).
# Correction round 1, 2026-11-21 (review 20261121T061222Z, purpose): read errors injected under the tree (a loop-mounted
# ext4 image remapped through a device-mapper error target: one file's blocks, then the subdirectory's block); nobody
# refused by sudo next to nagios. Prototyped on the node.
```
