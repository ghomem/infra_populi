# Puppet Class Migration Order

Generated: 2026-07-27 19:23:00 UTC

DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.

Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). The `[from: release-0.9.8]` annotation lives in migrated_classes.txt, not here.

Status summary: 18 done / 7 blocked / 0 gated / 0 needs verification / 62 pending / 87 total.

Next class: `puppet_infrastructure::filesystem_sec`

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
| 10 | `puppet_infrastructure::backup_rsnapshot` | 3 | 1 | 4 | yes |  |
| 11 | `puppet_infrastructure::openvpn_set_vpn_passwd_file` | 3 | 1 | 5 | yes |  |
| 12 | `puppet_infrastructure::caching_nameserver` | 3 | 2 | 4 | yes |  |
| 13 | `puppet_infrastructure::firewall_addon_xrdp` | 3 | 2 | 5 | no |  |
| 14 | `puppet_infrastructure::filesystem_yum` | 4 | 5 | 4 | no | filesystem_base |
| 15 | `puppet_infrastructure::rsyslog_client` | 4 | 6 | 3 | no | rsyslog_base |
| 16 | `puppet_infrastructure::sysmon_puppet_cert_status` | 5 | 5 | 5 | no | filesystem_base |
| 17 | `puppet_infrastructure::firewall` | 5 | 5 | 8 | yes |  |
| 18 | `puppet_infrastructure::rsyslog_base` | 5 | 8 | 5 | yes |  |

## BLOCKED

