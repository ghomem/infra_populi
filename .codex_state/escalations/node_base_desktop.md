# node_base_desktop: baseline-sync held — the baseline needs newer dependency content (hazard 8)

Status: ESCALATED 2026-10-27 (sprint 4.1c/4.2). Production use: 0 node statements (the desktop fleet uses
meaningful_puppet::meaningful_desktop instead; diagnosis B.3).
Local manifest differs from release-0.9.10. Its baseline declares gnome_lock_screen and
firewall_ipv6_drop_policy_desktop (both imported in 4.1c, so that precondition is now met) AND passes parameters to
puppet_infrastructure::rsyslog_client, whose local copy predates the baseline (group D of the reconciliation list:
no `forward_auth_log`, no `ssldir_override`, `target_ip` mandatory). Syncing node_base_desktop now would declare a
dependency with an interface the local dependency does not have — hazard 8's escalation condition.

## Options
- A (recommended): sync node_base_desktop after rsyslog_client's D-group re-migration (already first in the
  post-sprint queue: rsyslog_base → rsyslog_client → docker_container → filesystem_yum), as an ordinary
  `P8: baseline-sync` commit; no ruling beyond acknowledging the order.
- ~~B: retire node_base_desktop / node_base_domain_desktop~~ — withdrawn (HQ 2026-10-27 ruling 5: migrate everything;
  zero-declaration classes stay in the queue, sorted last). Option A is the path.
