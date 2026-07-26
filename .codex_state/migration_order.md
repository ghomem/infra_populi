# Puppet Class Migration Order

Generated: 2026-07-26 17:37:20 UTC

DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.

Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). The `[from: release-0.9.8]` annotation lives in migrated_classes.txt, not here.

Status summary: 16 done / 34 blocked / 11 gated / 0 needs verification / 26 pending / 87 total.

Next class: `puppet_infrastructure::firewall_addon_openvpn_server`

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
| 1 | `puppet_infrastructure::user` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 2 | `puppet_infrastructure::network_dhcp` | — blocked: network_config custom type fails on Puppet 8 (puppet-network/puppet-filemapper won't load); reimplementation candidate preserved at .codex_state/candidates/network_dhcp.reimplemented.pp; pending HQ resolution of dependency fork (a/b/c/d). See DESIGN_DECISIONS.md. |
| 3 | `puppet_infrastructure::network_static` | — blocked: same network_config root cause (also uses network_route); puppet-network/filemapper Puppet-8 incompat; deferred with networking cluster pending module-level resolution (a: P8-compatible module, or b: fix filemapper). See DESIGN_DECISIONS.md. |
| 4 | `puppet_infrastructure::firewall_addon_hosting` | — blocked: migration is CORRECT (action=>jump, 3 lines, behaviour-preserving, verified vs release-0.9.8) and preserved at .codex_state/candidates/firewall_addon_hosting.migrated.pp; NOT a code problem. Blocked on VALIDATION: class sets OUTPUT chain purge+policy=drop allowing only RELATED/ESTABLISHED+DNS+NTP, so an isolated harness run severs the node NEW outbound to master:8140 and run 2 hangs. Class documents it requires a base firewall (firewall/firewall_secure). Unblocks when base-context harness capability exists. See DESIGN_DECISIONS.md. |
| 5 | `puppet_infrastructure::user_desktop` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 6 | `puppet_infrastructure::user_desktop_sudoer` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 7 | `puppet_infrastructure::user_kde_lock_screen` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 8 | `puppet_infrastructure::user_lock` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 9 | `puppet_infrastructure::user_sudoer` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 10 | `puppet_infrastructure::ssl_nginx_domain` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 11 | `puppet_infrastructure::backup_rsnapshot` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 12 | `puppet_infrastructure::openvpn_set_vpn_passwd_file` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 13 | `puppet_infrastructure::backup` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 14 | `puppet_infrastructure::filesystem_sec` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 15 | `puppet_infrastructure::postfix_smtp_base_config_file` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 16 | `puppet_infrastructure::user_sysmon` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 17 | `puppet_infrastructure::sysmon_fs_health` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 18 | `puppet_infrastructure::sysmon_mysqldump_health` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 19 | `puppet_infrastructure::users_sudoers` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 20 | `puppet_infrastructure::letsencrypt_certificate` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 21 | `puppet_infrastructure::sftp_only` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 22 | `puppet_infrastructure::mount_shares_desktop` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 23 | `puppet_infrastructure::openvpn_nm_connection` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 24 | `puppet_infrastructure::user_samba` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 25 | `puppet_infrastructure::docker_container` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 26 | `puppet_infrastructure::sync` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 27 | `puppet_infrastructure::linux_policies_user` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 28 | `puppet_infrastructure::hello_world_flask` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 29 | `puppet_infrastructure::ssl_base` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 30 | `puppet_infrastructure::user_base` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 31 | `puppet_infrastructure::network_vpn` | — blocked: transitively (chains openvpn_server); deferred with networking cluster pending module-level resolution. See DESIGN_DECISIONS.md. |
| 32 | `puppet_infrastructure::openvpn_server` | — blocked: heavy network_config use (lo/lo:0/br0 bridge, bridge_ports, loopback aliasing, subscribe refs); puppet-network/filemapper Puppet-8 incompat; do NOT reimplement per-class; deferred with networking cluster pending module-level resolution. See DESIGN_DECISIONS.md. |
| 33 | `puppet_infrastructure::nginx_static_domain` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |
| 34 | `puppet_infrastructure::nginx_frontend_domain` | — blocked: harness cannot classify defined types (emits 'include', which is invalid for a define; needs title + parameters). NOT a code problem — migration not yet attempted, validation capability pending. Unblocks when the harness classification recipe capability lands. See DESIGN_DECISIONS.md. |

## TRANSITIVELY GATED

- `puppet_infrastructure::ssl_postfix` — gated by blocked `puppet_infrastructure::ssl_base`
- `puppet_infrastructure::ssl_nginx` — gated by blocked `puppet_infrastructure::ssl_base`
- `puppet_infrastructure::puppet_backup` — gated by blocked `puppet_infrastructure::backup`
- `puppet_infrastructure::sysmon_backup` — gated by blocked `puppet_infrastructure::backup`
- `puppet_infrastructure::nginx_static` — gated by blocked `puppet_infrastructure::nginx_static_domain`
- `puppet_infrastructure::postfix_smtp_base` — gated by `puppet_infrastructure::ssl_postfix` → blocked `puppet_infrastructure::ssl_base`; blocked `puppet_infrastructure::postfix_smtp_base_config_file`
- `puppet_infrastructure::nginx_frontend_mail` — gated by blocked `puppet_infrastructure::ssl_nginx_domain`; blocked `puppet_infrastructure::nginx_frontend_domain`
- `puppet_infrastructure::hashman_web` — gated by `puppet_infrastructure::nginx_frontend` → blocked `puppet_infrastructure::ssl_nginx_domain`; `puppet_infrastructure::nginx_frontend` → blocked `puppet_infrastructure::nginx_frontend_domain`
- `puppet_infrastructure::nginx_frontend` — gated by blocked `puppet_infrastructure::ssl_nginx_domain`; blocked `puppet_infrastructure::nginx_frontend_domain`
- `puppet_infrastructure::node_base_desktop` — gated by blocked `puppet_infrastructure::user_kde_lock_screen`
- `puppet_infrastructure::node_base` — gated by blocked `puppet_infrastructure::filesystem_sec`

## PENDING QUEUE

| # | class | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::firewall_addon_openvpn_server` | 3 | 3 | 5 | no |  |
| 2 | `puppet_infrastructure::extra_packages_el` | 3 | 4 | 3 | yes |  |
| 3 | `puppet_infrastructure::rsyslog_server` | 4 | 6 | 3 | no | rsyslog_base |
| 4 | `puppet_infrastructure::filesystem_base_desktop` | 4 | 7 | 4 | yes |  |
| 5 | `puppet_infrastructure::ssh_secure` | 5 | 7 | 5 | yes |  |
| 6 | `puppet_infrastructure::filesystem_base` | 5 | 9 | 4 | yes |  |
| 7 | `puppet_infrastructure::puppet_commush` | 2 | 4 | 3 | no | filesystem_base |
| 8 | `puppet_infrastructure::hello_world_flask_common` | 2 | 5 | 3 | no | filesystem_base |
| 9 | `puppet_infrastructure::user_kde_lock_screen_common` | 2 | 6 | 3 | no | filesystem_base |
| 10 | `puppet_infrastructure::puppet_boot_run` | 3 | 4 | 4 | no | filesystem_base |
| 11 | `puppet_infrastructure::sysmon_integrity_master` | 3 | 4 | 5 | no | filesystem_base |
| 12 | `puppet_infrastructure::sysmon_integrity_node` | 3 | 4 | 5 | no | filesystem_base |
| 13 | `puppet_infrastructure::nginx_proxy_smtp_auth_ppa` | 4 | 4 | 5 | no | filesystem_base |
| 14 | `puppet_infrastructure::linux_policies_common` | 4 | 5 | 5 | no | filesystem_base |
| 15 | `puppet_infrastructure::postfix_smtp_node` | 6 | 4 | 6 | yes |  |
| 16 | `puppet_infrastructure::letsencrypt_base` | 6 | 7 | 5 | no | filesystem_base |
| 17 | `puppet_infrastructure::packages_base` | 6 | 10 | 5 | yes | extra_packages_el |
| 18 | `puppet_infrastructure::openvpn_domain` | 7 | 4 | 6 | yes |  |
| 19 | `puppet_infrastructure::filesystem_apt` | 7 | 5 | 5 | no | filesystem_base |
| 20 | `puppet_infrastructure::firewall_secure` | 7 | 8 | 7 | no | filesystem_base |
| 21 | `puppet_infrastructure::node_base_domain_desktop` | 6 | 9 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base_desktop,filesystem_apt |
| 22 | `puppet_infrastructure::nginx_base` | 7 | 10 | 6 | no |  |
| 23 | `puppet_infrastructure::mysql_server` | 8 | 5 | 6 | no | filesystem_base |
| 24 | `puppet_infrastructure::sysmon_base` | 8 | 8 | 6 | no | filesystem_base,packages_base |
| 25 | `puppet_infrastructure::hashman_base` | 8 | 8 | 7 | no | filesystem_base |
| 26 | `puppet_infrastructure::firewall_secure_extra` | 9 | 8 | 8 | no | filesystem_base |

## KNOWN GAPS

node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant (routed via shared filesystem_base, which node_base already depends on) and was a considered omission, not an oversight. Revisit only if composition ever depends on it directly.
