# Puppet Class Migration Order

Generated: 2026-10-27 07:43:48 UTC

DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.

Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). The `[from: release-0.9.10]` annotation lives in migrated_classes.txt, not here.

Status summary: 31 done / 1 owner_validated / 3 blocked / 0 gated / 0 needs verification / 57 pending / 92 total.

Next class: `puppet_infrastructure::docker_container (re-migration)`

Order (step 4.3): HQ re-migrations marked `first`, then the pending queue — dependencies first, then `prod` (production node statements from `.codex_state/diagnosis/fleet_class_usage.md`, composites propagated) descending, then cx/dep/p8 — then re-migrations marked `sink`. prod 0 = no production declaration: they stay in the queue, last (HQ 2026-10-27: migrate everything).

## RE-MIGRATION QUEUE (gate-v1 done, reconciliation pending; HQ ck1 order, `.codex_state/rules/remigration_order.txt`)

| # | class | when |
|---:|---|---|
| 1 | `puppet_infrastructure::docker_container` | first |
| 2 | `puppet_infrastructure::filesystem_yum` | first |
| 3 | `puppet_infrastructure::backup_rsnapshot_pre` | first |
| 4 | `puppet_infrastructure::firewall` | sink |
| 5 | `puppet_infrastructure::sysmon_puppet_cert_status` | sink |

## DONE (git-derived)

| # | class | prod | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::dns_client` | 58 | 1 | 1 | 2 | yes |  |
| 2 | `puppet_infrastructure::nginx_default_removal` | 36 | 1 | 7 | 2 | no |  |
| 3 | `puppet_infrastructure::puppet_reports_cleanup` | 1 | 2 | 2 | 2 | yes |  |
| 4 | `puppet_infrastructure::network_dhcp` | 3 | 2 | 2 | 4 | yes |  |
| 5 | `puppet_infrastructure::network_static` | 0 | 2 | 2 | 4 | yes |  |
| 6 | `puppet_infrastructure::firewall_addon_caching_nameserver` | 3 | 2 | 2 | 5 | no |  |
| 7 | `puppet_infrastructure::firewall_addon_web` | 8 | 2 | 2 | 5 | no |  |
| 8 | `puppet_infrastructure::backup_rsnapshot_pre` | 2 | 2 | 3 | 3 | no | filesystem_base |
| 9 | `puppet_infrastructure::filesystem_lib64` | 58 | 2 | 4 | 2 | yes |  |
| 10 | `puppet_infrastructure::puppet_commush` | 2 | 2 | 4 | 3 | no | filesystem_base |
| 11 | `puppet_infrastructure::firewall_ipv6_drop` | 58 | 2 | 4 | 4 | yes |  |
| 12 | `puppet_infrastructure::firewall_ipv6_drop_policy` | 0 | 2 | 4 | 4 | yes |  |
| 13 | `puppet_infrastructure::hello_world_flask_common` | 0 | 2 | 5 | 3 | no | filesystem_base |
| 14 | `puppet_infrastructure::user_kde_lock_screen_common` | 1 | 2 | 6 | 3 | no | filesystem_base |
| 15 | `puppet_infrastructure::backup_rsnapshot` | 2 | 3 | 1 | 4 | yes |  |
| 16 | `puppet_infrastructure::openvpn_set_vpn_passwd_file` | 0 | 3 | 1 | 5 | yes |  |
| 17 | `puppet_infrastructure::caching_nameserver` | 3 | 3 | 2 | 4 | yes |  |
| 18 | `puppet_infrastructure::firewall_addon_xrdp` | 0 | 3 | 2 | 5 | no |  |
| 19 | `puppet_infrastructure::backup` | 2 | 3 | 3 | 4 | no | filesystem_base |
| 20 | `puppet_infrastructure::filesystem_sec` | 58 | 3 | 4 | 4 | no |  |
| 21 | `puppet_infrastructure::puppet_backup` | 1 | 3 | 4 | 4 | no | backup,filesystem_base |
| 22 | `puppet_infrastructure::sftp_only` | 0 | 4 | 1 | 4 | yes | ssh_secure |
| 23 | `puppet_infrastructure::docker_container` | 13 | 4 | 3 | 4 | no |  |
| 24 | `puppet_infrastructure::filesystem_yum` | 58 | 4 | 5 | 4 | no | filesystem_base |
| 25 | `puppet_infrastructure::rsyslog_client` | 57 | 4 | 6 | 3 | no | rsyslog_base |
| 26 | `puppet_infrastructure::filesystem_base_desktop` | 1 | 4 | 7 | 4 | yes |  |
| 27 | `puppet_infrastructure::sysmon_puppet_cert_status` | 0 | 5 | 5 | 5 | no | filesystem_base |
| 28 | `puppet_infrastructure::firewall` | 0 | 5 | 5 | 8 | yes |  |
| 29 | `puppet_infrastructure::ssh_secure` | 58 | 5 | 7 | 5 | yes |  |
| 30 | `puppet_infrastructure::rsyslog_base` | 58 | 5 | 8 | 5 | yes |  |
| 31 | `puppet_infrastructure::filesystem_base` | 58 | 5 | 9 | 4 | yes |  |

