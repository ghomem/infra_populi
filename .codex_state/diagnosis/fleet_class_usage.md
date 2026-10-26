# Fleet class usage — puppet_infrastructure classes vs production node declarations

Generated 2026-10-26 by the engine diagnosis (read-only). Sources: `~/work/puppet-nodes` (fleet, HEAD 0941beb, 2026-10-21), `~/work/meaningful_puppet` (company layer, HEAD a3c8910, 2026-06-02), `~/work/infra_populi` manifests (87) plus `release-0.9.8` upstream for the 3 classes missing locally. Only class names and aggregate counts appear here; no node names, hostnames, values or credentials were copied. Script: scratchpad `fleet_usage.py` (not committed; regenerable).

## Method and caveats (read first)

- Node population: 47 `node` statements parsed (one per file). Production = every group except `deleted/` and `tests/`. Counts are **node statements**: server statements = 58 (matches the CTO document's 58 cloud servers exactly); the single `desktops/` statement is a regex node which the CTO document says covers 20 laptops (8 Kubuntu, 12 Ubuntu 24.04) — shown as 1 statement (≈20 machines). Deleted = 9 statements, tests = 1.
- A class counts for a node if declared directly, via a `meaningful_puppet::*` class the node declares, or via a `puppet_infrastructure` composite (`node_base*`, `nginx_frontend`, `network_vpn`, `postfix_smtp_base`, ...). Detection: regex over `include`/`require`/`contain`/`class { }`/define declarations with comments stripped. `Class[...]`/`File[...]` references do not count.
- The closure is **unconditional**: OS- or parameter-conditional includes count as if always taken; rows with a `conditional` note overstate usage. 8 node files mention RedHat/rhel (52 mentions) so RHEL servers plausibly exist, but which ones was not read (unverified).
- **The `passwd/` layer was not read (off-limits).** Node files reference 8 distinct `passwd_*` classes, 188 times in total (per-class names reduced to a count before commit, ruling 12). Hashman writes user definitions into that layer, so **user_base, user, user_sudoer, users_sudoers, user_lock, user_samba, user_sysmon, sftp_only, backup, backup_rsnapshot*, sync and letsencrypt_certificate are almost certainly under-counted** — their production declarations live in `passwd_*` classes. A 0 for those means "not declared in node files", not "unused". The lab master's node definition also includes `passwd_common` (see diagnosis §D).
- Other namespaces declared directly by nodes and not resolved: `docker` (17 node stmts), `gitlab` (2), `ssl_certificates` (1), `sysmon_web_users` (1). `common.pp` is 332 lines of variables, no classes.

## Headline numbers

- 90 classes analysed (87 local + 3 only in release-0.9.8). 23 classes sit on 24+ production node statements; 33 classes have zero declarations anywhere in node files (including deleted/ and tests/).
- High-use classes NOT done (13): extra_packages_el (59, BLOCKED(cat 5)), firewall_secure (59, PENDING), packages_base (59, PENDING), filesystem_apt (58, PENDING), firewall_secure_extra (58, PENDING), node_base (58, PENDING), puppet_boot_run (58, PENDING), sysmon_base (58, PENDING), ssl_base (38, PENDING), ssl_nginx_domain (37, PENDING), nginx_frontend_domain (35, PENDING), nginx_base (33, PENDING), nginx_frontend (24, PENDING).
- High-use classes done (10): dns_client (58), filesystem_base (58), filesystem_lib64 (58), filesystem_sec (58), filesystem_yum (58), firewall_ipv6_drop (58), rsyslog_base (58), ssh_secure (58), rsyslog_client (57), nginx_default_removal (36).
- Missing locally but used in production: firewall_ipv6_drop_policy_desktop (1 node stmt via via_meaningful_puppet), gnome_lock_screen (1 node stmt via via_meaningful_puppet), rsyslog_apparmor_exception (1 node stmt via direct).
- `node_base` is declared directly by every one of the 58 server statements (and by all 9 deleted and the 1 test node); `node_base_desktop`/`node_base_domain_desktop` are declared by nobody — the desktop fleet uses `meaningful_puppet::meaningful_desktop` instead.

## Class table (sorted by production node statements)

| class | prod | servers | desktop stmts | deleted | tests | via | conditional | migration status |
|---|---:|---:|---|---:|---:|---|---|---|
| `extra_packages_el` | 59 | 58 | 1 (≈20) | 9 | 1 | via_composite=69 | RedHat-only (packages_base.pp:28-29) | BLOCKED(cat 5) |
| `firewall_secure` | 59 | 58 | 1 (≈20) | 9 | 1 | via_composite=68, via_meaningful_puppet=1 | node_base else-branch (node_base.pp:100-101); unconditional in meaningful_desktop | PENDING |
| `packages_base` | 59 | 58 | 1 (≈20) | 9 | 1 | via_composite=68, via_meaningful_puppet=1 |  | PENDING |
| `dns_client` | 58 | 58 | 0 | 9 | 1 | via_composite=68 |  | DONE |
| `filesystem_apt` | 58 | 58 | 0 | 9 | 1 | via_composite=68 | non-RedHat branch (node_base.pp:113-115) | PENDING |
| `filesystem_base` | 58 | 58 | 0 | 9 | 1 | via_composite=68 |  | DONE |
| `filesystem_lib64` | 58 | 58 | 0 | 9 | 1 | via_composite=68 | non-RedHat branch (node_base.pp:113) | DONE |
| `filesystem_sec` | 58 | 58 | 0 | 9 | 1 | via_composite=68 | only if $filesystem_security (node_base.pp:131-132) | DONE |
| `filesystem_yum` | 58 | 58 | 0 | 9 | 1 | via_composite=68 | RedHat-only (node_base.pp:110-111) | DONE |
| `firewall_ipv6_drop` | 58 | 58 | 0 | 9 | 1 | via_composite=68 |  | DONE |
| `firewall_secure_extra` | 58 | 58 | 0 | 9 | 1 | via_composite=68 | only if $firewall_secure_extra (node_base.pp:79-80) | PENDING |
| `node_base` | 58 | 58 | 0 | 9 | 1 | direct=68 |  | PENDING |
| `puppet_boot_run` | 58 | 58 | 0 | 9 | 1 | via_composite=68 | only if $run_puppet_on_boot (node_base.pp:163-164) | PENDING |
| `rsyslog_base` | 58 | 57 | 1 (≈20) | 1 | 0 | via_composite=59 |  | DONE |
| `ssh_secure` | 58 | 58 | 0 | 9 | 1 | via_composite=68 |  | DONE |
| `sysmon_base` | 58 | 58 | 0 | 9 | 1 | via_composite=68 |  | PENDING |
| `rsyslog_client` | 57 | 56 | 1 (≈20) | 1 | 0 | direct=57, via_meaningful_puppet=1 |  | DONE |
| `ssl_base` | 38 | 38 | 0 | 5 | 1 | direct=1, via_composite=43 |  | PENDING |
| `ssl_nginx_domain` | 37 | 37 | 0 | 5 | 1 | direct=1, via_composite=31, via_meaningful_puppet=11 |  | PENDING |
| `nginx_default_removal` | 36 | 36 | 0 | 5 | 1 | via_composite=42 |  | DONE |
| `nginx_frontend_domain` | 35 | 35 | 0 | 5 | 1 | via_composite=30, via_meaningful_puppet=11 |  | PENDING |
| `nginx_base` | 33 | 33 | 0 | 5 | 1 | direct=16, via_meaningful_puppet=23 |  | PENDING |
| `nginx_frontend` | 24 | 24 | 0 | 5 | 1 | direct=16, via_composite=1, via_meaningful_puppet=13 |  | PENDING |
| `docker_container` | 13 | 13 | 0 | 3 | 0 | direct=16 |  | DONE |
| `firewall_addon_web` | 8 | 8 | 0 | 5 | 1 | direct=14 |  | DONE |
| `caching_nameserver` | 3 | 3 | 0 | 0 | 0 | via_composite=3 |  | DONE |
| `firewall_addon_caching_nameserver` | 3 | 3 | 0 | 0 | 0 | via_composite=3 |  | DONE |
| `firewall_addon_openvpn_server` | 3 | 3 | 0 | 0 | 0 | via_composite=3 |  | BLOCKED(cat 1) |
| `network_dhcp` | 3 | 3 | 0 | 0 | 0 | direct=3 |  | DONE |
| `network_vpn` | 3 | 3 | 0 | 0 | 0 | direct=3 |  | GATED |
| `openvpn_server` | 3 | 3 | 0 | 0 | 0 | via_composite=3 |  | PENDING |
| `postfix_smtp_node` | 3 | 3 | 0 | 1 | 0 | direct=4 |  | PENDING |
| `user_base` | 3 | 3 | 0 | 2 | 0 | via_composite=5 |  | PENDING |
| `backup` | 2 | 2 | 0 | 0 | 0 | via_composite=2 |  | DONE |
| `backup_rsnapshot` | 2 | 2 | 0 | 0 | 0 | direct=2 |  | DONE |
| `backup_rsnapshot_pre` | 2 | 2 | 0 | 0 | 0 | direct=2 |  | DONE |
| `puppet_commush` | 2 | 2 | 0 | 0 | 0 | direct=2 |  | DONE |
| `sync` | 2 | 2 | 0 | 0 | 0 | direct=2 |  | PENDING |
| `user` | 2 | 2 | 0 | 2 | 0 | direct=4 |  | PENDING |
| `filesystem_base_desktop` | 1 | 0 | 1 (≈20) | 0 | 0 | via_meaningful_puppet=1 |  | DONE |
| `firewall_ipv6_drop_policy_desktop` | 1 | 0 | 1 (≈20) | 0 | 0 | via_meaningful_puppet=1 |  | MISSING_LOCALLY |
| `gnome_lock_screen` | 1 | 0 | 1 (≈20) | 0 | 0 | via_meaningful_puppet=1 |  | MISSING_LOCALLY |
| `hashman_base` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `hashman_web` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `letsencrypt_base` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `mysql_server` | 1 | 1 | 0 | 1 | 0 | direct=2 |  | PENDING |
| `nginx_static_domain` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `puppet_backup` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | DONE |
| `puppet_reports_cleanup` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | DONE |
| `rsyslog_apparmor_exception` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | MISSING_LOCALLY |
| `rsyslog_server` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `sysmon_backup` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `user_kde_lock_screen` | 1 | 0 | 1 (≈20) | 0 | 0 | via_meaningful_puppet=1 |  | PENDING |
| `user_kde_lock_screen_common` | 1 | 0 | 1 (≈20) | 0 | 0 | via_composite=1 |  | DONE |
| `user_sudoer` | 1 | 1 | 0 | 0 | 0 | direct=1 |  | PENDING |
| `firewall` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `firewall_addon_hosting` | 0 | 0 | 0 | 0 | 0 | - |  | BLOCKED(cat 3) |
| `firewall_addon_xrdp` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `firewall_ipv6_drop_policy` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `hello_world_flask` | 0 | 0 | 0 | 0 | 1 | direct=1 |  | PENDING |
| `hello_world_flask_common` | 0 | 0 | 0 | 0 | 1 | via_composite=1 |  | DONE |
| `letsencrypt_certificate` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `linux_policies_common` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `linux_policies_user` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `mount_shares_desktop` | 0 | 0 | 0 | 0 | 0 | - |  | BLOCKED(cat 3) |
| `network_static` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `nginx_frontend_mail` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `nginx_proxy_smtp_auth_ppa` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `nginx_static` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `node_base_desktop` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `node_base_domain_desktop` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `openvpn_domain` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `openvpn_nm_connection` | 0 | 0 | 0 | 0 | 0 | - |  | BLOCKED(cat 1) |
| `openvpn_set_vpn_passwd_file` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `postfix_smtp_base` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `postfix_smtp_base_config_file` | 0 | 0 | 0 | 0 | 0 | - |  | OWNER_VALIDATED |
| `sftp_only` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `ssl_nginx` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `ssl_postfix` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `sysmon_fs_health` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `sysmon_integrity_master` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `sysmon_integrity_node` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `sysmon_mysqldump_health` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `sysmon_puppet_cert_status` | 0 | 0 | 0 | 0 | 0 | - |  | DONE |
| `user_desktop` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `user_desktop_sudoer` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `user_lock` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |
| `user_samba` | 0 | 0 | 0 | 0 | 0 | - |  | BLOCKED(cat 5) |
| `user_sysmon` | 0 | 0 | 0 | 0 | 0 | - |  | BLOCKED(cat 1) |
| `users_sudoers` | 0 | 0 | 0 | 0 | 0 | - |  | PENDING |

## Zero-declaration classes (candidates for not migrating, subject to the passwd caveat)

- `firewall` — DONE
- `firewall_addon_hosting` — BLOCKED(cat 3)
- `firewall_addon_xrdp` — DONE
- `firewall_ipv6_drop_policy` — DONE
- `letsencrypt_certificate` — PENDING
- `linux_policies_common` — PENDING
- `linux_policies_user` — PENDING
- `mount_shares_desktop` — BLOCKED(cat 3)
- `network_static` — DONE
- `nginx_frontend_mail` — PENDING
- `nginx_proxy_smtp_auth_ppa` — PENDING
- `nginx_static` — PENDING
- `node_base_desktop` — PENDING
- `node_base_domain_desktop` — PENDING
- `openvpn_domain` — PENDING
- `openvpn_nm_connection` — BLOCKED(cat 1)
- `openvpn_set_vpn_passwd_file` — DONE
- `postfix_smtp_base` — PENDING
- `postfix_smtp_base_config_file` — OWNER_VALIDATED
- `sftp_only` — DONE
- `ssl_nginx` — PENDING
- `ssl_postfix` — PENDING
- `sysmon_fs_health` — PENDING
- `sysmon_integrity_master` — PENDING
- `sysmon_integrity_node` — PENDING
- `sysmon_mysqldump_health` — PENDING
- `sysmon_puppet_cert_status` — DONE
- `user_desktop` — PENDING
- `user_desktop_sudoer` — PENDING
- `user_lock` — PENDING
- `user_samba` — BLOCKED(cat 5)
- `user_sysmon` — BLOCKED(cat 1)
- `users_sudoers` — PENDING

Declared only in `tests/`: `hello_world_flask`, `hello_world_flask_common`.
Declared only in `deleted/`: none.

## meaningful_puppet (company layer) → puppet_infrastructure dependencies

| meaningful_puppet class | kind | prod node stmts | direct puppet_infrastructure deps | closure size | external modules |
|---|---|---:|---|---:|---|
| `adam_nginx` | class | 12 | nginx_base, nginx_frontend | 6 | - |
| `disable_usb_storage` | class | 0 | - | 0 | - |
| `docker_dev_script` | class | 0 | - | 0 | - |
| `docker_gitlab_prune` | class | 1 | - | 0 | - |
| `docker_gitlab_registry_gc` | class | 1 | - | 0 | - |
| `docker_prune` | class | 18 | - | 0 | - |
| `gitlab_backup_verify` | class | 1 | - | 0 | - |
| `log_scanner` | class | 1 | - | 0 | - |
| `md_simple_app` | class | 1 | nginx_frontend | 5 | - |
| `meaningful_desktop` | class | 1 | filesystem_base_desktop, firewall_ipv6_drop_policy_desktop, firewall_secure, gnome_lock_screen, packages_base, rsyslog_client, user_kde_lock_screen | 10 | - |
| `postgresql_backup` | class | 3 | - | 0 | - |
| `postgresql_db` | define | 2 | - | 0 | - |
| `postgresql_server` | class | 6 | - | 0 | postgresql::globals, postgresql::server |
| `vtlsuite_docker` | class | 3 | - | 0 | - |
| `vtlsuite_docker2` | class | 3 | - | 0 | - |
| `vtlsuite_nginx` | class | 8 | nginx_base, nginx_frontend_domain, ssl_nginx_domain | 5 | - |
| `vtlsuite_nginx2` | class | 8 | nginx_base, nginx_frontend_domain, ssl_nginx_domain | 5 | - |
| `webfilter_master` | class | 1 | - | 0 | - |

Full puppet_infrastructure closure per company class (what the company layer breaks on):

- `adam_nginx` (12 node stmts) → nginx_base, nginx_default_removal, nginx_frontend, nginx_frontend_domain, ssl_base, ssl_nginx_domain
- `md_simple_app` (1 node stmts) → nginx_default_removal, nginx_frontend, nginx_frontend_domain, ssl_base, ssl_nginx_domain
- `meaningful_desktop` (1 node stmts) → extra_packages_el, filesystem_base_desktop, firewall_ipv6_drop_policy_desktop, firewall_secure, gnome_lock_screen, packages_base, rsyslog_base, rsyslog_client, user_kde_lock_screen, user_kde_lock_screen_common
- `vtlsuite_nginx` (8 node stmts) → nginx_base, nginx_default_removal, nginx_frontend_domain, ssl_base, ssl_nginx_domain
- `vtlsuite_nginx2` (8 node stmts) → nginx_base, nginx_default_removal, nginx_frontend_domain, ssl_base, ssl_nginx_domain

## Composite classes and what they pull in (local manifests, unconditional)

- `node_base` → dns_client, filesystem_apt, filesystem_base, filesystem_lib64, filesystem_sec, filesystem_yum, firewall_ipv6_drop, firewall_secure, firewall_secure_extra, packages_base, puppet_boot_run, ssh_secure, sysmon_base
- `node_base_desktop` → filesystem_apt, filesystem_base_desktop, firewall_ipv6_drop_policy, firewall_secure, packages_base, rsyslog_client, ssh_secure, user_kde_lock_screen
- `node_base_domain_desktop` → filesystem_apt, filesystem_base_desktop, firewall_ipv6_drop, firewall_secure, packages_base, ssh_secure
- `network_vpn` → caching_nameserver, firewall_addon_caching_nameserver, firewall_addon_openvpn_server, openvpn_server
- `nginx_frontend` → nginx_default_removal, nginx_frontend_domain, ssl_nginx_domain
- `nginx_static` → nginx_default_removal, nginx_static_domain
- `postfix_smtp_base` → postfix_smtp_base_config_file, ssl_postfix
- `hashman_web` → nginx_frontend
- `user_desktop` → user_base, user_kde_lock_screen
- `user_desktop_sudoer` → user_base, user_kde_lock_screen
- `users_sudoers` → -
- `puppet_backup` → backup, puppet_backup
- `sysmon_backup` → backup, sysmon_backup
- `hello_world_flask` → hello_world_flask_common
