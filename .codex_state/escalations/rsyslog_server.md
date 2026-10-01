# Escalation: rsyslog_server — local manifest predates the declared baseline (baseline drift)

Date: 2026-10-01. Raised by: advisor, pre-migration hazard check (before Codex was invoked).

## Evidence
- `manifests/rsyslog_server.pp` (from `d93f147 Baseline import`) is byte-identical to upstream commit
  `3fa2cc1` (2025-06-25, "issue #69: making changes based on Gustavo's comments").
- `release-0.9.8:manifests/rsyslog_server.pp` contains 4+ later Issue #69 commits
  (8a5df36, 5d78528, 39917c8, merged in PR #110 on 2026-05-21):
  - new params `active_days`, `retention_days`, `max_sessions`, `notify_on_connection_close`
  - `/etc/logrotate.d/rsyslog-hosts` from new template `rsyslog/rsyslog-hosts.logrotate.epp` (absent locally)
  - retention `cron { 'rsyslog_hosts_retention_cleanup' }`
  - `self_forward` param REMOVED; `40-forward-self.conf` forced `absent` ("avoid recursive logging loops")
  - `listener_simple.conf.epp` changed (takes max_sessions/notify_on_connection_close)
- Templates differ from 0.9.8 too: listener_simple, forward_simple (shared with rsyslog_client), and
  rsyslog-hosts.logrotate is missing. rsyslog_base/rsyslog_client (plain `Done`, reconciliation backlog)
  also differ from 0.9.8.
- Reviewer faithfulness check diffs against release-0.9.8; the wrapper runbook never instructs Codex to
  bring a class to 0.9.8 content. Outcomes without a ruling: reviewer FAIL (faithful=fail), or a
  `Done [from: release-0.9.8]` stamp on 2025-06 content (false provenance — violates Ruling B).

## Scope — this is systemic, not one class
Pending classes whose local manifest != release-0.9.8 (changed-line counts):
rsyslog_server 57+/7-, ssl_base 16, user_kde_lock_screen 11, puppet_boot_run 14, letsencrypt_base 16,
filesystem_apt 4, user_desktop 4, user_desktop_sudoer 4, node_base_desktop 90.
The other 45 pending manifests are identical to release-0.9.8.

## Options
A. Baseline-sync step (recommended): before migrating a drifted class, a separate commit
   `P8: baseline-sync <class> to release-0.9.8` copies the 0.9.8 manifest + the class's own templates
   verbatim from upstream; then the normal wrapper run migrates syntax. Shared templates
   (forward_simple, used by rsyslog_client) need a call: sync with the client reconciliation, or now.
   Requires: who performs the sync (advisor or a Codex bookkeeping exec), and a runbook/CLAUDE.md line.
B. Defer all 9 drifted classes to the end-of-Phase-1 reconciliation pass (block now, consistent with
   Ruling B's treatment of the historical 15).
C. Migrate the local (pre-0.9.8) content with a distinct marker (e.g. `Done [from: dev-3fa2cc1]`) —
   truthful but leaves the reconciliation debt and needs a new marker rule.

Recommendation: A. 0.9.8 is already the declared target (2026-07-01); syncing to it is applying that
decision, not redesigning. It just needs your sign-off because it changes repo behaviour and touches a
template shared with an already-Done class.
