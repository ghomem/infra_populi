# nginx_frontend: authoring notes (the comments of .codex_state/checks/nginx_frontend.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_frontend (class; node ubuntu; required_base nginx_base,
# filesystem_base). Fixture (params, never committed): domain p8test.example.com, frontend_sslprefix p8test,
# backend_hosts_and_ports ["127.0.0.1:8080"], backend_protocol http, server_monitoring_create true; every other
# parameter at its default (manage_ssl true, server_default_create true, redirect_default false). The class declares
# nginx_frontend_domain for the domain (the frontend checks below are that define's, through this class) and adds a
# default server, a monitoring server and its Nagios check. The lab's throwaway certificate (master_fixtures.sh) names
# p8test.example.com and *.p8test.example.com. Probes connect only to the node's own loopback.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the parameters production sets are a check in the variant run
# `prod`, the RedHat branch in `rhel` (rhel9); the parameters production does not set are an accepted gap.
# 2026-11-23 authoring correction (sweep run 20261123T135444Z-author, variant prod APPLY_FAILED): the prod
# fixture set dynamic_dns_resolution and www_fix_redirect together, and the class cannot take both: the www-catcher
# location (nginx_frontend_domain.pp:461-477 at the baseline) reads $backend_name, which only the non-dynamic branch sets (:408);
# Puppet 8 refuses the catalog ("Unknown variable: 'backend_name'", :479 of the current file). No production node statement sets both
# (fleet_variants.py usage, names only: 0; both default false; Hiera is not read), so dynamic_dns_resolution moved to
# its own variant `dyn`, with a check that proxies through it. Also corrected: the prod probe's 'Let's Encrypt' echo
# broke its own single quotes; the resolver line tested nothing dynamic (the resolver is rendered in every variant,
# baseline :710) and gave way to proxy_locations_others_config (production sets it; the fixture lacked it) and www_fix_redirect.
# The combination is Phase 5 backlog #14.
  # Correction round 1 of the swept set (2026-11-25, review 20261125T091633Z): two lines of production-parameters-render
  # (the www server name and a `return 30x`) matched whatever decorate_naked and redirect_default are, since the HTTP
  # servers always render them. They are removed, and the prod variant tests both parameters as redirects. manage_ssl
  # and redirects_external_location, set by no production node, join the accepted-gap row.
  # Correction round 1 (2026-11-18, review 20261118T220835Z): the status page's refusal off loopback became a check.
  # 2026-11-18 authoring correction (run 1, 20261118T220129Z): nginx's return turns the \n of 'Hello World!\n' into a
  # newline, so the body ends with one; the expectation allowed only a literal backslash-n.
```
