# filesystem_lib64: authoring notes (the comments of .codex_state/checks/filesystem_lib64.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::filesystem_lib64 (class; node ubuntu; on Debian only in production's
# node_base, and as a [Debian] base of sysmon_base). Fixture: defaults (the class has no parameters). The clean node has
# /usr/lib64 (a directory holding the ld-linux link) and no /usr/lib64/nagios. Monitoring checks configured with the
# RedHat plugin path /usr/lib64/nagios/plugins must run on Ubuntu, where the plugins live in /usr/lib/nagios/plugins: a
# mutating check installs the Ubuntu plugins (packages_base installs them in production) and runs one through the link.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2).
```
