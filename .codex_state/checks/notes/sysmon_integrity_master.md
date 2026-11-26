# sysmon_integrity_master: authoring notes (the comments of .codex_state/checks/sysmon_integrity_master.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sysmon_integrity_master (class; required_base filesystem_base). It installs
# a checklist script that, when run on the Puppet master, writes `$integrity_checklist` (md5 sums of filelist) into the
# master's manifests directory (puppet::manifdir) as 97_integrity.pp. Fixture (params, never committed): filelist
# "/etc/hostname /etc/os-release". outdir comes from the lab Hiera (puppet::manifdir; it renders with a doubled slash).
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1); the link to the nodes as a capability row.
```
