# ssl_nginx: authoring notes (the comments of .codex_state/checks/ssl_nginx.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::ssl_nginx (class; required_base nginx_base, which declares the
# Service['nginx'] ssl_base notifies). Fixture (params, never committed): sslprefix p8test (the lab master's fixture
# PKI, CN p8test.invalid). The class hands ssl_base the service nginx (letsencrypt_certificate default false).
# Adapted from ssl_postfix's reviewed set (same ssl_base; the bundle is named for nginx).
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), and ssl_base's restart on a changed
# certificate as behaviour (a bundle changed by hand, the node's agent run, nginx under a new PID).
# Correction round 1, 2026-11-21 (review 20261121T055031Z, purpose): the key's restore and restart (a second agent run,
# after the key is changed by hand); the Let's Encrypt half dropped from the uncovered row (unreachable here).
# Not an outcome of this class: ssl_base's Let's Encrypt branch (ssl_base.pp:70-76). ssl_nginx has no parameter for it
# and passes no letsencrypt_certificate (ssl_nginx.pp:1-9), so the branch is unreachable through this class.
```
