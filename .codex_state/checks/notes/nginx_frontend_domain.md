# nginx_frontend_domain: authoring notes (the comments of .codex_state/checks/nginx_frontend_domain.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_frontend_domain (define; node ubuntu; required_base per plan).
# Fixture (params, never committed): domain p8test.example.com, frontend_sslprefix p8test, manage_ssl true,
# backend_hosts_and_ports ["127.0.0.1:8080"], backend_protocol http; every other parameter at its default
# (enable_ssl true, decorate_naked false, server_https_www_create and redirect_http_www_to_https_www_create true,
# TLSv1.3 only, security_headers false, no IP whitelist, no external-redirect prevention). The lab's throwaway
# certificate (master_fixtures.sh) names p8test.example.com and *.p8test.example.com. Probes connect only to the node's
# own loopback, naming the domain with curl's --resolve.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the parameters production sets are a check in the variant run
# `prod`, the RedHat branch in `rhel` (rhel9); the parameters production does not set are an accepted gap.
# 2026-11-23 authoring correction (sweep run 20261123T135839Z-author, variant prod APPLY_FAILED): the prod
# fixture set dynamic_dns_resolution and www_fix_redirect together, and the class cannot take both: the www-catcher
# location (nginx_frontend_domain.pp:461-477 at the baseline) reads $backend_name, which only the non-dynamic branch sets (:408);
# Puppet 8 refuses the catalog ("Unknown variable: 'backend_name'", :479 of the current file). No production node statement sets both
# (fleet_variants.py usage, names only: 0; both default false; Hiera is not read), so dynamic_dns_resolution moved to
# its own variant `dyn`, with a check that proxies through it. Also corrected: the prod probe's 'Let's Encrypt' echo
# broke its own single quotes; the resolver line tested nothing dynamic (the resolver is rendered in every variant,
# baseline :710) and gave way to proxy_locations_others_config (production sets it; the fixture lacked it) and www_fix_redirect.
# The combination is Phase 5 backlog #14.
# Correction round 1 of the swept set (2026-11-25, review 20261125T095356Z, purpose): decorate_naked, which production
# sets, was untested, and the render line for the www server matched whatever it is (the HTTP www server is always
# there). The line is removed and the prod variant tests decorate_naked as the naked domain's 301 to www over HTTP and
# HTTPS. The parameters no production node sets that the table left out join the accepted-gap row.
# Correction round 2 of the swept set (2026-11-25, review 20261125T101915Z, purpose): the cipher list the class sets for
# TLS below 1.3 had no row; it acts once TLSv1.2 is on, as production sets on 2 node statements and the prod variant
# does, so a prod check now handshakes TLSv1.2 with a cipher in the list and one outside it.
  # 2026-11-18 authoring correction (run 1, 20261118T215346Z): openssl s_client prints "Protocol : TLSv1.2" in the session stub of
  # a refused TLS 1.2 handshake and no Protocol line for TLS 1.3 (measured on the node: nginx answered TLS 1.2 with a
  # protocol-version alert and completed TLS 1.3); the handshake's "New, <version>" line is read instead.
```
