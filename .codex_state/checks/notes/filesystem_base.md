# filesystem_base: authoring notes (the comments of .codex_state/checks/filesystem_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::filesystem_base (class; node ubuntu). Fixture (params, never committed):
# customize_syslog_mode true, syslog_mode 'u=rw,g=r,o=' at its default. The lab Hiera's filesystem::* keys put the
# local tree at /opt/puppet-infrastructure (bin, etc, backup, pkgsdir). On the clean node /etc/default/locale is
# Ubuntu's link to /etc/locale.conf and /var/log/syslog already has 0640 syslog:adm, so the syslog mode is shown by a
# drift that the class's next agent run corrects. Probes read the node's own files and run its tools.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the default variant (customize_syslog_mode false, node_base's
# default) and the RedHat branch on rhel9 are now checks in the variant runs `default` and `rhel`.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2); the set-level uncovered list moved into it.
```
