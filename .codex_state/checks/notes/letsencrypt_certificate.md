# letsencrypt_certificate: authoring notes (the comments of .codex_state/checks/letsencrypt_certificate.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 for puppet_infrastructure::letsencrypt_certificate (define; harness title letsencrypt_certificate): DEFERRED.
# The define's whole behaviour is one certbot run: letsencrypt::certonly with the domain list it builds and a DNS-01
# authenticator (DigitalOcean or Hetzner) reading API credentials from credentials_path. The lab has no ACME CA and no
# DNS provider API; Phase 1 went GREEN as mock-apply (node fixture letsencrypt_cert_standin: a self-signed stand-in
# certificate satisfies puppet-letsencrypt's domain-validation guard, so certbot never runs). Nothing the define does
# can be observed on the lab node: the only evidence there is the stand-in the fixture wrote.
# 2026-11-20 (backfill batch 7): purpose added (HQ ruling C1); the deferral stands until the stand-in lifts that follow
# the backfill (a test ACME CA with a DNS-01 stand-in on ubuntu2).
```
