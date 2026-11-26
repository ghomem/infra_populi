# nginx_static: authoring notes (the comments of .codex_state/checks/nginx_static.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_static (class; required_base nginx_base). The wrapper includes
# nginx_default_removal and declares nginx_static_domain { $domain: } with its own parameters. Fixture (params, never
# committed): domain p8test.example.com, www_root /var/www/html; every other parameter at its default (ssl false,
# redirects false, server_default_create true, redirect_default false).
# Resulting servers (nginx_static_domain.pp at the baseline): static_http_<domain> (port 80, server_name <domain>,
# www_root) and static_default_<domain> (port 80, default_server, return 404); no redirector, no HTTPS server.
# Unlike nginx_static_domain's HTTPS fixture, port 80 here has two servers, so the Host header discriminates.
# Probes talk to the node's own nginx on 127.0.0.1 only.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), and a directory without an index is not listed.
  # 2026-11-17 authoring correction (Phase 3 review FAIL, 20261117T015005Z): run 1 asked for a MISSING path
  # (/p8/phase3), which the domain's own server also answers 404, so the 404 was not attributable to the default
  # server; its mismatch varied the Host AND the path, and claimed `/` serves content (it is 403: no index.html,
  # autoindex off). Now both probes request the same EXISTING www_root file and only the Host varies.
```
