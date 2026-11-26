# ssl_postfix: authoring notes (the comments of .codex_state/checks/ssl_postfix.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::ssl_postfix (class; required_base postfix_smtp_node, which declares the
# Service['postfix'] ssl_base notifies). Fixture (params, never committed): sslprefix p8test (the lab master's fixture
# PKI, CN p8test.invalid), letsencrypt_certificate false. The class hands ssl_base the service postfix.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), and ssl_base's restart on a changed
# certificate as behaviour (a bundle changed by hand, the node's agent run, the postfix master under a new PID: Ubuntu's
# postfix.service is a oneshot wrapper, so the master's PID file is read); the key's restore and restart likewise (a
# second agent run), as ssl_nginx's set after its review 20261121T055031Z.
```
