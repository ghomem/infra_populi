# ssl_nginx_domain: authoring notes (the comments of .codex_state/checks/ssl_nginx_domain.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::ssl_nginx_domain (define; node ubuntu; required_base nginx_base). Fixture
# (params, never committed): sslprefix p8test, letsencrypt_certificate false. The define declares ssl_base for nginx
# with that prefix. The master's extra_files mount holds the lab's throwaway PKI (master_fixtures.sh): p8test.key and
# p8test.crt are a server key and certificate (CN p8test.invalid), and p8test.intermediate.crt is the throwaway CA's
# certificate that signed it, standing in for an intermediate. Probes read only the node; the TLS check connects to
# the node's own loopback.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): Let's Encrypt material (production uses it) and the RedHat branch
# are checks in the variant runs `letsencrypt` and `rhel`.
  # Correction round 1 of the swept set (2026-11-25, review 20261125T045948Z): the letsencrypt variant checked only the
  # key, under an id that claimed nginx served the pair. Its key check is renamed for what it tests, and two checks are
  # added on the Let's Encrypt paths: the bundle .pem is the certificate then its chain (p8test-chain.pem), and nginx
  # serves that pair over TLS.
  # Correction round 2 (2026-11-18, review 20261118T214106Z): the bundle and the key now drift one at a time, each
  # followed by an agent run, so each file's notify is shown on its own.
  # Correction round 1 (2026-11-18, review 20261118T213542Z): the TLS check's handshake moved from its action into its
  # effect (the action only adds the server block and reloads nginx); a RedHat row was added.
```
