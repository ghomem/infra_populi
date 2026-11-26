# rsyslog_base: authoring notes (the comments of .codex_state/checks/rsyslog_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::rsyslog_base (class; node ubuntu). Fixture (params, never committed): none
# in the base and rhel runs since 2026-11-24 (no ssldir_override; the lab Hiera binds none either); the variant
# `override` gives ssldir_override /etc/puppetlabs/puppet/./ssl. The node's
# certname is its host name. Probes read the node's own files and rsyslog; the use of this material by a forwarding
# client and a TLS server is tested end to end in rsyslog_client's and rsyslog_server's sets.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1b): the RedHat syslog account is a check in the variant run `rhel` (rhel9).
# 2026-11-23 correction round 1 (review FAIL 02690f2, purpose): the default ssldir arm, which production nodes use unless
# their Hiera sets the key, is now a row naming what the lab lacks, with evidence (and documentation list cutover row
# 10); the rhel run now also checks the TLS files there (byte for byte, ids 0, key 0600) and that rsyslog runs as root.
# 2026-11-24 (HQ resume ruling 2, policy B, local change #23): with no ssldir_override an AIO agent's TLS files come
# from its own ssldir, /etc/puppetlabs/puppet/ssl (the aio_agent_version fact), so the base and rhel runs now take the
# default arm and the uncovered row for it is gone; the override arm is the variant `override`, whose path differs in
# text from the default so that the catalog shows which arm was taken. The pre-AIO arm (/var/lib/puppet/ssl) is a row.
  # 2026-11-18 authoring correction (run 1, 20261118T112712Z): `systemctl stop rsyslog` alone left syslog.socket
  # listening, and the next log line re-activated rsyslog at once (effect: active; the agent run had nothing to do).
  # The drift now stops the socket too, so only the class's `ensure => running` can bring rsyslog back.
  # 2026-11-18 purpose correction (review 20261118T113259Z): the service's restart relationship (subscribe to the TLS
  # directory, line 79) was neither tested nor listed; the next two checks test it, and the uncovered note above states
  # what the relationship does not cover.
  # 2026-11-18 (HQ batch-10 ruling 5, policy B): the renewal case, formerly uncovered, is a check now. It fails on the
  # baseline (the service subscribes to the directory only) and passes after the local change (rules/local_changes.md).
  # 2026-11-18 authoring corrections: run 4 (20261118T151822Z), the noted time was unquoted; run 5
  # (20261118T152241Z), a one-second --since window counted the previous check's restart. The check now notes rsyslog's
  # journal cursor and counts starts after it.
```
