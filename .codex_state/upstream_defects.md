# Upstream defects fixed locally — running list (HQ 2026-10-27 production-facts ruling 2)

Upstream defects are fixed in infra_populi ONLY, each with the tracker marker
`[from: <baseline>; upstream defect fixed: <short>]`. No upstream patches, no escalation of these to anyone;
this list exists for reference. The reviewer reads it: with that marker, DIFF A may contain EXACTLY the change in
the entry's `Ruled change` (plus ordinary Puppet 8 translations); anything else fails, and a marker without a
`ruled`/`applied` entry fails `records`. `Status`: `ruled` (apply when the class is migrated) | `applied <commit>` |
`pending HQ` (a behaviour question that the defect rule alone does not settle).

## filesystem_sec
- Short: default group assigned to a new variable (no parameter reassignment)
- Defect: the default branch (`restricted_group` = '') reassigns the parameter `$restricted_group`; Puppet 8 refuses
  (`Cannot reassign variable '$restricted_group'`). The branch never compiled on Puppet 8.
- Ruled change (HQ ck1 ruling 6): `$restricted_group_real` = 'wheel' (RedHat) / 'sudo' (other) when the parameter is
  '', else the parameter; `file { $restricted_cmds: group => $restricted_group_real }`. Same values on every branch.
- Note: production nodes that pass `restricted_group` explicitly were unaffected.
- Status: applied 929062b (reviewer v2 PASS 2026-10-27)

## puppet_boot_run
- Short: ensure dropped
- Defect: upstream 4ae2e35 adds `ensure => running` to a Type=oneshot unit without RemainAfterExit; every agent run
  restarts it (`ensure changed stopped to running`): never idempotent, and the unit that runs the agent is started
  from inside an agent run.
- Ruled change (HQ ruling 8; intent check passed, escalations/puppet_boot_run.md): drop `ensure => running` from the
  service; keep `enable => true`.
- Status: applied 1f3e212 (reviewer v2 PASS 2026-11-10)

## openvpn_nm_connection
- Short: fqdn_rand_uuid replaced by stdlib fqdn_uuid
- Defect: calls `fqdn_rand_uuid`, defined nowhere (stdlib 4.25.1/9.x, any module; production master inspected
  2026-09-30) — the class cannot compile anywhere.
- Ruled change (HQ ck1 ruling 3): `fqdn_rand_uuid(<args>)` → stdlib `fqdn_uuid(<same seed argument>)`.
- Status: ruled (the class is still blocked: no NetworkManager on the node — blocked.txt, category 5)

## user_base
- Short: exec guarded by its post-condition
- Defect: `exec { "${ecryptdir}/wrapped-passphrase": ... }` (user_base.pp:128-133, only for ecryptfs users) has no
  guard: it rewrites wrapped-passphrase on every agent run.
- Ruled change (proposal escalations/user_base-exec-guard.md, lab-tested; confirmed by HQ production-facts ruling 2,
  advisor reading recorded at checkpoint 2): add
  `unless => "sh -c \"base64 -d < ${ecryptdir}/wrapped-passphrase.b64 | cmp -s - ${ecryptdir}/wrapped-passphrase\""`.
  Effect preserved incl. repair of out-of-band changes (refreshonly would lose that).
- Status: ruled

## user_lock
- Short: exec guarded by its post-condition
- Defect: `exec { "user_lock_${myuser}": command => "${hashmandir}/common/pp_auth.py lock ${myuser} DUMMYARG; exit 0" }`
  (user_lock.pp:11-15) has no guard: it runs every agent run although `lockpw(..., ignorestatus=True)` is a no-op for a
  locked user (libhashman/dbutils.py lockpw/is_pwlocked).
- Post-condition: the user's entry in hashman's DB `${dbdir}/hashes.pp` (`$<user>_pwd_hash = '<value>'`,
  SUFFIX_USER `_pwd_hash`, SEPARATOR `=`) has a value starting with LOCKPREFIX `!` (libhashman/config.py.erb:38,57,58).
- Ruled change: add `$hashmandb = lookup('hashman::dbdir')` and
  `unless => "grep -Eq \"^[[:space:]]*\\\$${myuser}_pwd_hash[[:space:]]*=[[:space:]]*'!\" ${hashmandb}/hashes.pp"`.
  When the user is locked the command would change nothing (E_OK); when not locked or absent it runs as today.
  Verify the exact quoting against a locked p8testuser entry when the class is migrated (needs hashman_base).
- Status: ruled

## mariadb_server (the 0.9.10 mysql_server exec, moved by upstream 874f854)
- Short: certificate generation guarded by its post-condition
- Defect: `exec { "generate the ssl certificates, sign them and deploy them at $ssl_dir": command =>
  "$bindir/deploy_self_signed_certificates.sh" }` (mariadb_server.pp:99-102, inside `if $generate_certificates`) has no
  guard: every agent run mints a NEW CA and server key/cert (templates/mariadb/deploy_self_signed_certificates.sh.erb)
  and replaces the ones clients may trust — rotation on every run is the defect.
- Post-condition: ca.pem, server-key.pem and server-cert.pem exist (non-empty) in `$ssl_dir`.
- Ruled change: add `unless => "test -s ${ssl_dir}ca.pem -a -s ${ssl_dir}server-key.pem -a -s ${ssl_dir}server-cert.pem"`
  (the script writes `<ssl_dir>*`, so `$ssl_dir` carries its trailing slash — verify at migration).
- Note: mysql_server at 874f854 is no longer affected (its only exec is a refreshonly + onlyif AppArmor reload).
- Status: ruled

