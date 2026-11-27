# Puppet Class Migration Order

Generated: 2026-11-27 18:14:32 UTC

DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.

Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). The `[from: release-0.9.10]` annotation lives in migrated_classes.txt, not here.

Status summary: 90 done / 1 owner_validated / 0 blocked / 0 gated / 0 needs verification / 0 pending / 1 retired / 92 total.

Next class: all migrated

Order (step 4.3): HQ re-migrations marked `first`, then the pending queue — dependencies first, then `prod` (production MACHINES: servers + 20 per desktop regex statement, from `.codex_state/diagnosis/fleet_class_usage.md`, composites propagated) descending, then cx/dep/p8 — then re-migrations marked `sink`. prod 0 = no production declaration: they stay in the queue, last (HQ 2026-10-27: migrate everything).

## RE-MIGRATION QUEUE (gate-v1 done, reconciliation pending; HQ ck1 order, `.codex_state/rules/remigration_order.txt`)

| # | class | when |
|---:|---|---|
| - | - | - |

## DONE (git-derived)

| # | class | prod | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | `infra_populi::dns_client` | 58 | 1 | 1 | 2 | yes |  |
| 2 | `infra_populi::user` | 2 | 1 | 4 | 2 | yes | user_base |
| 3 | `infra_populi::nginx_default_removal` | 36 | 1 | 7 | 2 | no |  |
| 4 | `infra_populi::puppet_reports_cleanup` | 1 | 2 | 2 | 2 | yes |  |
| 5 | `infra_populi::rsyslog_apparmor_exception` | 1 | 2 | 2 | 3 | no | rsyslog_base |
| 6 | `infra_populi::network_dhcp` | 3 | 2 | 2 | 4 | yes |  |
| 7 | `infra_populi::network_static` | 0 | 2 | 2 | 4 | yes |  |
| 8 | `infra_populi::firewall_addon_caching_nameserver` | 3 | 2 | 2 | 5 | no |  |
| 9 | `infra_populi::firewall_addon_hosting` | 0 | 2 | 2 | 5 | no |  |
| 10 | `infra_populi::firewall_addon_web` | 8 | 2 | 2 | 5 | no |  |
| 11 | `infra_populi::backup_rsnapshot_pre` | 2 | 2 | 3 | 3 | no | filesystem_base |
| 12 | `infra_populi::filesystem_lib64` | 58 | 2 | 4 | 2 | yes |  |
| 13 | `infra_populi::puppet_commush` | 2 | 2 | 4 | 3 | no | filesystem_base |
| 14 | `infra_populi::firewall_ipv6_drop` | 58 | 2 | 4 | 4 | yes |  |
| 15 | `infra_populi::firewall_ipv6_drop_policy` | 0 | 2 | 4 | 4 | yes |  |
| 16 | `infra_populi::firewall_ipv6_drop_policy_desktop` | 20 | 2 | 4 | 4 | yes |  |
| 17 | `infra_populi::hello_world_flask_common` | 0 | 2 | 5 | 3 | no | filesystem_base |
| 18 | `infra_populi::user_desktop` | 0 | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 19 | `infra_populi::user_desktop_sudoer` | 0 | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 20 | `infra_populi::user_kde_lock_screen` | 20 | 2 | 5 | 3 | no | user_kde_lock_screen_common,filesystem_base,user_base |
| 21 | `infra_populi::user_lock` | 0 | 2 | 5 | 3 | no | hashman_base |
| 22 | `infra_populi::user_sudoer` | 1 | 2 | 5 | 3 | yes | user_base |
| 23 | `infra_populi::user_kde_lock_screen_common` | 20 | 2 | 6 | 3 | no | filesystem_base |
| 24 | `infra_populi::ssl_postfix` | 0 | 2 | 6 | 4 | no | ssl_base |
| 25 | `infra_populi::ssl_nginx` | 0 | 2 | 7 | 4 | no | ssl_base |
| 26 | `infra_populi::ssl_nginx_domain` | 37 | 2 | 7 | 4 | no | ssl_base |
| 27 | `infra_populi::backup_rsnapshot` | 2 | 3 | 1 | 4 | yes |  |
| 28 | `infra_populi::openvpn_set_vpn_passwd_file` | 0 | 3 | 1 | 5 | yes |  |
| 29 | `infra_populi::gnome_lock_screen` | 20 | 3 | 2 | 3 | yes |  |
| 30 | `infra_populi::caching_nameserver` | 3 | 3 | 2 | 4 | yes |  |
| 31 | `infra_populi::mysql_db` | 0 | 3 | 2 | 4 | no | mysql_server |
| 32 | `infra_populi::firewall_addon_xrdp` | 0 | 3 | 2 | 5 | no |  |
| 33 | `infra_populi::backup` | 2 | 3 | 3 | 4 | no | filesystem_base |
| 34 | `infra_populi::firewall_addon_openvpn_server` | 3 | 3 | 3 | 5 | no |  |
| 35 | `infra_populi::extra_packages_el` | 78 | 3 | 4 | 3 | yes |  |
| 36 | `infra_populi::filesystem_sec` | 58 | 3 | 4 | 4 | no |  |
| 37 | `infra_populi::puppet_backup` | 1 | 3 | 4 | 4 | no | backup,filesystem_base |
| 38 | `infra_populi::puppet_boot_run` | 58 | 3 | 4 | 4 | no | filesystem_base |
| 39 | `infra_populi::sysmon_backup` | 1 | 3 | 4 | 4 | no | backup,filesystem_base |
| 40 | `infra_populi::user_sysmon` | 0 | 3 | 4 | 4 | yes |  |
| 41 | `infra_populi::sysmon_fs_health` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 42 | `infra_populi::sysmon_integrity_master` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 43 | `infra_populi::sysmon_integrity_node` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 44 | `infra_populi::sysmon_mysqldump_health` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 45 | `infra_populi::users_sudoers` | 0 | 3 | 5 | 6 | yes | user_sudoer |
| 46 | `infra_populi::letsencrypt_certificate` | 0 | 3 | 6 | 4 | no | letsencrypt_base |
| 47 | `infra_populi::sftp_only` | 0 | 4 | 1 | 4 | yes | ssh_secure |
| 48 | `infra_populi::mount_shares_desktop` | 0 | 4 | 1 | 5 | yes |  |
| 49 | `infra_populi::openvpn_nm_connection` | 0 | 4 | 2 | 5 | no |  |
| 50 | `infra_populi::user_samba` | 0 | 4 | 2 | 6 | no |  |
| 51 | `infra_populi::docker_container` | 13 | 4 | 3 | 4 | no |  |
| 52 | `infra_populi::sync` | 2 | 4 | 3 | 4 | no | filesystem_base |
| 53 | `infra_populi::linux_policies_user` | 0 | 4 | 4 | 5 | no | linux_policies_common |
| 54 | `infra_populi::filesystem_yum` | 58 | 4 | 5 | 4 | no | filesystem_base |
| 55 | `infra_populi::linux_policies_common` | 0 | 4 | 5 | 5 | no | filesystem_base |
| 56 | `infra_populi::rsyslog_client` | 76 | 4 | 6 | 3 | no | rsyslog_base |
| 57 | `infra_populi::rsyslog_server` | 1 | 4 | 6 | 3 | no | rsyslog_base |
| 58 | `infra_populi::filesystem_base_desktop` | 20 | 4 | 7 | 4 | yes |  |
| 59 | `infra_populi::hello_world_flask` | 0 | 5 | 4 | 5 | no | hello_world_flask_common,filesystem_base |
| 60 | `infra_populi::sysmon_puppet_cert_status` | 0 | 5 | 5 | 5 | no | filesystem_base |
| 61 | `infra_populi::firewall` | 0 | 5 | 5 | 8 | yes |  |
| 62 | `infra_populi::nginx_static` | 0 | 5 | 7 | 5 | no | nginx_base,nginx_default_removal,nginx_static_domain |
| 63 | `infra_populi::ssh_secure` | 58 | 5 | 7 | 5 | yes |  |
| 64 | `infra_populi::rsyslog_base` | 77 | 5 | 8 | 5 | yes |  |
| 65 | `infra_populi::ssl_base` | 38 | 5 | 8 | 5 | no |  |
| 66 | `infra_populi::filesystem_base` | 58 | 5 | 9 | 4 | yes |  |
| 67 | `infra_populi::postfix_smtp_node` | 3 | 6 | 4 | 6 | yes |  |
| 68 | `infra_populi::letsencrypt_base` | 1 | 6 | 7 | 5 | no | filesystem_base |
| 69 | `infra_populi::node_base_domain_desktop` | 0 | 6 | 9 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base_desktop,filesystem_apt |
| 70 | `infra_populi::packages_base` | 78 | 6 | 10 | 5 | yes |  |
| 71 | `infra_populi::openvpn_domain` | 0 | 7 | 4 | 6 | yes |  |
| 72 | `infra_populi::filesystem_apt` | 58 | 7 | 5 | 5 | no | filesystem_base |
| 73 | `infra_populi::mysql_server` | 1 | 7 | 5 | 6 | no |  |
| 74 | `infra_populi::user_base` | 3 | 7 | 8 | 6 | yes |  |
| 75 | `infra_populi::firewall_secure` | 78 | 7 | 8 | 7 | no | filesystem_base |
| 76 | `infra_populi::nginx_base` | 33 | 7 | 10 | 6 | no |  |
| 77 | `infra_populi::mariadb_server` | 0 | 8 | 4 | 6 | no | filesystem_base |
| 78 | `infra_populi::postfix_smtp_base` | 0 | 8 | 6 | 6 | yes | ssl_postfix,postfix_smtp_base_config_file |
| 79 | `infra_populi::network_vpn` | 3 | 8 | 7 | 6 | no | caching_nameserver,firewall_addon_caching_nameserver,firewall_addon_openvpn_server,openvpn_server |
| 80 | `infra_populi::nginx_frontend_mail` | 0 | 8 | 7 | 6 | no | ssl_nginx_domain,nginx_frontend_domain |
| 81 | `infra_populi::hashman_web` | 1 | 8 | 7 | 7 | no | hashman_base,nginx_frontend |
| 82 | `infra_populi::nginx_frontend` | 24 | 8 | 8 | 6 | no | nginx_base,nginx_default_removal,ssl_nginx_domain,nginx_frontend_domain |
| 83 | `infra_populi::sysmon_base` | 58 | 8 | 8 | 6 | no | filesystem_base,packages_base |
| 84 | `infra_populi::hashman_base` | 1 | 8 | 8 | 7 | no | filesystem_base |
| 85 | `infra_populi::node_base_desktop` | 0 | 8 | 10 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop_policy,filesystem_base_desktop,filesystem_apt,rsyslog_client,user_kde_lock_screen |
| 86 | `infra_populi::openvpn_server` | 3 | 9 | 6 | 7 | no |  |
| 87 | `infra_populi::nginx_static_domain` | 1 | 9 | 7 | 6 | no | nginx_base,nginx_default_removal |
| 88 | `infra_populi::firewall_secure_extra` | 58 | 9 | 8 | 8 | no | filesystem_base |
| 89 | `infra_populi::node_base` | 58 | 9 | 10 | 6 | no | packages_base,sysmon_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base,filesystem_apt,filesystem_lib64,filesystem_sec,dns_client |
| 90 | `infra_populi::nginx_frontend_domain` | 35 | 10 | 7 | 7 | no | nginx_base,nginx_default_removal |

