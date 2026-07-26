# Puppet Class Migration Order

Generated: 2026-07-26 16:55:20 UTC

DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.

Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). The `[from: release-0.9.8]` annotation lives in migrated_classes.txt, not here.

Status summary: 16 done / 5 blocked / 0 needs verification / 66 pending / 87 total.

Next class: `puppet_infrastructure::backup_rsnapshot`

## DONE (git-derived)

| # | class | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::dns_client` | 1 | 1 | 2 | yes |  |
| 2 | `puppet_infrastructure::nginx_default_removal` | 1 | 7 | 2 | no |  |
| 3 | `puppet_infrastructure::puppet_reports_cleanup` | 2 | 2 | 2 | yes |  |
| 4 | `puppet_infrastructure::firewall_addon_caching_nameserver` | 2 | 2 | 5 | no |  |
| 5 | `puppet_infrastructure::firewall_addon_web` | 2 | 2 | 5 | no |  |
| 6 | `puppet_infrastructure::backup_rsnapshot_pre` | 2 | 3 | 3 | no | filesystem_base |
| 7 | `puppet_infrastructure::filesystem_lib64` | 2 | 4 | 2 | yes |  |
| 8 | `puppet_infrastructure::firewall_ipv6_drop` | 2 | 4 | 4 | yes |  |
| 9 | `puppet_infrastructure::firewall_ipv6_drop_policy` | 2 | 4 | 4 | yes |  |
| 10 | `puppet_infrastructure::caching_nameserver` | 3 | 2 | 4 | yes |  |
| 11 | `puppet_infrastructure::firewall_addon_xrdp` | 3 | 2 | 5 | no |  |
| 12 | `puppet_infrastructure::filesystem_yum` | 4 | 5 | 4 | no | filesystem_base |
| 13 | `puppet_infrastructure::rsyslog_client` | 4 | 6 | 3 | no | rsyslog_base |
| 14 | `puppet_infrastructure::sysmon_puppet_cert_status` | 5 | 5 | 5 | no | filesystem_base |
| 15 | `puppet_infrastructure::firewall` | 5 | 5 | 8 | yes |  |
| 16 | `puppet_infrastructure::rsyslog_base` | 5 | 8 | 5 | yes |  |

## BLOCKED

