# Documentation list — single source
Behaviour that operators of the migrated code must know. Phase 3 runs observed it; none of it is a defect to fix.
Add an item only with its HQ source and the evidence (the Phase 3 result that showed it). Advisor-only file.

| # | class | what to document | evidence | source |
|---|---|---|---|---|
| 1 | backup_rsnapshot | Restores use the path `daily.0/etc/etc/…` (generally `<snapshot_root>/daily.N/<prefix>/<basedir>/…`). The template's `backup <basedir> ./<prefix>` combined with rsnapshot's `--relative` nests the source path under the prefix: a backup of `/etc` with prefix `etc` lands in `daily.0/etc/etc/hostname`. | `checks/results/backup_rsnapshot/20261116T113256Z-author.json` (daily-backup-executes effect: `/opt/puppet-infrastructure/backup/daily.0/etc/etc/hostname`) | HQ 2026-11-16 item 4 |
