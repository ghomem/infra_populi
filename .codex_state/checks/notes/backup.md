# backup: authoring notes (the comments of .codex_state/checks/backup.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::backup (define; harness title `backup`, so the script is backup-backup.sh).
# Fixture (params, never committed): basedir /etc/default, prefix p8test-backup, backdir
# /opt/puppet-infrastructure/backup/p8test, ndays 7, bindir /opt/puppet-infrastructure/bin; defaults: user root, 23:00, every
# monthday, compression true. Written 2026-11-19 (backfill batch 5): the script runs by hand as behaviour (a gzip tar of
# the base directory, restorable byte for byte), and retention is shown with planted archives of known ages: with
# ndays 7 the script deletes its own prefix's files older than 6 full days (find -mtime +6), and nothing else.
# 2026-11-20 (HQ after batch 16, item 1): the fixture's backdir moved to /opt/puppet-infrastructure/backup/p8test, a
# directory under filesystem_base's parent as every real caller's is; local change #14 has the define declare it.
# 2026-11-20 (HQ after batch 16, item 1b): a run whose archive cannot be written must fail loudly. The check mounts the
# backup directory read-only over itself (a read-only bind mount: even root cannot write into it) and runs the script as
# cron would. Authoring error in run 20261120T212613Z: chattr +i only blocks new names, and the archive of the same
# minute (written by the check before it) was simply rewritten, so tar did not fail; the read-only mount blocks both.
# 2026-11-20 correction (review 20261120T224719Z, puppet_backup): the loud-failure check made the directory read-only,
# so the retention step could not have deleted anything either way. It now fills a one-page tmpfs over the
# directory (tar fails, the directory stays writable) holding an archive old enough for retention to delete.
```

2026-11-28 (local change #26, rules/local_changes.md): the template quotes the directory list
(`FILETARGETDIRS="<%= @basedir %>"`), so the two checks that read the script's assignments expect the quoted line
(script-installed-with-the-parameters, plain-script-and-the-users-cron). Their expectations followed the baseline's
text, which the local change alters on purpose; the after-run before this edit
(results/backup/20261128T022054Z-author) failed on them only, and the mutating run was skipped because of them.
