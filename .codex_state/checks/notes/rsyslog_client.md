# rsyslog_client: authoring notes (the comments of .codex_state/checks/rsyslog_client.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::rsyslog_client (class; node ubuntu; it declares rsyslog_base itself).
# Fixture (params, never committed; changed 2026-11-18 for these checks, and 2026-11-24): target = the peer's host
# name, target_ip = the peer's host-only address (so the class pins it in /etc/hosts), forward_auth_log true; no
# ssldir_override (rsyslog_base's default, the AIO agent's own ssldir, local change #23); port 6514, check_names
# false, no failover at their defaults.
# The peer (ubuntu2) plays the remote log server: an rsyslog TLS listener on 6514 with the peer's own Puppet
# certificate from the same lab CA (x509/certvalid on both sides). Node probes name no other host; peer probes name
# only the class node's host-only address.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): forward_auth_log, check_names and a failover target are a check in
# the variant run `options`; the failover switch itself names what is missing.
# 2026-11-24 (HQ resume rulings 1 and 2): local change #22 removes deleteStateOnFileMove, which rsyslog 8.2312 (Ubuntu
# 24.04) and 8.2310 (RHEL 9.5) reject (escalations/rsyslog_client.behaviour.md). The base run now sets
# forward_auth_log and no ssldir_override: rsyslog must start with no configuration error, a line appended to
# /var/log/auth.log (which only the imfile input reads) must reach the peer, and the TLS files come from the default
# ssldir (#23). The variant `rhel` checks the configuration on RHEL 9.5.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2), with the restart on a changed rule (line
# 40's comment) the table showed untested; the set-level uncovered entry moved into it.
  # 2026-11-18 authoring correction (run 1, 20261118T111532Z): the peer's server kept its TLS files in
  # /etc/p8test-rsyslog, which Ubuntu's AppArmor profile for rsyslogd does not let it read ("apparmor=DENIED ...
  # /etc/p8test-rsyslog/ca.pem"), so no listener came up. They now live under /etc/rsyslog.d, which the profile allows
  # (the class's own /etc/rsyslog.d/tls is there for the same reason). The behaviour is unchanged.
  # 2026-11-18 authoring correction (run 2, 20261118T111830Z): the class applied (and rsyslog first tried the target)
  # before the peer's server existed, so rsyslog suspended the forward ("Connection refused", next retry in 30 s) and
  # the token line, logged 5 s after the server came up, fell into that suspension and was dropped (the template's
  # legacy action has no queue). The action now restarts rsyslog first, as a client would start with its server up.
  # The behaviour is unchanged; the loss of lines logged while the target is unreachable is noted for Phase 5.
  # 2026-11-24 authoring correction (before run 20261124T163235Z): the journal count ends the probe, and grep -c exits 1
  # when it counts 0, so on rhel9 the check failed with the expected output (1, 1, active, 0); the count now ends in
  # `|| true` (here and in the rhel check). In that run rhel9's rsyslog was 8.2604.0-4.el9_9.1, not the baseline's
  # 8.2310.0-4.el9: installing rsyslog-gnutls upgrades rsyslog from the repository (dnf.rpm.log), and 8.2604 accepts
  # deleteStateOnFileMove (rsyslogd -N1 on a one-input file, measured by hand). The Ubuntu base run failed as before.
```
