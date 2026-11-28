# sysmon_backup: authoring notes (the comments of .codex_state/checks/sysmon_backup.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sysmon_backup (class; required_base filesystem_base).
# Fixture: the master's Hiera lab fixtures (master_fixtures.sh): sysmon::basedir /var/tmp/p8test-sysmon/,
# sysmon::address sysmon.p8test.invalid, sysmon::backdir %{filesystem::backdir}/sysmon
# (= /opt/puppet-infrastructure/backup/sysmon), sysmon::backdays 10; no sysmon::compression key (default true);
# filesystem::bindir /opt/puppet-infrastructure/bin. The class instantiates puppet_infrastructure::backup 'sysmon'.
# 2026-11-20 (HQ after batch 16, item 1): the earlier exercise created the backup directory itself, which masked that
# nothing declared it (puppet_backup's finding). The set no longer creates it: local change #14 has the backup define
# declare it, and the-backup-directory-exists reads it after the apply. The exercise creates only the source data
# (sysmon::basedir, the monitoring server's data). Purpose and outcomes (HQ rulings 2 and C1), a restore, retention with
# planted archives (backdays 10: find -mtime +9), and local change #15: a run that cannot write fails loudly.
# 2026-11-20 correction (review 20261120T224719Z, puppet_backup): the loud-failure check made the directory read-only,
# so the retention step could not have deleted anything either way. It now fills a one-page tmpfs over the
# directory (tar fails, the directory stays writable) holding an archive old enough for retention to delete.
```

2026-11-28 (the re-verification after the rename, results/sysmon_backup/: FINDINGS): local change #26 quotes the shared backup
template's directory list (`FILETARGETDIRS="<%= @basedir %>"`); the check that reads the script's assignments expects
the quoted line now. The change's row names this class as a user of the template; its set was not updated with it.
