# Phase 5 backlog — single source
Behaviour changes that Phase 1 (syntax only) deliberately does NOT make. Each one is upstream behaviour that the
harness accepts today through an explicit, justified mechanism; Phase 5 decides whether to change it. Add an item
only with its HQ source and every carrier class (verified by grep at the time of writing). Advisor-only file.

| # | change for Phase 5 | carriers (manifest:line) | accepted in Phase 1 by | source |
|---|---|---|---|---|
| 1 | apt update frequency: `class { 'apt': update => { frequency => 'always' } }` → `'daily'` (stops `Exec[apt_update]` on every agent run) | packages_base.pp:22 (inherited by node_base) | plan expected_run2_events `Exec[apt_update]` + header justification | DESIGN_DECISIONS 2026-11-10 "HQ rulings before batch 2 (1/3)" |
| 2 | replace `notify` resources with `notice()` / `debug()` function calls (a notify resource reports a change on every run; a logging function does not) | nginx_frontend_domain.pp:256 (Array backends) / :262 (Hash backends), both debug, also reached through nginx_frontend; mariadb_server.pp:64 (debug, unconditional; class still pending — its migration will need the same expected_run2_events entry); ssl_base.pp:98 (only when `$myservice` is not nginx/postfix; not reached by the harness fixture) | plan expected_run2_events `Notify[Generated Upstream members for *]` + header justification (report stage) | HQ batch-3 acceptance item 2 — accepted on the apt_update basis |
