# puppet_backup: authoring notes (the comments of .codex_state/checks/puppet_backup.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::puppet_backup (class, no parameters: no params file; required_base
# filesystem_base). It declares puppet_infrastructure::backup titled `puppet` with the lab Hiera's puppet:: keys:
# basedir /etc/puppetlabs/, prefix puppet::address puppet.example.com, backdir %{filesystem::backdir}/puppet
# (= /opt/puppet-infrastructure/backup/puppet), backdays 10, no puppet::compression key (default true); bindir
# /opt/puppet-infrastructure/bin. Production declares it on the Puppet master (operations/puppet.pp); /etc/puppetlabs
# exists on every node, so the plan's default node runs it.
# 2026-11-20 (backfill batch 6): first set. The script runs by hand as behaviour (a gzip tar of /etc/puppetlabs,
# restorable byte for byte), retention with planted archives of known ages (ndays 10: find -mtime +9). No step of the set
# creates the backup directory: whether it exists after the apply is itself a check (neither this class, the backup
# define nor filesystem_base declares it; filesystem_base declares only its parent).
# 2026-11-20 (HQ after batch 16, item 1): the finding is fixed by local change #14 (the backup define declares the
# directory) and #15 (a run that cannot write fails loudly, checked by a-failed-run-is-loud).
# 2026-11-20 correction (review 20261120T224719Z, puppet_backup): the loud-failure check made the directory read-only,
# so the retention step could not have deleted anything either way. It now fills a one-page tmpfs over the
# directory (tar fails, the directory stays writable) holding an archive old enough for retention to delete.
```

2026-11-28 (the re-verification after the rename, results/puppet_backup/: FINDINGS): local change #26 quotes the shared backup
template's directory list (`FILETARGETDIRS="<%= @basedir %>"`); the check that reads the script's assignments expects
the quoted line now. The change's row names this class as a user of the template; its set was not updated with it.