| # | class | reason |
|---:|---|---|
| 1 | `puppet_infrastructure::network_dhcp` | — blocked: network_config custom type fails on Puppet 8 (puppet-network/puppet-filemapper won't load); reimplementation candidate preserved at .codex_state/candidates/network_dhcp.reimplemented.pp; pending HQ resolution of dependency fork (a/b/c/d). See DESIGN_DECISIONS.md. |
| 2 | `puppet_infrastructure::network_static` | — blocked: same network_config root cause (also uses network_route); puppet-network/filemapper Puppet-8 incompat; deferred with networking cluster pending module-level resolution (a: P8-compatible module, or b: fix filemapper). See DESIGN_DECISIONS.md. |
| 3 | `puppet_infrastructure::firewall_addon_hosting` | — blocked: migration is CORRECT (action=>jump, 3 lines, behaviour-preserving, verified vs release-0.9.8) and preserved at .codex_state/candidates/firewall_addon_hosting.migrated.pp; NOT a code problem. Blocked on VALIDATION: class sets OUTPUT chain purge+policy=drop allowing only RELATED/ESTABLISHED+DNS+NTP, so an isolated harness run severs the node NEW outbound to master:8140 and run 2 hangs. Class documents it requires a base firewall (firewall/firewall_secure). Unblocks when base-context harness capability exists. See DESIGN_DECISIONS.md. |
| 4 | `puppet_infrastructure::network_vpn` | — blocked: transitively (chains openvpn_server); deferred with networking cluster pending module-level resolution. See DESIGN_DECISIONS.md. |
| 5 | `puppet_infrastructure::openvpn_server` | — blocked: heavy network_config use (lo/lo:0/br0 bridge, bridge_ports, loopback aliasing, subscribe refs); puppet-network/filemapper Puppet-8 incompat; do NOT reimplement per-class; deferred with networking cluster pending module-level resolution. See DESIGN_DECISIONS.md. |

## PENDING QUEUE

| # | class | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::backup_rsnapshot` | 3 | 1 | 4 | yes |  |
| 2 | `puppet_infrastructure::openvpn_set_vpn_passwd_file` | 3 | 1 | 5 | yes |  |
| 3 | `puppet_infrastructure::firewall_addon_openvpn_server` | 3 | 3 | 5 | no |  |
| 4 | `puppet_infrastructure::extra_packages_el` | 3 | 4 | 3 | yes |  |
| 5 | `puppet_infrastructure::filesystem_sec` | 3 | 4 | 4 | no |  |
| 6 | `puppet_infrastructure::postfix_smtp_base_config_file` | 3 | 4 | 4 | yes |  |
| 7 | `puppet_infrastructure::user_sysmon` | 3 | 4 | 4 | yes |  |
| 8 | `puppet_infrastructure::sftp_only` | 4 | 1 | 4 | yes |  |
| 9 | `puppet_infrastructure::mount_shares_desktop` | 4 | 1 | 5 | yes |  |
| 10 | `puppet_infrastructure::openvpn_nm_connection` | 4 | 2 | 5 | no |  |
| 11 | `puppet_infrastructure::user_samba` | 4 | 2 | 6 | no |  |
| 12 | `puppet_infrastructure::docker_container` | 4 | 3 | 4 | no |  |
| 13 | `puppet_infrastructure::rsyslog_server` | 4 | 6 | 3 | no | rsyslog_base |
| 14 | `puppet_infrastructure::filesystem_base_desktop` | 4 | 7 | 4 | yes |  |
| 15 | `puppet_infrastructure::ssh_secure` | 5 | 7 | 5 | yes |  |
| 16 | `puppet_infrastructure::ssl_base` | 5 | 8 | 5 | no |  |
| 17 | `puppet_infrastructure::ssl_postfix` | 2 | 6 | 4 | no | ssl_base |
| 18 | `puppet_infrastructure::ssl_nginx` | 2 | 7 | 4 | no | ssl_base |
| 19 | `puppet_infrastructure::ssl_nginx_domain` | 2 | 7 | 4 | no | ssl_base |
| 20 | `puppet_infrastructure::filesystem_base` | 5 | 9 | 4 | yes |  |
| 21 | `puppet_infrastructure::puppet_commush` | 2 | 4 | 3 | no | filesystem_base |
| 22 | `puppet_infrastructure::hello_world_flask_common` | 2 | 5 | 3 | no | filesystem_base |
| 23 | `puppet_infrastructure::user_kde_lock_screen_common` | 2 | 6 | 3 | no | filesystem_base |
| 24 | `puppet_infrastructure::user_kde_lock_screen` | 2 | 5 | 3 | no | user_kde_lock_screen_common,filesystem_base |
| 25 | `puppet_infrastructure::backup` | 3 | 3 | 4 | no | filesystem_base |
| 26 | `puppet_infrastructure::puppet_backup` | 3 | 4 | 4 | no | backup,filesystem_base |
| 27 | `puppet_infrastructure::puppet_boot_run` | 3 | 4 | 4 | no | filesystem_base |
| 28 | `puppet_infrastructure::sysmon_backup` | 3 | 4 | 4 | no | backup,filesystem_base |
| 29 | `puppet_infrastructure::sysmon_fs_health` | 3 | 4 | 5 | no | filesystem_base |
| 30 | `puppet_infrastructure::sysmon_integrity_master` | 3 | 4 | 5 | no | filesystem_base |
| 31 | `puppet_infrastructure::sysmon_integrity_node` | 3 | 4 | 5 | no | filesystem_base |
| 32 | `puppet_infrastructure::sysmon_mysqldump_health` | 3 | 4 | 5 | no | filesystem_base |
| 33 | `puppet_infrastructure::sync` | 4 | 3 | 4 | no | filesystem_base |
| 34 | `puppet_infrastructure::nginx_proxy_smtp_auth_ppa` | 4 | 4 | 5 | no | filesystem_base |
| 35 | `puppet_infrastructure::linux_policies_common` | 4 | 5 | 5 | no | filesystem_base |
| 36 | `puppet_infrastructure::linux_policies_user` | 4 | 4 | 5 | no | linux_policies_common |
| 37 | `puppet_infrastructure::hello_world_flask` | 5 | 4 | 5 | no | hello_world_flask_common,filesystem_base |
| 38 | `puppet_infrastructure::postfix_smtp_node` | 6 | 4 | 6 | yes |  |
| 39 | `puppet_infrastructure::letsencrypt_base` | 6 | 7 | 5 | no | filesystem_base |
| 40 | `puppet_infrastructure::letsencrypt_certificate` | 3 | 6 | 4 | no | letsencrypt_base |
| 41 | `puppet_infrastructure::packages_base` | 6 | 10 | 5 | yes | extra_packages_el |
| 42 | `puppet_infrastructure::openvpn_domain` | 7 | 4 | 6 | yes |  |
| 43 | `puppet_infrastructure::filesystem_apt` | 7 | 5 | 5 | no | filesystem_base |
| 44 | `puppet_infrastructure::user_base` | 7 | 8 | 6 | yes |  |
| 45 | `puppet_infrastructure::user` | 1 | 4 | 2 | yes | user_base |
| 46 | `puppet_infrastructure::user_desktop` | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 47 | `puppet_infrastructure::user_desktop_sudoer` | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 48 | `puppet_infrastructure::user_sudoer` | 2 | 5 | 3 | yes | user_base |
| 49 | `puppet_infrastructure::users_sudoers` | 3 | 5 | 6 | yes | user_sudoer |
| 50 | `puppet_infrastructure::firewall_secure` | 7 | 8 | 7 | no | filesystem_base |
| 51 | `puppet_infrastructure::node_base_domain_desktop` | 6 | 9 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base_desktop,filesystem_apt |
| 52 | `puppet_infrastructure::nginx_base` | 7 | 10 | 6 | no |  |
| 53 | `puppet_infrastructure::mysql_server` | 8 | 5 | 6 | no | filesystem_base |
| 54 | `puppet_infrastructure::postfix_smtp_base` | 8 | 6 | 6 | yes | ssl_postfix,postfix_smtp_base_config_file |
| 55 | `puppet_infrastructure::sysmon_base` | 8 | 8 | 6 | no | filesystem_base,packages_base |
| 56 | `puppet_infrastructure::hashman_base` | 8 | 8 | 7 | no | filesystem_base |
| 57 | `puppet_infrastructure::user_lock` | 2 | 5 | 3 | no | hashman_base |
| 58 | `puppet_infrastructure::node_base_desktop` | 8 | 10 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop_policy,filesystem_base_desktop,filesystem_apt,rsyslog_client,user_kde_lock_screen |
| 59 | `puppet_infrastructure::nginx_static_domain` | 9 | 7 | 6 | no | nginx_base,nginx_default_removal |
| 60 | `puppet_infrastructure::nginx_static` | 5 | 7 | 5 | no | nginx_base,nginx_default_removal,nginx_static_domain |
| 61 | `puppet_infrastructure::firewall_secure_extra` | 9 | 8 | 8 | no | filesystem_base |
| 62 | `puppet_infrastructure::node_base` | 9 | 10 | 6 | no | packages_base,sysmon_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base,filesystem_apt,filesystem_lib64,filesystem_sec,dns_client |
| 63 | `puppet_infrastructure::nginx_frontend_domain` | 10 | 7 | 7 | no | nginx_base,nginx_default_removal |
| 64 | `puppet_infrastructure::nginx_frontend_mail` | 8 | 7 | 6 | no | ssl_nginx_domain,nginx_frontend_domain |
| 65 | `puppet_infrastructure::nginx_frontend` | 8 | 8 | 6 | no | nginx_base,nginx_default_removal,ssl_nginx_domain,nginx_frontend_domain |
| 66 | `puppet_infrastructure::hashman_web` | 8 | 7 | 7 | no | hashman_base,nginx_frontend |

## KNOWN GAPS

node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant (routed via shared filesystem_base, which node_base already depends on) and was a considered omission, not an oversight. Revisit only if composition ever depends on it directly.
