# rsyslog_apparmor_exception: authoring notes (the comments of .codex_state/checks/rsyslog_apparmor_exception.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::rsyslog_apparmor_exception (class; required_base rsyslog_base).
# Fixture (params, never committed): logs_dir /srv/p8test-logs. It is deliberately OUTSIDE /var/log: the stock
# usr.sbin.rsyslogd profile already allows `/var/log/** rw`, so only a directory outside it shows what the exception
# adds. (The Phase 1 harness run used /var/log/p8test-remote; the fixture moved for Phase 3, 2026-11-16.)
# 2026-11-20 (backfill batch 6): purpose and outcomes (HQ rulings 2 and C1), and the control that the same confined
# rsyslogd is still denied a directory outside the exception (the profile, not ownership, decides).
```
