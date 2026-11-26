# nginx_base: authoring notes (the comments of .codex_state/checks/nginx_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_base (class; required_external apt for Exec['apt_update']). Fixture:
# defaults (my_configs {}, ad_hoc_configs [], dh_params_bits 2048). Written for HQ batch-8 ruling 1: with puppet-nginx
# 8.4.0 the baseline's own `nginx_cfg_prepend` include of /etc/nginx/modules-enabled is a second include beside the
# module's (Debian `include_modules_enabled => true`), so the first dynamic module installed is loaded twice and nginx
# refuses to start (escalations/nginx_base.md). The mutating check installs one dynamic module (libnginx-mod-stream,
# Ubuntu 24.04) and judges the effect: exactly one include of the directory, `nginx -t` passes, the service runs.
# Probes read the node's own files and nginx only.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): my_configs and ad-hoc lines (production uses both) are a check in
# the variant run `custom`; another DH size and extra log formats are an accepted gap; the stream row names what is
# missing.
# Purpose and outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 rulings 2 and C1), with the Server
# header (server_tokens off) checked as behaviour and the default absence of the ad-hoc file.
  # Correction round 2 of the swept set (2026-11-25, review 20261125T055427Z): the stream row was uncovered for a false
  # reason. class nginx renders the stream block whenever its `stream` parameter is true, and my_configs reaches it, so
  # the variant run `stream` (my_configs {stream, package_name nginx-core, nginx_version}, nginx_frontend_mail's
  # per-target nginx_base fixture without mail) tests the block.
  # Correction round 1 of the swept set (2026-11-25, review 20261125T053027Z): the class's non-Ubuntu branch was in no
  # row although the rhel9 node kind is active; the variant run `rhel` now tests the base outcomes there.
  # Correction round 1 (2026-11-19, review 20261119T032919Z): nginx from the distribution (manage_repo false) got a row
  # and a check.
```
