# Puppet Class Migration Order

Generated: 2026-10-27 05:34:54 UTC

DERIVED file: scores/deps come from `.codex_state/migration_plan.md`; DONE comes from git minus `.codex_state/blocked.txt`. MUST NOT be hand-edited; regenerate via `python3 .codex_state/gen_migration_order.py`.

Precedence: git > migrated_classes.txt (canonical) > migration_order.md (advisory). The `[from: release-0.9.10]` annotation lives in migrated_classes.txt, not here.

Status summary: 31 done / 1 owner_validated / 6 blocked / 0 gated / 0 needs verification / 52 pending / 90 total.

Next class: `puppet_infrastructure::rsyslog_apparmor_exception`

## DONE (git-derived)

| # | class | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::dns_client` | 1 | 1 | 2 | yes |  |
| 2 | `puppet_infrastructure::nginx_default_removal` | 1 | 7 | 2 | no |  |
| 3 | `puppet_infrastructure::puppet_reports_cleanup` | 2 | 2 | 2 | yes |  |
| 4 | `puppet_infrastructure::network_dhcp` | 2 | 2 | 4 | yes |  |
| 5 | `puppet_infrastructure::network_static` | 2 | 2 | 4 | yes |  |
| 6 | `puppet_infrastructure::firewall_addon_caching_nameserver` | 2 | 2 | 5 | no |  |
| 7 | `puppet_infrastructure::firewall_addon_web` | 2 | 2 | 5 | no |  |
| 8 | `puppet_infrastructure::backup_rsnapshot_pre` | 2 | 3 | 3 | no | filesystem_base |
| 9 | `puppet_infrastructure::filesystem_lib64` | 2 | 4 | 2 | yes |  |
| 10 | `puppet_infrastructure::puppet_commush` | 2 | 4 | 3 | no | filesystem_base |
| 11 | `puppet_infrastructure::firewall_ipv6_drop` | 2 | 4 | 4 | yes |  |
| 12 | `puppet_infrastructure::firewall_ipv6_drop_policy` | 2 | 4 | 4 | yes |  |
| 13 | `puppet_infrastructure::hello_world_flask_common` | 2 | 5 | 3 | no | filesystem_base |
| 14 | `puppet_infrastructure::user_kde_lock_screen_common` | 2 | 6 | 3 | no | filesystem_base |
| 15 | `puppet_infrastructure::backup_rsnapshot` | 3 | 1 | 4 | yes |  |
| 16 | `puppet_infrastructure::openvpn_set_vpn_passwd_file` | 3 | 1 | 5 | yes |  |
| 17 | `puppet_infrastructure::caching_nameserver` | 3 | 2 | 4 | yes |  |
| 18 | `puppet_infrastructure::firewall_addon_xrdp` | 3 | 2 | 5 | no |  |
| 19 | `puppet_infrastructure::backup` | 3 | 3 | 4 | no | filesystem_base |
| 20 | `puppet_infrastructure::filesystem_sec` | 3 | 4 | 4 | no |  |
| 21 | `puppet_infrastructure::puppet_backup` | 3 | 4 | 4 | no | backup,filesystem_base |
| 22 | `puppet_infrastructure::sftp_only` | 4 | 1 | 4 | yes | ssh_secure |
| 23 | `puppet_infrastructure::docker_container` | 4 | 3 | 4 | no |  |
| 24 | `puppet_infrastructure::filesystem_yum` | 4 | 5 | 4 | no | filesystem_base |
| 25 | `puppet_infrastructure::rsyslog_client` | 4 | 6 | 3 | no | rsyslog_base |
| 26 | `puppet_infrastructure::filesystem_base_desktop` | 4 | 7 | 4 | yes |  |
| 27 | `puppet_infrastructure::sysmon_puppet_cert_status` | 5 | 5 | 5 | no | filesystem_base |
| 28 | `puppet_infrastructure::firewall` | 5 | 5 | 8 | yes |  |
| 29 | `puppet_infrastructure::ssh_secure` | 5 | 7 | 5 | yes |  |
| 30 | `puppet_infrastructure::rsyslog_base` | 5 | 8 | 5 | yes |  |
| 31 | `puppet_infrastructure::filesystem_base` | 5 | 9 | 4 | yes |  |

## OWNER-VALIDATED

| # | class | owner |
|---:|---|---|
| 1 | `puppet_infrastructure::postfix_smtp_base_config_file` | `puppet_infrastructure::postfix_smtp_base` |

## BLOCKED

