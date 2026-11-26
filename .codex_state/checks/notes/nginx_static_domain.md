# nginx_static_domain: authoring notes (the comments of .codex_state/checks/nginx_static_domain.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_static_domain (define, harness title `nginx_static_domain`).
# Fixture (params): domain p8test.example.com, www_root /var/www/html, static_sslprefix p8test, ssl, manage_ssl,
# redirect_to_https = true; redirect_to_www, server_default_create, allow_directory_listing, letsencrypt = false.
# Resulting servers (lines 136-205): static_main_redirector (HTTP, 301 to https://<domain>) and static_https (HTTPS,
# www_root); static_http, static_default and static_https_www_redirector are absent. Required base: nginx_base
# (2048-bit DH group at /etc/nginx/dhparams.pem). Probes talk to the node's own nginx on 127.0.0.1 only.
# 2026-11-20 (backfill batch 6): outcomes table (HQ 2026-11-18 ruling 2); checks unchanged.
```
