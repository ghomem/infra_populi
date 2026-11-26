# postfix_smtp_node: authoring notes (the comments of .codex_state/checks/postfix_smtp_node.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::postfix_smtp_node (class, no parameters; values from the lab master's Hiera).
# Lab Hiera: relayhost mailserver.mycompany.com, relayport 587, myorigin mycompany.com (common.yaml), relayuser
# p8test-relay and a fake relaypass (p8test_fixtures.yaml); mynetworks, mydestination, message_size_limit and
# root_email_alias take their lookup defaults (127.0.0.0/8, the hostname, 10240000, ''). Ubuntu: libsasl2-modules,
# CA file /etc/ssl/certs/ca-certificates.crt. No probe sends mail: the fixture relayhost is a real-world domain, and a
# probe must never contact another host. The relay password is never printed.
# Purpose, outcomes and the relay as behaviour added 2026-11-19 (backfill batch 4, HQ batch-10 rulings 2 and C1): the
# peer (ubuntu2) plays the relayhost (postfix submission on 587 with SASL from dovecot, the relay account p8test-relay
# with the lab fixture's fake password, marked not-a-secret in master_fixtures.sh). On the node the relayhost name is
# pinned to the peer in /etc/hosts (the runner's P8_PEER_ADDR), and a fence rejects mail ports to every other address,
# so no message can reach the real-world domain. Measured on an applied node (2026-11-19, a TEST-NET pin): the MX
# question for the name gets NXDOMAIN and the A question the /etc/hosts address, and postfix falls back from a missing
# MX to the A record; sendmail refuses an over-size message with exit 75 'message file too big'.
# AUTHORING ERROR corrected 2026-11-19 after run 20261119T055606Z (3 FAIL): (1) that measurement asked the resolved
# stub (127.0.0.53) directly, but the node's /etc/resolv.conf is a static file naming public resolvers, which postfix's
# chroot copy also names, so postfix never saw the /etc/hosts pin ('Host not found', message deferred). The relay
# check now points /etc/resolv.conf and postfix's chroot copy at the stub (a declared lab fixture: production resolves
# the relayhost through its DNS), waits until the stub answers the pin, and reloads postfix. (2) The peer's postfix also
# listens on [::]:587; the expectation allows that line.
# AUTHORING ERROR corrected 2026-11-19 after run 20261119T060057Z (1 FAIL; the relay itself passed: queue empty,
# status=sent, the mailbox holds the message with ESMTPSA): the peer's submission service logs under the tag
# postfix/smtpd (the master.cf entry sets no syslog_name), not postfix/submission/smtpd; read on the peer's journal
# ('client=unknown[...], sasl_method=PLAIN, sasl_username=p8test-relay').
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the RedHat branch is a check in the variant run `rhel` (rhel9); the
# per-node Hiera variants name what is missing.
# Correction round 1 of the swept set (2026-11-25, review 20261125T074313Z): the per-node Hiera row was uncovered for a
# false reason. The keys are looked up under the node's certname, and the lab Hiera fixture (master_fixtures.sh) now
# gives p8lab-rhel9 non-default values for all four, so the variant run `rhel` checks that they reach postfix.
# 2026-11-25 authoring correction (run 20261125T075907Z-author): the new check expected mydestination to be the Hiera
# value alone; the template appends ', localhost.localdomain, , localhost' to it (main.cf:34), as the base check's
# expectation already shows. The node's value was as the baseline makes it.
```
