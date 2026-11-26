# backup_rsnapshot: authoring notes (the comments of .codex_state/checks/backup_rsnapshot.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::backup_rsnapshot (define, harness title `backup_rsnapshot`).
# Fixture (params): basedir /etc, prefix etc, backdir /opt/puppet-infrastructure/backup, ndays 7; user/hour/minute
# at their defaults (root, 23, 0). Required base (plan): backup_rsnapshot_pre (rsnapshot package, /etc/rsnapshot.d),
# filesystem_base. Read-only probes, except daily-backup-executes (opt-in mutating: one real `rsnapshot daily`,
# judged on the snapshot it leaves). `rsnapshot -t` in daily-plan is test mode (prints, executes nothing).
# Outcomes table added 2026-11-19 (backfill batch 5, HQ batch-10 rulings 2 and C1), with retention as behaviour: eight
# more daily runs after the first must leave exactly ndays (7) snapshots, daily.0 to daily.6.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): other parameters (undeterminable production use: the passwd/ layer)
# are a check in the variant run `other`; the 23:00 firing names what is missing.
```
