# postfix_smtp_base: authoring notes (the comments of .codex_state/checks/postfix_smtp_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::postfix_smtp_base (class). Fixture (params, never committed):
# smtp_hostname smtp.p8test.example.com, smtp_sslprefix p8test (the master's throwaway p8test PKI via ssl_postfix),
# postfix_port 587, smtp_users [p8testuser with the fake {PLAIN} password p8test-not-a-secret], allowed_client_ips
# [127.0.0.1], one allowed MAIL FROM address for p8testuser; extra_sec and letsencrypt_certificate false.
# Probes talk to the node's own postfix and dovecot on 127.0.0.1 only.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), and the restrictions as behaviour. The params
# fixture (local) now also holds a second SASL user p8testuser2 and a second allowed address
# p8test-other@p8test.example.com owned by it, so the sender-login rule has an address another user owns. The unlisted
# client is the node's own ::1 (inet_protocols = all; client_access lists 127.0.0.1 only). Prototyped on the node.
# Correction round 1, 2026-11-21 (review 20261121T052303Z, purpose): plaintext tried (TLS mandatory) and a system
# account tried (an OS user p8testsys whose password the OS accepts through PAM, refused by dovecot and SMTP AUTH).
# Correction round 2, 2026-11-21 (review 20261121T053246Z, purpose; the last round, production use 0): a full
# submission queued and delivered to root's local mailbox; onward relay to a remote MX as an uncovered row.
# Correction round 3, 2026-11-21 (HQ after batch 18, item 1; review 20261121T054226Z): relay to another domain through
# the second node. The peer ubuntu2 runs a small SMTP sink on port 25 that records what it receives; the node submits
# to an address-literal recipient on it (P8_PEER_ADDR; relayhost is empty, so postfix's SMTP client connects straight
# there). The params fixture now also sets do_not_warn_from_addresses_regexes [p8test@p8test\.example\.com], so the
# smtp_header_checks warning fires for the second message (From p8test-other@...) and not for the first.
  # 2026-11-17 authoring correction (run 1, 20261117T023815Z, FINDINGS): the probe called smtplib.SMTP.getwelcome(),
  # which does not exist (AttributeError after a successful connect); the banner is now read from a plain socket.
  # 2026-11-21 authoring correction (round 3 run 1, 20261121T110147Z, FINDINGS): postfix logs the header as
  # "header From: <value>: ..." and the pattern kept the trailing colon; it now stops at the colon. The behaviour (both
  # relayed and delivered, the warning once, for the second message) was as expected.
```
