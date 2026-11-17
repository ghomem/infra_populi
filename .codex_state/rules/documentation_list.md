# Documentation list — single source
Behaviour that operators of the migrated code must know. Phase 3 runs observed it; none of it is a defect to fix.
Add an item only with its HQ source and the evidence (the Phase 3 result that showed it). Advisor-only file.

| # | class | what to document | evidence | source |
|---|---|---|---|---|
| 1 | backup_rsnapshot | Restores use the path `daily.0/etc/etc/…` (generally `<snapshot_root>/daily.N/<prefix>/<basedir>/…`). The template's `backup <basedir> ./<prefix>` combined with rsnapshot's `--relative` nests the source path under the prefix: a backup of `/etc` with prefix `etc` lands in `daily.0/etc/etc/hostname`. | `checks/results/backup_rsnapshot/20261116T113256Z-author.json` (daily-backup-executes effect: `/opt/puppet-infrastructure/backup/daily.0/etc/etc/hostname`) | HQ 2026-11-16 item 4 |
| 2 | nginx_proxy_smtp_auth_ppa (retired) | The class is gone from the module. It added the solidangle nginx PPA (Ubuntu 20.04 only) and its version-check script; on any newer release it broke `apt-get update`. A node that still declares it fails to compile; one that had it applied keeps the PPA's sources.list entry, which must be removed by hand. | batch-7 report item 2 (Launchpad `dists/<release>/Release` 200 for focal, 404 for jammy, kinetic and noble; run-1 `apt-get update` returned 100 on 24.04) | HQ 2026-11-17 ruling 3 |