## openvpn_server
- Short: duplicate service resource dropped (module manages openvpn-server@<name>)
- Defect: declares `service { 'openvpn-server@puppet_infrastructure' }` (openvpn_server.pp:117) that puppet-openvpn
  (11.0.1 and 12.0.0) declares itself on systemd hosts → `Duplicate declaration` (REAL compile 2026-10-27).
- Ruled change (option A of escalations/openvpn_server-upstream-defects.md, settled by production-facts ruling 2):
  remove our service resource; notifies that targeted it point at the module's `Service['openvpn-server@puppet_infrastructure']`.
- Open (module level, not a defect ruling): behind it the compile hits a network_config type-redefine conflict.
- Status: ruled

## firewall_addon_hosting
- Short: OUTPUT accept for the master on 8140
- Defect: sets `OUTPUT:filter:IPv4` purge + policy drop allowing only RELATED/ESTABLISHED, DNS and NTP; no class
  (firewall, firewall_secure, firewall_secure_extra — no OUTPUT rule anywhere; `8140` appears in no manifest or
  template) permits NEW outbound to the master on 8140, and every production node is agent-mode (HQ ruling 3), so
  the class severs the agent from its master.
- Ruled change (HQ production-facts ruling 3; destination amended by the HQ NAT step review C, 2026-11-16): add
  `firewall { '152 OUTPUT PUPPET MASTER': chain => 'OUTPUT', proto => 'tcp', dport => '8140',
  destination => $server_facts['servername'], jump => 'accept' }` (the firewall-8 `jump` translation, like the class's
  other rules). puppetlabs-firewall 8.3.0 resolves a hostname destination ON THE AGENT
  (`PuppetX::Firewall::Utility.host_to_ip`: `Resolv.each_address`, /etc/hosts then DNS) and compares the resolved /32
  with the installed rule (`insync?` → `host_to_mask`), so the rule carries the address the node resolves for its
  master's name.
- Superseded wording: `destination => $server_facts['serverip']`. On a two-NIC master `serverip` is the master's
  primary address, not the one the node uses: in the lab 10.0.2.15 (NIC1 NAT) while the node reaches the master at
  192.168.56.10, so that rule would have let the class cut the agent off.
- Limit: the rule follows the master's own FQDN (`servername`), resolved on the node. A node that reaches its master
  under a different name whose address differs from the FQDN's (split DNS, an alias to another interface) is not
  covered; the agent's `server` setting is not a fact. A name the node cannot resolve fails that resource loudly
  ("Failed to resolve hostname"), never silently.
- Idempotency proof (2026-11-16, lab-network-nat.md step 6, NIC1 NAT on both VMs): the class with the `action` →
  `jump` translation and this rule, in the worktree only (not committed or recorded; the class waits for its
  re-migration), `test_class.sh --revert-first puppet_infrastructure::firewall_addon_hosting` → GREEN (stamp code
  b7cc55a8e16a at d31e872, node fresh). Run 2 reached the master through the class's own `OUTPUT` DROP policy with no
  change events. The node's `iptables -S OUTPUT` shows
  `-A OUTPUT -d 192.168.56.10/32 -p tcp -m tcp --dport 8140 -m comment --comment "152 OUTPUT PUPPET MASTER" -j ACCEPT`;
  the master's `ipaddress` (= `serverip`) was 10.0.2.15. The manifest was restored and the node reverted. Seen in the
  same run: "Unable to persist firewall rules" (no Class['firewall'] in the harness; hazard 14 at re-migration).
- Status: applied bd0529a (reviewer v2 PASS 2026-11-16)

## linux_policies_user
- Short: exec runs only under the policy script's own login check (no effect without a session)
- Defect: `exec { "Execute linux policies for: ${username}": command => "${policies_script_exec} puppet-agent", user =>
  $username }` (linux_policies_user.pp:71-75) has no guard, so it runs every agent run. The policy lines are opaque
  (arbitrary calls into files/linux-policies/COMMON/common), so there is no queryable post-condition.
- Why a session guard preserves behaviour (HQ checkpoint-2 ruling 2): the script the exec runs is assembled from
  templates/linux-policies/puppet_header.sh.erb, which itself does `who | awk '{print $1}' | grep -q "^$USERNAME\$"`
  and otherwise logs "not loged in, skipping policies execution" and `exit 0` — the policies cannot take effect without a
  login session. The guard uses the IDENTICAL predicate, so the policies run in exactly the same cases; the only
  difference is that the "not logged in" syslog line is no longer written when nobody is logged in.
- Ruled change: add `onlyif => "who | awk '{print \$1}' | grep -q '^${username}\$'"` (path as needed); command, user,
  environment unchanged. With the user logged in it still runs every agent run (re-applying policies by design).
- Status: ruled

## mysql_server
- Short: explicit MySQL service name (puppetlabs-mysql >= 11 defaults Ubuntu to MariaDB)
- Defect: the class declares `mysql::server` with `package_name => "mysql-server-${version}"` and no `service_name`;
  puppetlabs-mysql 17.3.0 (the Puppet 8 line) defaults Ubuntu >= 20.04 to the mariadb provider (service `mariadb`),
  so the class manages a service that does not exist on a MySQL node ("Systemd start for mariadb failed!"). Under
  10.5.0 (production) Ubuntu defaulted to `mysql`.
- Proposed change: `service_name => 'mysql'` in the `mysql::server` declaration (escalations/mysql_server.md option 1).
- Status: not a defect — HQ batch-5 ruling 2: a module-compatibility change (like the firewall-8 renames), recorded in rules/class_rulings.txt; no upstream-defect marker