| # | class | reason |
|---:|---|---|
| 1 | `puppet_infrastructure::network_dhcp` | — blocked: network_config custom type fails on Puppet 8 (puppet-network/puppet-filemapper won't load); reimplementation candidate preserved at .codex_state/candidates/network_dhcp.reimplemented.pp; pending HQ resolution of dependency fork (a/b/c/d). See DESIGN_DECISIONS.md. |
| 2 | `puppet_infrastructure::network_static` | — blocked: same network_config root cause (also uses network_route); puppet-network/filemapper Puppet-8 incompat; deferred with networking cluster pending module-level resolution (a: P8-compatible module, or b: fix filemapper). See DESIGN_DECISIONS.md. |
| 3 | `puppet_infrastructure::firewall_addon_hosting` | — blocked (RE-BLOCKED, corrected reason): migration is CORRECT and preserved at .codex_state/candidates/firewall_addon_hosting.migrated.pp. Previously blocked pending base-context harness capability; that capability now exists, but the diagnosis was WRONG. required_base has been CLEARED because no base class supplies what is missing: firewall.pp and firewall_secure.pp both state "allowing OUTPUT and specific INPUTs" - they manage INPUT/FORWARD only and never restrict OUTPUT, so neither grants outbound to master:8140. Verified no duplicate-declaration risk: firewall.pp declares firewallchain FORWARD:filter:IPv4 and INPUT:filter:IPv4 only, NOT OUTPUT:filter:IPv4 (so the addon's comment about "overriding the default OUTPUT from the firewall class" is itself inaccurate - there is no such default). The real obstacle: the addon sets OUTPUT purge+policy=drop permitting only RELATED/ESTABLISHED+DNS+NTP, with no rule for NEW outbound to master:8140, so an isolated or base-context run severs the agent and run 2 hangs. Category 3, sub-state "capability built, required input unknown" - resolution path is now information-gathering, not capability-building. Open question with three hypotheses for production inspection: (a) something else in production opens 8140; (b) genuine upstream bug production tolerates; (c) hosting servers run MASTERLESS (puppet apply + r10k) so no outbound 8140 is ever needed - in which case the class is correct in production and fundamentally untestable in an agent/master rig. Batched with the sysctl/network_config production-inspection trip. NOT a code problem. See DESIGN_DECISIONS.md. |
| 4 | `puppet_infrastructure::firewall_addon_openvpn_server` | — blocked: uses the sysctl custom type (sysctl { 'net.ipv4.ip_forward': value => '1' }); no sysctl module installed on the master and none declared upstream in metadata.json/Puppetfile. Forge search found no module stating Puppet 8 support (duritong/sysctl lists 5/6/7, last released 2018). Category 1 (dependency-incompatibility): resolve at module level, batched with the network_config investigation (same shape: which Forge module, is it Puppet-8-viable). Lead: the PRODUCTION Puppet 5 master running puppet_infrastructure must have both sysctl and network modules installed - inspect its module list for the authoritative answer rather than inferring from call syntax. NOT a code problem. When unblocked: needs params JSON (wan_iface mandatory, no default; lan_bridge_iface defaults to br0), and upstream is half-migrated (3x legacy action =>, 1x jump => 'MASQUERADE'). The sysctl resource must NOT be dropped - ip_forward=1 is what makes MASQUERADE effective; the author's "not directly related to firewall" comment is about placement, not function. See DESIGN_DECISIONS.md. |
| 5 | `puppet_infrastructure::extra_packages_el` | — blocked: CATEGORY 5 (environment-mismatch — class targets an OS the test node isn't). Two UNGUARDED exec resources with no OS-family conditional: 'install-epel-release' (dnf install of epel-release rpm) and 'enable-codeready-builder-repo' (subscription-manager). The Ubuntu test node has neither dnf nor subscription-manager, so both execs fail on run 1. NOT a code problem and NOT a harness-capability gap - the harness classifies it correctly; the code is correct for RHEL. Resolution requires a RHEL test node (a RHEL9 VM exists in VirtualBox - state unverified; batch the check with the production-inspection trip). Note a second gap sits behind this one: the harness hardcodes NODE_HOST="puppet8node", so multi-OS validation also needs node-selection capability (category 3). Contrast with filesystem_yum, which is RHEL-oriented but only DEPLOYS scripts Puppet never executes, and validated fine - the distinguishing question is whether the class EXECUTES OS-specific commands and whether that execution is guarded. See DESIGN_DECISIONS.md. |
| 6 | `puppet_infrastructure::network_vpn` | — blocked: transitively (chains openvpn_server); deferred with networking cluster pending module-level resolution. See DESIGN_DECISIONS.md. |
| 7 | `puppet_infrastructure::openvpn_server` | — blocked: heavy network_config use (lo/lo:0/br0 bridge, bridge_ports, loopback aliasing, subscribe refs); puppet-network/filemapper Puppet-8 incompat; do NOT reimplement per-class; deferred with networking cluster pending module-level resolution. See DESIGN_DECISIONS.md. |

## TRANSITIVELY GATED

- None

## PENDING QUEUE

| # | class | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::filesystem_sec` | 3 | 4 | 4 | no |  |
| 2 | `puppet_infrastructure::postfix_smtp_base_config_file` | 3 | 4 | 4 | yes |  |
| 3 | `puppet_infrastructure::user_sysmon` | 3 | 4 | 4 | yes |  |
| 4 | `puppet_infrastructure::sftp_only` | 4 | 1 | 4 | yes |  |
| 5 | `puppet_infrastructure::mount_shares_desktop` | 4 | 1 | 5 | yes |  |
| 6 | `puppet_infrastructure::openvpn_nm_connection` | 4 | 2 | 5 | no |  |
| 7 | `puppet_infrastructure::user_samba` | 4 | 2 | 6 | no |  |
| 8 | `puppet_infrastructure::docker_container` | 4 | 3 | 4 | no |  |
| 9 | `puppet_infrastructure::rsyslog_server` | 4 | 6 | 3 | no | rsyslog_base |
| 10 | `puppet_infrastructure::filesystem_base_desktop` | 4 | 7 | 4 | yes |  |
| 11 | `puppet_infrastructure::ssh_secure` | 5 | 7 | 5 | yes |  |
| 12 | `puppet_infrastructure::ssl_base` | 5 | 8 | 5 | no |  |
| 13 | `puppet_infrastructure::ssl_postfix` | 2 | 6 | 4 | no | ssl_base |
| 14 | `puppet_infrastructure::ssl_nginx` | 2 | 7 | 4 | no | ssl_base |
| 15 | `puppet_infrastructure::ssl_nginx_domain` | 2 | 7 | 4 | no | ssl_base |
| 16 | `puppet_infrastructure::filesystem_base` | 5 | 9 | 4 | yes |  |
| 17 | `puppet_infrastructure::puppet_commush` | 2 | 4 | 3 | no | filesystem_base |
| 18 | `puppet_infrastructure::hello_world_flask_common` | 2 | 5 | 3 | no | filesystem_base |
| 19 | `puppet_infrastructure::user_kde_lock_screen_common` | 2 | 6 | 3 | no | filesystem_base |
| 20 | `puppet_infrastructure::user_kde_lock_screen` | 2 | 5 | 3 | no | user_kde_lock_screen_common,filesystem_base |
| 21 | `puppet_infrastructure::backup` | 3 | 3 | 4 | no | filesystem_base |
| 22 | `puppet_infrastructure::puppet_backup` | 3 | 4 | 4 | no | backup,filesystem_base |
| 23 | `puppet_infrastructure::puppet_boot_run` | 3 | 4 | 4 | no | filesystem_base |
| 24 | `puppet_infrastructure::sysmon_backup` | 3 | 4 | 4 | no | backup,filesystem_base |
| 25 | `puppet_infrastructure::sysmon_fs_health` | 3 | 4 | 5 | no | filesystem_base |
| 26 | `puppet_infrastructure::sysmon_integrity_master` | 3 | 4 | 5 | no | filesystem_base |
| 27 | `puppet_infrastructure::sysmon_integrity_node` | 3 | 4 | 5 | no | filesystem_base |
| 28 | `puppet_infrastructure::sysmon_mysqldump_health` | 3 | 4 | 5 | no | filesystem_base |
| 29 | `puppet_infrastructure::sync` | 4 | 3 | 4 | no | filesystem_base |
| 30 | `puppet_infrastructure::nginx_proxy_smtp_auth_ppa` | 4 | 4 | 5 | no | filesystem_base |
| 31 | `puppet_infrastructure::linux_policies_common` | 4 | 5 | 5 | no | filesystem_base |
| 32 | `puppet_infrastructure::linux_policies_user` | 4 | 4 | 5 | no | linux_policies_common |
| 33 | `puppet_infrastructure::hello_world_flask` | 5 | 4 | 5 | no | hello_world_flask_common,filesystem_base |
| 34 | `puppet_infrastructure::postfix_smtp_node` | 6 | 4 | 6 | yes |  |
| 35 | `puppet_infrastructure::letsencrypt_base` | 6 | 7 | 5 | no | filesystem_base |
| 36 | `puppet_infrastructure::letsencrypt_certificate` | 3 | 6 | 4 | no | letsencrypt_base |
| 37 | `puppet_infrastructure::packages_base` | 6 | 10 | 5 | yes |  |
| 38 | `puppet_infrastructure::openvpn_domain` | 7 | 4 | 6 | yes |  |
| 39 | `puppet_infrastructure::filesystem_apt` | 7 | 5 | 5 | no | filesystem_base |
| 40 | `puppet_infrastructure::user_base` | 7 | 8 | 6 | yes |  |
| 41 | `puppet_infrastructure::user` | 1 | 4 | 2 | yes | user_base |
| 42 | `puppet_infrastructure::user_desktop` | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 43 | `puppet_infrastructure::user_desktop_sudoer` | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 44 | `puppet_infrastructure::user_sudoer` | 2 | 5 | 3 | yes | user_base |
| 45 | `puppet_infrastructure::users_sudoers` | 3 | 5 | 6 | yes | user_sudoer |
| 46 | `puppet_infrastructure::firewall_secure` | 7 | 8 | 7 | no | filesystem_base |
| 47 | `puppet_infrastructure::node_base_domain_desktop` | 6 | 9 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base_desktop,filesystem_apt |
| 48 | `puppet_infrastructure::nginx_base` | 7 | 10 | 6 | no |  |
| 49 | `puppet_infrastructure::mysql_server` | 8 | 5 | 6 | no | filesystem_base |
| 50 | `puppet_infrastructure::postfix_smtp_base` | 8 | 6 | 6 | yes | ssl_postfix,postfix_smtp_base_config_file |
| 51 | `puppet_infrastructure::sysmon_base` | 8 | 8 | 6 | no | filesystem_base,packages_base |
| 52 | `puppet_infrastructure::hashman_base` | 8 | 8 | 7 | no | filesystem_base |
| 53 | `puppet_infrastructure::user_lock` | 2 | 5 | 3 | no | hashman_base |
| 54 | `puppet_infrastructure::node_base_desktop` | 8 | 10 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop_policy,filesystem_base_desktop,filesystem_apt,rsyslog_client,user_kde_lock_screen |
| 55 | `puppet_infrastructure::nginx_static_domain` | 9 | 7 | 6 | no | nginx_base,nginx_default_removal |
| 56 | `puppet_infrastructure::nginx_static` | 5 | 7 | 5 | no | nginx_base,nginx_default_removal,nginx_static_domain |
| 57 | `puppet_infrastructure::firewall_secure_extra` | 9 | 8 | 8 | no | filesystem_base |
| 58 | `puppet_infrastructure::node_base` | 9 | 10 | 6 | no | packages_base,sysmon_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base,filesystem_apt,filesystem_lib64,filesystem_sec,dns_client |
| 59 | `puppet_infrastructure::nginx_frontend_domain` | 10 | 7 | 7 | no | nginx_base,nginx_default_removal |
| 60 | `puppet_infrastructure::nginx_frontend_mail` | 8 | 7 | 6 | no | ssl_nginx_domain,nginx_frontend_domain |
| 61 | `puppet_infrastructure::nginx_frontend` | 8 | 8 | 6 | no | nginx_base,nginx_default_removal,ssl_nginx_domain,nginx_frontend_domain |
| 62 | `puppet_infrastructure::hashman_web` | 8 | 7 | 7 | no | hashman_base,nginx_frontend |

## KNOWN GAPS

node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant (routed via shared filesystem_base, which node_base already depends on) and was a considered omission, not an oversight. Revisit only if composition ever depends on it directly.
