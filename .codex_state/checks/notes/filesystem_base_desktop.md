# filesystem_base_desktop: authoring notes (the comments of .codex_state/checks/filesystem_base_desktop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::filesystem_base_desktop (class; plan node ubuntu). Fixture (params):
# customize_syslog_mode true; syslog_mode at its default u=rw,g=r,o= (0640). Hiera: localdir /opt/puppet-infrastructure,
# bindir and etcdir under it. Written 2026-11-19 (backfill batch 5). The three base directories are declared 0644;
# Puppet adds search permission to a directory wherever read is set, so the effective mode is read on the node. rsyslog
# on Ubuntu 24.04 already creates /var/log/syslog as syslog:adm 0640, the class's own values, so the class's part is
# shown as enforcement: the file's owner and mode are changed by hand and the next agent run must restore them.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the option's default and another syslog_mode, both passed by the
# desktop composites, are checks in the variant runs `default` and `mode`.
```
