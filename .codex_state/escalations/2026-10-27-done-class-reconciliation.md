# Reconciliation list — the 31 "done" classes under gate v2 (sprint step 1.5)

Source: the latest verdict per class in `.codex_state/reviews/<class>/<UTC>.json` (reviewer v2, revert-first,
gate v2 + coverage, two-diff vs release-0.9.10 = cf477c6). Generated 2026-10-27 from those files; the
verdict files are the evidence, this list is the routing.

**Result: 8 PASS / 23 FAIL.** Until HQ rules, the 23 remain "done under gate v1" and none of the 31 is
quoted externally as verified (ruling 2). Failing checks across the 23: faithful 20, records 19,
comments_preserved 18, header_modules 12, provenance 4, idempotent 3, scope 1.

## PASS (8) — verified at baseline content under gate v2
backup, filesystem_base, filesystem_base_desktop, hello_world_flask_common, network_static*, puppet_backup,
puppet_commush, user_kde_lock_screen_common.
(*network_static: syntax-faithful, but it writes ifupdown config on a netplan-only node — a no-op here;
Phase-3 item, already in the diagnosis.)

## Resolution paths for the 23

### A. Records only — code is faithful (3)
| class | finding | path |
|---|---|---|
| ssh_secure | no migration header; saz-ssh 13.1.0 unnamed. Code change `$::osfamily` → `$facts['os']['family']` is correct | header via record_green.sh (3.2) |
| sftp_only | content == baseline, but the migrate commit changed no class file; no header; saz-ssh unnamed | header via record_green.sh |
| network_dhcp | scope: migrate commit 0ecf985 also edited blocked.txt for network_static, network_vpn, openvpn_server (ruling 8: record, do not revert — recorded here); header lacks deps (puppet-network 2.2.1, filemapper 4.0.0, kmod 4.1.0) | header via record_green.sh |

### B. Upstream comments deleted and/or code reformatted — no behaviour change (13)
Path: restore the baseline text verbatim, keep only the genuine syntax translations listed, add the 2-line
header. Mechanical; advisor tier (baseline text restored, nothing invented). Then the normal loop.
| class | kept translations | extra |
|---|---|---|
| backup_rsnapshot | — | parameter list reformatted |
| caching_nameserver | — | plain `Done` |
| dns_client | — | header names nonexistent `puppet-resolv_conf` (uses saz-resolv_conf 8.0.1); fixture equals baseline resolv.conf → run 1 is a no-op: pick nameservers that differ |
| filesystem_lib64 | — | lost the "ubuntu only" note |
| filesystem_sec | — | reformatted; **default branch cannot compile** (`Cannot reassign variable '$restricted_group'`, filesystem_sec.pp:25 — found by the 2.2 default-param compile; upstream code reassigns a parameter → see question 6) |
| firewall_addon_caching_nameserver | `action`→`jump` | whole-file reformat; header firewall without version |
| firewall_addon_web | `action`→`jump` | lost the "do the main firewall configuration first" warning |
| firewall_addon_xrdp | `action`→`jump`, `provider`→`protocol` | lost the 14-line IPv6/ESTABLISHED rationale; `state => ['ESTABLISHED']` → `'ESTABLISHED'` must revert to the array |
| firewall_ipv6_drop | `action`→`jump`, `provider`→`protocol` | lost the "add-on to firewall_secure" warning |
| firewall_ipv6_drop_policy | — | lost the add-on warning; reformatted |
| nginx_default_removal | — | one comment deleted; run 1 no-op is genuine (nginx absent on baseline) — justify in the review |
| openvpn_set_vpn_passwd_file | — | lost "only tested on LD7"; whole-block reformat |
| puppet_reports_cleanup | — | re-indented cron attributes |

### C. Behaviour divergence / reimplementation — re-migrate from the baseline (4)
| class | divergence | note |
|---|---|---|
| filesystem_yum | adds `file { $localdir }` and `file { "${localdir}/bin" }` (mode 0755) | false `[from:]` provenance; causes node_base/RedHat duplicate declaration (composite node_base_redhat). Ruling 8: drop the dirs, required_base=filesystem_base |
| firewall | adds the same inline dirs; removes resource default `Firewall { require => undef }` | `action`→`jump` hunks are correct |
| sysmon_puppet_cert_status | adds exec `sysmon_puppet_cert_status_apt_update`, a new OS conditional, inline dirs; retargets the package require | ruling 8: re-migrate faithfully |
| rsyslog_base | `ssldir_override` parameter + selector replaced by `$settings::ssldir`; `source` values gain `file://`; 7 comments rewritten | pre-migrate drift too (D) |

### D. Drift that predates the migration — baseline-sync, then the normal loop (3)
| class | drift | fleet |
|---|---|---|
| rsyslog_client | manifest AND `templates/rsyslog/forward_simple.conf.epp` older than baseline: no `forward_auth_log` (auth.log forwarding block missing), no `ssldir_override`, `target_ip` made mandatory | **57 production servers** — highest-impact item on this list |
| rsyslog_base | (see C) | 58 |
| docker_container | baseline 0.9.10 adds `$command`; migrate commit changed no class file; `[from: release-0.9.8]` | 13; ruling 1: re-migrate |

### E. Plan / harness items surfaced by revert-first (1)
| class | finding | path |
|---|---|---|
| backup_rsnapshot_pre | run 1 fails: `/opt/puppet-infrastructure/bin/rdiff.sh` — parent dir undeclared (hazard 4). Passed gate v1 only because the node was not reverted | plan fix `required_base=filesystem_base` (4.1, advisor tier), then content as B |

## Engine defects the sweep found (fixed, committed, re-reviewed)
- 3.1-fix (6947198): v2 snapshot froze apt lists (Feb 2026) → mirror 404 for bind9; revert now runs `apt-get update` (~12 s). caching_nameserver re-reviewed.
- 1.1-fix (90a8a44): Resource API creations (`defined 'ensure' as 'present'`, puppetlabs-firewall 8) were not counted. firewall_addon_caching_nameserver re-reviewed.

## Decisions requested (see sprint-checkpoint-1.md)
Routing A/B as advisor tier; C/D through the normal loop after the sprint (ruling 8); question 6
(filesystem_sec default branch) as an upstream-defect ruling.