## OWNER-VALIDATED

| # | class | owner |
|---:|---|---|
| 1 | `infra_populi::postfix_smtp_base_config_file` | `infra_populi::postfix_smtp_base` |

## BLOCKED

| # | class | reason |
|---:|---|---|
| - | - | - |

## TRANSITIVELY GATED

- None

## PENDING QUEUE

| # | class | prod | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---:|---|---|
| - | - | - | - | - | - | - | - |

## UPSTREAM DEFECTS FIXED LOCALLY (tracker markers; list: .codex_state/upstream_defects.md)

- `infra_populi::filesystem_sec` [from: release-0.9.10] — default group assigned to a new variable (no parameter reassignment)
- `infra_populi::firewall_addon_hosting` [from: release-0.9.10] — OUTPUT accept for the master on 8140
- `infra_populi::linux_policies_user` [from: release-0.9.10] — policy exec guarded by the script login check
- `infra_populi::mariadb_server` [from: 874f854] — certificate generation guarded by its post-condition
- `infra_populi::openvpn_nm_connection` [from: release-0.9.10] — fqdn_rand_uuid replaced by stdlib fqdn_uuid
- `infra_populi::openvpn_server` [from: release-0.9.10] — module owns the unit (duplicate service dropped, notifies retargeted)
- `infra_populi::puppet_boot_run` [from: release-0.9.10] — ensure dropped
- `infra_populi::user_base` [from: release-0.9.10] — exec guarded by its post-condition
- `infra_populi::user_lock` [from: release-0.9.10] — exec guarded by its post-condition

## RETIRED (removed from the module; tracker `Retired [reason: ...]`)

- `infra_populi::nginx_proxy_smtp_auth_ppa` — retired by Salatiel's decision (HQ 2026-11-17 ruling 3): PPA workarounds for old machines are not carried forward; the solidangle PPA publishes Ubuntu 20.04 only

## KNOWN GAPS

node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant (routed via shared filesystem_base, which node_base already depends on) and was a considered omission, not an oversight. Revisit only if composition ever depends on it directly.