## OWNER-VALIDATED

| # | class | owner |
|---:|---|---|
| 1 | `puppet_infrastructure::postfix_smtp_base_config_file` | `puppet_infrastructure::postfix_smtp_base` |

## BLOCKED

| # | class | reason |
|---:|---|---|
| 1 | `puppet_infrastructure::extra_packages_el` | — blocked: CATEGORY 5 (environment-mismatch — class targets an OS the test node isn't). Two UNGUARDED exec resources with no OS-family conditional: 'install-epel-release' (dnf install of epel-release rpm) and 'enable-codeready-builder-repo' (subscription-manager). The Ubuntu test node has neither dnf nor subscription-manager, so both execs fail on run 1. NOT a code problem and NOT a harness-capability gap - the harness classifies it correctly; the code is correct for RHEL. Resolution requires a RHEL test node (a RHEL9 VM exists in VirtualBox - state unverified; batch the check with the production-inspection trip). Note a second gap sits behind this one: the harness hardcodes NODE_HOST="puppet8node", so multi-OS validation also needs node-selection capability (category 3). Contrast with filesystem_yum, which is RHEL-oriented but only DEPLOYS scripts Puppet never executes, and validated fine - the distinguishing question is whether the class EXECUTES OS-specific commands and whether that execution is guarded. See DESIGN_DECISIONS.md. |
| 2 | `puppet_infrastructure::mount_shares_desktop` | — blocked: CATEGORY 3 (harness capability/context gap) and HAND-REPAIRING NODE STATE stop. Actual run-1 errors after the Puppet 8 master successfully compiled the catalog were "Could not set 'file' on ensure: No such file or directory" for the mount script at `manifests/mount_shares_desktop.pp` line 9 and the same missing-directory error for the unmount script at line 16. That run used the now-corrected unsafe real-account params override; the observed missing-parent failure mode remains valid, but its overridden path is not the intended fixture target. Traced chain: the harness classification supplies define title `p8testuser`; the corrected untracked params fixture now preserves `username` as `p8testuser`; `manifests/mount_shares_desktop.pp:7-8` derives `$desktop_dir` as `/home/${myusername}/Desktop`; the two `File` resources at lines 9 and 16 therefore consume `/home/p8testuser/Desktop` without declaring it. The prior node probe returned `desktop_exists_rc=1`, establishing that the clean baseline does not furnish a user Desktop even for its login account; the migration plan establishes `p8testuser` as deliberately synthetic and non-existent on the node, and a repository-wide search found no manifest or required base that owns any user `Desktop` directory. The specific missing prerequisite is `/home/p8testuser/Desktop`, not Puppet 8 syntax: the catalog compiles, then application fails. Creating the directory manually would violate the hand-repair stop; making this define create it would change release-0.9.8 behaviour and ownership responsibilities. Unblock with a faithful, repeatable desktop-node test context whose baseline already includes the target user's Desktop directory, or add a harness fixture capability that establishes the externally owned prerequisite without changing this target; then revert the node and rerun the unchanged define for two clean applications. |
| 3 | `puppet_infrastructure::openvpn_nm_connection` | — blocked: CATEGORY 5 (environment mismatch — the define manages NetworkManager connections). Re-categorized 2026-10-27 (sprint 4.2): the former category-1 blocker (`Unknown function: 'fqdn_rand_uuid'`, openvpn_nm_connection.pp:29; the function exists nowhere, production master inspected 2026-09-30) has a RULED fix — fqdn_rand_uuid -> stdlib fqdn_uuid with the same seed, marker `upstream defect fixed` (HQ ck1 ruling 3; .codex_state/rules/upstream_defects.md), applied when the class is migrated. Remaining obstacle: the define notifies `exec { 'Reload Network Manager Connections: <title>': name => '/usr/bin/nmcli con reload', refreshonly }` (openvpn_nm_connection.pp:22-23); on puppet8node `command -v nmcli` = absent and NetworkManager is inactive (netplan server), so run 1 fails as soon as the connection file changes. Unblock: a NetworkManager desktop node (diagnosis C9). |

## TRANSITIVELY GATED

- None

## PENDING QUEUE

| # | class | prod | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::packages_base` | 59 | 6 | 10 | 5 | yes |  |
| 2 | `puppet_infrastructure::firewall_secure` | 59 | 7 | 8 | 7 | no | filesystem_base |
| 3 | `puppet_infrastructure::puppet_boot_run` | 58 | 3 | 4 | 4 | no | filesystem_base |
| 4 | `puppet_infrastructure::filesystem_apt` | 58 | 7 | 5 | 5 | no | filesystem_base |
| 5 | `puppet_infrastructure::sysmon_base` | 58 | 8 | 8 | 6 | no | filesystem_base,packages_base |
| 6 | `puppet_infrastructure::firewall_secure_extra` | 58 | 9 | 8 | 8 | no | filesystem_base |
| 7 | `puppet_infrastructure::node_base` | 58 | 9 | 10 | 6 | no | packages_base,sysmon_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base,filesystem_apt,filesystem_lib64,filesystem_sec,dns_client |
| 8 | `puppet_infrastructure::ssl_base` | 38 | 5 | 8 | 5 | no |  |
| 9 | `puppet_infrastructure::ssl_nginx_domain` | 37 | 2 | 7 | 4 | no | ssl_base |
| 10 | `puppet_infrastructure::nginx_base` | 33 | 7 | 10 | 6 | no |  |
| 11 | `puppet_infrastructure::nginx_frontend_domain` | 35 | 10 | 7 | 7 | no | nginx_base,nginx_default_removal |
| 12 | `puppet_infrastructure::nginx_frontend` | 24 | 8 | 8 | 6 | no | nginx_base,nginx_default_removal,ssl_nginx_domain,nginx_frontend_domain |
| 13 | `puppet_infrastructure::firewall_addon_openvpn_server` | 3 | 3 | 3 | 5 | no |  |
| 14 | `puppet_infrastructure::postfix_smtp_node` | 3 | 6 | 4 | 6 | yes |  |
| 15 | `puppet_infrastructure::user_base` | 3 | 7 | 8 | 6 | yes |  |
| 16 | `puppet_infrastructure::openvpn_server` | 3 | 9 | 6 | 7 | no |  |
| 17 | `puppet_infrastructure::network_vpn` | 3 | 8 | 7 | 6 | no | caching_nameserver,firewall_addon_caching_nameserver,firewall_addon_openvpn_server,openvpn_server |
| 18 | `puppet_infrastructure::user` | 2 | 1 | 4 | 2 | yes | user_base |
| 19 | `puppet_infrastructure::sync` | 2 | 4 | 3 | 4 | no | filesystem_base |
| 20 | `puppet_infrastructure::rsyslog_apparmor_exception` | 1 | 2 | 2 | 3 | no | rsyslog_base |
| 21 | `puppet_infrastructure::firewall_ipv6_drop_policy_desktop` | 1 | 2 | 4 | 4 | yes |  |
| 22 | `puppet_infrastructure::user_kde_lock_screen` | 1 | 2 | 5 | 3 | no | user_kde_lock_screen_common,filesystem_base,user_base |
| 23 | `puppet_infrastructure::user_sudoer` | 1 | 2 | 5 | 3 | yes | user_base |
| 24 | `puppet_infrastructure::gnome_lock_screen` | 1 | 3 | 2 | 3 | yes |  |
| 25 | `puppet_infrastructure::sysmon_backup` | 1 | 3 | 4 | 4 | no | backup,filesystem_base |
| 26 | `puppet_infrastructure::rsyslog_server` | 1 | 4 | 6 | 3 | no | rsyslog_base |
| 27 | `puppet_infrastructure::letsencrypt_base` | 1 | 6 | 7 | 5 | no | filesystem_base |
| 28 | `puppet_infrastructure::mysql_server` | 1 | 7 | 5 | 6 | no |  |
| 29 | `puppet_infrastructure::hashman_base` | 1 | 8 | 8 | 7 | no | filesystem_base |
| 30 | `puppet_infrastructure::hashman_web` | 1 | 8 | 7 | 7 | no | hashman_base,nginx_frontend |
| 31 | `puppet_infrastructure::nginx_static_domain` | 1 | 9 | 7 | 6 | no | nginx_base,nginx_default_removal |
| 32 | `puppet_infrastructure::firewall_addon_hosting` | 0 | 2 | 2 | 5 | no |  |
| 33 | `puppet_infrastructure::user_desktop` | 0 | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 34 | `puppet_infrastructure::user_desktop_sudoer` | 0 | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 35 | `puppet_infrastructure::user_lock` | 0 | 2 | 5 | 3 | no | hashman_base |
| 36 | `puppet_infrastructure::ssl_postfix` | 0 | 2 | 6 | 4 | no | ssl_base |
| 37 | `puppet_infrastructure::ssl_nginx` | 0 | 2 | 7 | 4 | no | ssl_base |
| 38 | `puppet_infrastructure::mysql_db` | 0 | 3 | 2 | 4 | no | mysql_server |
| 39 | `puppet_infrastructure::user_sysmon` | 0 | 3 | 4 | 4 | yes |  |
| 40 | `puppet_infrastructure::sysmon_fs_health` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 41 | `puppet_infrastructure::sysmon_integrity_master` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 42 | `puppet_infrastructure::sysmon_integrity_node` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 43 | `puppet_infrastructure::sysmon_mysqldump_health` | 0 | 3 | 4 | 5 | no | filesystem_base |
| 44 | `puppet_infrastructure::users_sudoers` | 0 | 3 | 5 | 6 | yes | user_sudoer |
| 45 | `puppet_infrastructure::letsencrypt_certificate` | 0 | 3 | 6 | 4 | no | letsencrypt_base |
| 46 | `puppet_infrastructure::user_samba` | 0 | 4 | 2 | 6 | no |  |
| 47 | `puppet_infrastructure::nginx_proxy_smtp_auth_ppa` | 0 | 4 | 4 | 5 | no | filesystem_base |
| 48 | `puppet_infrastructure::linux_policies_common` | 0 | 4 | 5 | 5 | no | filesystem_base |
| 49 | `puppet_infrastructure::linux_policies_user` | 0 | 4 | 4 | 5 | no | linux_policies_common |
| 50 | `puppet_infrastructure::hello_world_flask` | 0 | 5 | 4 | 5 | no | hello_world_flask_common,filesystem_base |
| 51 | `puppet_infrastructure::nginx_static` | 0 | 5 | 7 | 5 | no | nginx_base,nginx_default_removal,nginx_static_domain |
| 52 | `puppet_infrastructure::node_base_domain_desktop` | 0 | 6 | 9 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base_desktop,filesystem_apt |
| 53 | `puppet_infrastructure::openvpn_domain` | 0 | 7 | 4 | 6 | yes |  |
| 54 | `puppet_infrastructure::mariadb_server` | 0 | 8 | 4 | 6 | no | filesystem_base |
| 55 | `puppet_infrastructure::postfix_smtp_base` | 0 | 8 | 6 | 6 | yes | ssl_postfix,postfix_smtp_base_config_file |
| 56 | `puppet_infrastructure::nginx_frontend_mail` | 0 | 8 | 7 | 6 | no | ssl_nginx_domain,nginx_frontend_domain |
| 57 | `puppet_infrastructure::node_base_desktop` | 0 | 8 | 10 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop_policy,filesystem_base_desktop,filesystem_apt,rsyslog_client,user_kde_lock_screen |

## UPSTREAM DEFECTS FIXED LOCALLY (tracker markers; list: .codex_state/upstream_defects.md)

- `puppet_infrastructure::filesystem_sec` [from: release-0.9.10] — default group assigned to a new variable (no parameter reassignment)

## KNOWN GAPS

node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant (routed via shared filesystem_base, which node_base already depends on) and was a considered omission, not an oversight. Revisit only if composition ever depends on it directly.
