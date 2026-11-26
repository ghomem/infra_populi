# rsyslog_server: authoring notes (the comments of .codex_state/checks/rsyslog_server.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::rsyslog_server (class; required_base filesystem_base; it includes
# rsyslog_base itself). Fixture: class defaults (port 6514, log_root /var/log, active/retention 7 days, rotation 00:00,
# retention 03:17, max_sessions 2000, notify_on_connection_close false); the lab Hiera binds rsyslog_base's ssldir to
# /etc/puppetlabs/puppet/ssl (master_fixtures.sh). The node's own Puppet certificate (CN/SAN puppet8node) is the
# listener's certificate.
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1); exercises for the certificate check (a
# self-signed client is refused), the rotation (forced, then a new message lands in a fresh file: rsyslog reopened
# it after the postrotate HUP) and the retention script (planted files of known dates and ages).
# Correction round 1, 2026-11-20 (review 20261120T232205Z, purpose): the server's own logs in its host directory, the
# unknown-program branch, and rsyslogd's own refusal entry as the self-signed check's evidence (prototyped on the node).
```