| # | class | reason |
|---:|---|---|
| 1 | `puppet_infrastructure::firewall_addon_hosting` | — blocked (RE-BLOCKED, corrected reason): migration is CORRECT and preserved at .codex_state/candidates/firewall_addon_hosting.migrated.pp. Previously blocked pending base-context harness capability; that capability now exists, but the diagnosis was WRONG. required_base has been CLEARED because no base class supplies what is missing: firewall.pp and firewall_secure.pp both state "allowing OUTPUT and specific INPUTs" - they manage INPUT/FORWARD only and never restrict OUTPUT, so neither grants outbound to master:8140. Verified no duplicate-declaration risk: firewall.pp declares firewallchain FORWARD:filter:IPv4 and INPUT:filter:IPv4 only, NOT OUTPUT:filter:IPv4 (so the addon's comment about "overriding the default OUTPUT from the firewall class" is itself inaccurate - there is no such default). The real obstacle: the addon sets OUTPUT purge+policy=drop permitting only RELATED/ESTABLISHED+DNS+NTP, with no rule for NEW outbound to master:8140, so an isolated or base-context run severs the agent and run 2 hangs. Category 3, sub-state "capability built, required input unknown" - resolution path is now information-gathering, not capability-building. Open question with three hypotheses for production inspection: (a) something else in production opens 8140; (b) genuine upstream bug production tolerates; (c) hosting servers run MASTERLESS (puppet apply + r10k) so no outbound 8140 is ever needed - in which case the class is correct in production and fundamentally untestable in an agent/master rig. Batched with the sysctl/network_config production-inspection trip. NOT a code problem. See DESIGN_DECISIONS.md. |
| 2 | `puppet_infrastructure::extra_packages_el` | — blocked: CATEGORY 5 (environment-mismatch — class targets an OS the test node isn't). Two UNGUARDED exec resources with no OS-family conditional: 'install-epel-release' (dnf install of epel-release rpm) and 'enable-codeready-builder-repo' (subscription-manager). The Ubuntu test node has neither dnf nor subscription-manager, so both execs fail on run 1. NOT a code problem and NOT a harness-capability gap - the harness classifies it correctly; the code is correct for RHEL. Resolution requires a RHEL test node (a RHEL9 VM exists in VirtualBox - state unverified; batch the check with the production-inspection trip). Note a second gap sits behind this one: the harness hardcodes NODE_HOST="puppet8node", so multi-OS validation also needs node-selection capability (category 3). Contrast with filesystem_yum, which is RHEL-oriented but only DEPLOYS scripts Puppet never executes, and validated fine - the distinguishing question is whether the class EXECUTES OS-specific commands and whether that execution is guarded. See DESIGN_DECISIONS.md. |
| 3 | `puppet_infrastructure::user_sysmon` | — blocked: CATEGORY 5 (environment mismatch — the define targets a Naemon/Thruk monitoring server). Re-categorized 2026-10-27 (sprint 4.1b): the former category-1 blocker is RESOLVED — citrin-htpasswd 1.0.3 replaces leinaddm-htpasswd 0.0.3 (HQ ruling 7; providers byte-identical, types identical except the Puppet-3 `module Puppet; newtype` wrapper -> `Puppet::Type.newtype`, functions renamed to htpasswd::ht_* which this define does not call); `test_class.sh --compile-only user_sysmon` = COMPILE OK on puppet8master. Remaining obstacle (evidence: manifests/user_sysmon.pp:11-18): it writes /etc/thruk/htpasswd and /etc/naemon/conf.d/contacts/<user>.cfg owned by user `naemon` — none exist on puppet8node (Ubuntu 24.04 baseline has no Thruk/Naemon). Unblock: a monitoring-server node or fixture state with Thruk+Naemon (diagnosis E.1; Salatiel-tier infrastructure). Note: citrin-htpasswd 1.0.3 metadata declares puppet >= 5.5.10 < 8.0.0 (informational; the types load on OpenVox 8.24.2). |
| 4 | `puppet_infrastructure::mount_shares_desktop` | — blocked: CATEGORY 3 (harness capability/context gap) and HAND-REPAIRING NODE STATE stop. Actual run-1 errors after the Puppet 8 master successfully compiled the catalog were "Could not set 'file' on ensure: No such file or directory" for the mount script at `manifests/mount_shares_desktop.pp` line 9 and the same missing-directory error for the unmount script at line 16. That run used the now-corrected unsafe real-account params override; the observed missing-parent failure mode remains valid, but its overridden path is not the intended fixture target. Traced chain: the harness classification supplies define title `p8testuser`; the corrected untracked params fixture now preserves `username` as `p8testuser`; `manifests/mount_shares_desktop.pp:7-8` derives `$desktop_dir` as `/home/${myusername}/Desktop`; the two `File` resources at lines 9 and 16 therefore consume `/home/p8testuser/Desktop` without declaring it. The prior node probe returned `desktop_exists_rc=1`, establishing that the clean baseline does not furnish a user Desktop even for its login account; the migration plan establishes `p8testuser` as deliberately synthetic and non-existent on the node, and a repository-wide search found no manifest or required base that owns any user `Desktop` directory. The specific missing prerequisite is `/home/p8testuser/Desktop`, not Puppet 8 syntax: the catalog compiles, then application fails. Creating the directory manually would violate the hand-repair stop; making this define create it would change release-0.9.8 behaviour and ownership responsibilities. Unblock with a faithful, repeatable desktop-node test context whose baseline already includes the target user's Desktop directory, or add a harness fixture capability that establishes the externally owned prerequisite without changing this target; then revert the node and rerun the unchanged define for two clean applications. |
| 5 | `puppet_infrastructure::openvpn_nm_connection` | — blocked: CATEGORY 1 (dependency incompatibility — a function the class calls is not available in the environment, and the resolution is at the dependency level, identical in shape to the network_config, sysctl, and htpasswd blocks; the behaviour-preservation concern is why we cannot work around it, not what the block is). Actual harness error: "Evaluation Error: Unknown function: 'fqdn_rand_uuid'. (file: /etc/puppetlabs/code/environments/production/modules/puppet_infrastructure/manifests/openvpn_nm_connection.pp, line: 29, column: 13)". Traced chain: the harness rendered define title `openvpn_nm_connection` with the untracked safe fixture (`vpn_username` and `local_username` both `p8testuser`, `remote` `127.0.0.1`, and the node-existing CA path `/etc/ssl/certs/ca-certificates.crt`); `manifests/openvpn_nm_connection.pp:29` passes `$connection_name` to `fqdn_rand_uuid`; `templates/openvpn/connection_file.erb:3` writes the return value as NetworkManager's persistent connection UUID. The upstream 0.9.8 source has that exact call and declares only `puppetlabs/stdlib >= 4.25.1`. The complete GitHub trees for Puppet 5.5.22 and stdlib 4.25.1 contain no `fqdn_rand_uuid`; stdlib 4.25.1 contains only `lib/puppet/parser/functions/fqdn_uuid.rb`, and GitHub's path history reports that no `fqdn_rand_uuid` implementation ever existed in stdlib's legacy, modern, or Puppet-language function locations. The Puppet 8 master likewise has stdlib 9.7.0 with `fqdn_uuid` but no `fqdn_rand_uuid`. Replacing the call with `fqdn_uuid($connection_name)` is the smallest apparent code fix, but it would make a release class compile by choosing an algorithm that cannot be shown to match a possible site-local production function; a different result would replace the deployed connection identity. UPSTREAM BUG HYPOTHESIS: Two hypotheses, and they have different resolutions. (a) `fqdn_rand_uuid` is a SITE-LOCAL function in the production Puppet 5 modulepath that upstream never declared as a dependency — in which case the class has an undeclared dependency and the exact algorithm must be ported. (b) It is an UPSTREAM TYPO that has never worked: stdlib provides both `fqdn_rand` and `fqdn_uuid`, and `fqdn_rand_uuid` reads as a conflation of the two; the search found no evidence it ever existed in stdlib's legacy, modern, or Puppet-language function locations, nor in Puppet 5.5.22 core. If (b), this class has never compiled anywhere and the defect predates the migration entirely — a genuine upstream bug worth reporting to the maintainers independently of this work. Settle it by inspecting the production Puppet 5 master's modulepath for any `fqdn_rand_uuid` implementation: if one exists, hypothesis (a) holds and its algorithm must be ported; if none exists, hypothesis (b) is confirmed and the correction is an authorized bug fix rather than a behaviour change. Batched with the production-inspection trip already queued for network_config, sysctl, htpasswd, and the 8140 question. |
| 6 | `puppet_infrastructure::user_samba` | — blocked: CATEGORY 5 (environment mismatch — the define targets a Zentyal/Samba domain controller, but the harness node is Ubuntu 24.04 without that command stack). Actual harness error after the Puppet 8 catalog compiled and began applying: "Error: /Stage[main]/Main/Node[puppet8node]/Puppet_infrastructure::User_samba[p8testuser]/Exec[create zentyal user: p8testuser]: Could not evaluate: Could not find command 'pdbedit'"; Puppet also reported "Dependency Exec[create zentyal user: p8testuser] has failures: true" and skipped `Exec[set p8testuser samba hash]`. Traced chain: the harness safely rendered define title `p8testuser` with the untracked synthetic-only fixture (`myname` `P8 Testuser` and a synthetic `unicodePwd` hash); `manifests/user_samba.pp:11-16` declares `Exec[create zentyal user: p8testuser]`, whose command is `create-user.pl ...` and whose `unless` guard starts with `pdbedit -Lw`; `manifests/user_samba.pp:18-24` declares the dependent hash update, whose command is `set-user-samba-hash.sh ...` and whose guard starts with `ldbsearch` against `/var/lib/samba/private/sam.ldb`; `templates/samba/set-user-samba-hash.sh.erb` in turn executes `ldbmodify`. A direct clean-node probe established `ID=ubuntu`, `VERSION_ID=24.04`, `p8testuser=absent`, and that `pdbedit`, `ldbsearch`, `ldbmodify`, `create-user.pl`, and `set-user-samba-hash.sh` are all missing. The commands are OS/service-specific and do execute during apply; critically, both guards depend on missing OS-specific binaries, which meets the runbook's Category 5 rule that an unexecutable guard is not protection. The target also consumes the two scripts externally rather than deploying them. The actionable Puppet 8 syntax finding is preserved in the working tree: legacy dynamic `$localdir` resolution failed with "Unknown variable: 'localdir'" at the original line 13, and adding the repository-standard `lookup('filesystem::localdir')` made catalog compilation succeed without changing the configured path semantics. Altering guards, dropping either exec, installing substitutes by hand, or making the define deploy its previously external prerequisites would change behaviour or hand-repair node state. Unblock with a faithful Zentyal/Samba domain-controller test node/context that provides the normal `pdbedit`/LDB tools and externally owned helper scripts (plus harness node-selection support if the current hardcoded Ubuntu node remains); then revert that disposable node and rerun this target through two clean applications. |

## TRANSITIVELY GATED

- None

## PENDING QUEUE

| # | class | cx | dep | p8 | sc | internal_deps |
|---:|---|---:|---:|---:|---|---|
| 1 | `puppet_infrastructure::rsyslog_apparmor_exception` | 2 | 2 | 3 | no | rsyslog_base |
| 2 | `puppet_infrastructure::firewall_ipv6_drop_policy_desktop` | 2 | 4 | 4 | yes |  |
| 3 | `puppet_infrastructure::gnome_lock_screen` | 3 | 2 | 3 | yes |  |
| 4 | `puppet_infrastructure::firewall_addon_openvpn_server` | 3 | 3 | 5 | no |  |
| 5 | `puppet_infrastructure::puppet_boot_run` | 3 | 4 | 4 | no | filesystem_base |
| 6 | `puppet_infrastructure::sysmon_backup` | 3 | 4 | 4 | no | backup,filesystem_base |
| 7 | `puppet_infrastructure::sysmon_fs_health` | 3 | 4 | 5 | no | filesystem_base |
| 8 | `puppet_infrastructure::sysmon_integrity_master` | 3 | 4 | 5 | no | filesystem_base |
| 9 | `puppet_infrastructure::sysmon_integrity_node` | 3 | 4 | 5 | no | filesystem_base |
| 10 | `puppet_infrastructure::sysmon_mysqldump_health` | 3 | 4 | 5 | no | filesystem_base |
| 11 | `puppet_infrastructure::sync` | 4 | 3 | 4 | no | filesystem_base |
| 12 | `puppet_infrastructure::nginx_proxy_smtp_auth_ppa` | 4 | 4 | 5 | no | filesystem_base |
| 13 | `puppet_infrastructure::linux_policies_common` | 4 | 5 | 5 | no | filesystem_base |
| 14 | `puppet_infrastructure::linux_policies_user` | 4 | 4 | 5 | no | linux_policies_common |
| 15 | `puppet_infrastructure::rsyslog_server` | 4 | 6 | 3 | no | rsyslog_base |
| 16 | `puppet_infrastructure::hello_world_flask` | 5 | 4 | 5 | no | hello_world_flask_common,filesystem_base |
| 17 | `puppet_infrastructure::ssl_base` | 5 | 8 | 5 | no |  |
| 18 | `puppet_infrastructure::ssl_postfix` | 2 | 6 | 4 | no | ssl_base |
| 19 | `puppet_infrastructure::ssl_nginx` | 2 | 7 | 4 | no | ssl_base |
| 20 | `puppet_infrastructure::ssl_nginx_domain` | 2 | 7 | 4 | no | ssl_base |
| 21 | `puppet_infrastructure::postfix_smtp_node` | 6 | 4 | 6 | yes |  |
| 22 | `puppet_infrastructure::letsencrypt_base` | 6 | 7 | 5 | no | filesystem_base |
| 23 | `puppet_infrastructure::letsencrypt_certificate` | 3 | 6 | 4 | no | letsencrypt_base |
| 24 | `puppet_infrastructure::packages_base` | 6 | 10 | 5 | yes |  |
| 25 | `puppet_infrastructure::openvpn_domain` | 7 | 4 | 6 | yes |  |
| 26 | `puppet_infrastructure::filesystem_apt` | 7 | 5 | 5 | no | filesystem_base |
| 27 | `puppet_infrastructure::user_base` | 7 | 8 | 6 | yes |  |
| 28 | `puppet_infrastructure::user` | 1 | 4 | 2 | yes | user_base |
| 29 | `puppet_infrastructure::user_kde_lock_screen` | 2 | 5 | 3 | no | user_kde_lock_screen_common,filesystem_base,user_base |
| 30 | `puppet_infrastructure::user_desktop` | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 31 | `puppet_infrastructure::user_desktop_sudoer` | 2 | 5 | 3 | yes | user_base,user_kde_lock_screen |
| 32 | `puppet_infrastructure::user_sudoer` | 2 | 5 | 3 | yes | user_base |
| 33 | `puppet_infrastructure::users_sudoers` | 3 | 5 | 6 | yes | user_sudoer |
| 34 | `puppet_infrastructure::firewall_secure` | 7 | 8 | 7 | no | filesystem_base |
| 35 | `puppet_infrastructure::node_base_domain_desktop` | 6 | 9 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base_desktop,filesystem_apt |
| 36 | `puppet_infrastructure::nginx_base` | 7 | 10 | 6 | no |  |
| 37 | `puppet_infrastructure::mysql_server` | 8 | 5 | 6 | no | filesystem_base |
| 38 | `puppet_infrastructure::postfix_smtp_base` | 8 | 6 | 6 | yes | ssl_postfix,postfix_smtp_base_config_file |
| 39 | `puppet_infrastructure::sysmon_base` | 8 | 8 | 6 | no | filesystem_base,packages_base |
| 40 | `puppet_infrastructure::hashman_base` | 8 | 8 | 7 | no | filesystem_base |
| 41 | `puppet_infrastructure::user_lock` | 2 | 5 | 3 | no | hashman_base |
| 42 | `puppet_infrastructure::node_base_desktop` | 8 | 10 | 5 | no | packages_base,ssh_secure,firewall_secure,firewall_ipv6_drop_policy,filesystem_base_desktop,filesystem_apt,rsyslog_client,user_kde_lock_screen |
| 43 | `puppet_infrastructure::openvpn_server` | 9 | 6 | 7 | no |  |
| 44 | `puppet_infrastructure::network_vpn` | 8 | 7 | 6 | no | caching_nameserver,firewall_addon_caching_nameserver,firewall_addon_openvpn_server,openvpn_server |
| 45 | `puppet_infrastructure::nginx_static_domain` | 9 | 7 | 6 | no | nginx_base,nginx_default_removal |
| 46 | `puppet_infrastructure::nginx_static` | 5 | 7 | 5 | no | nginx_base,nginx_default_removal,nginx_static_domain |
| 47 | `puppet_infrastructure::firewall_secure_extra` | 9 | 8 | 8 | no | filesystem_base |
| 48 | `puppet_infrastructure::node_base` | 9 | 10 | 6 | no | packages_base,sysmon_base,ssh_secure,firewall_secure,firewall_ipv6_drop,filesystem_base,filesystem_apt,filesystem_lib64,filesystem_sec,dns_client |
| 49 | `puppet_infrastructure::nginx_frontend_domain` | 10 | 7 | 7 | no | nginx_base,nginx_default_removal |
| 50 | `puppet_infrastructure::nginx_frontend_mail` | 8 | 7 | 6 | no | ssl_nginx_domain,nginx_frontend_domain |
| 51 | `puppet_infrastructure::nginx_frontend` | 8 | 8 | 6 | no | nginx_base,nginx_default_removal,ssl_nginx_domain,nginx_frontend_domain |
| 52 | `puppet_infrastructure::hashman_web` | 8 | 7 | 7 | no | hashman_base,nginx_frontend |

## KNOWN GAPS

node_base internal_deps omits puppet_boot_run; this edge is ordering-irrelevant (routed via shared filesystem_base, which node_base already depends on) and was a considered omission, not an oversight. Revisit only if composition ever depends on it directly.
