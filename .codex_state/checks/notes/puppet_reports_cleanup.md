# puppet_reports_cleanup: authoring notes (the comments of .codex_state/checks/puppet_reports_cleanup.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::puppet_reports_cleanup (class, no parameters: no params file). Lab Hiera:
# puppet::reportdir /opt/puppetlabs/server/data/puppetserver/reports, puppet::reportdays 7. Production declares it on the
# Puppet master (operations/puppet.pp), whose puppetserver writes the reports; the plan's default node is an agent with
# no puppetserver, so the exercise plants a report store of that shape (the server's, not the class's, to create) and
# runs the command root's crontab holds, as cron would at midnight.
# 2026-11-20 (backfill batch 6): first set.
```
