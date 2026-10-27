# Sprint checkpoint 2 — after 4.3 and the "production facts" rulings (2026-10-27). The sprint WAITS here for HQ.

Per-step detail, commits and measures: `.codex_state/sprint/2026-10-26-engine-sprint.md` (every row done).
Next by §13: resume `/migrate-next` with metrics on — after the master snapshot below.

## State (`python3 .codex_state/tools/status.py`, release-0.9.10 = cf477c6 + per-class exceptions)
- **92 classes** (90 at release-0.9.10 after the 3 imports; +mariadb_server, mysql_db from upstream 874f854 by ruling 4).
- 31 done = **24 verified (gate v2)** + 7 gate-v1 re-migrations at the head of the queue (rsyslog_base → rsyslog_client
  → docker_container → filesystem_yum → backup_rsnapshot_pre; firewall, sysmon_puppet_cert_status sink). 1 owner_validated.
- 3 blocked (was 7): extra_packages_el (RHEL node — post-sprint VM), mount_shares_desktop (desktop fixture),
  openvpn_nm_connection (no NetworkManager on the node; its fqdn fix is ruled).
- 57 pending, ordered by dependencies then production use (4.3). **Path sweep of the 57 (real lab, 461 s):
  16 unchanged-validated (advisor-direct, no Codex), 26 syntax-work, 14 context-gap (params/Hiera fixtures),
  1 baseline-sync first (node_base_desktop, after rsyslog_client)** — was 4/21/14/8 of 47 before 4.1.
- Metrics: `.codex_state/runs/metrics.jsonl` is produced (first record: filesystem_sec, PASS, revert 27.8 s median,
  0 Codex runs); every tool emits events; `metrics.py summary` is in the skill's end-of-run report.
- Upstream defects fixed locally: `.codex_state/upstream_defects.md` (1 applied, 7 ruled, 1 pending — below).
- Node: reverted to P8NODE_BASELINE_GREEN_v2. Worktree clean, pushed. Tests: 173 + 3 lab-skipped pass; shellcheck clean.

## Done since checkpoint 1 (commits in the sprint file)
3.2 orientation packet + record_green.sh (the only records writer; GREEN stamp) · 3.3 classify_path + advisor-direct path ·
A/B reconciliation 16/16 PASS · 3.4 per-attempt metrics · 3.5 single sources (hazard file, tracked runbook, Puppetfile
export check, generated rules digest + hook) · 4.1a plan fixes (22 classes) · 4.1b/pf1 Forge pins (mysql 17.3.0, sysctl
1.0.8, htpasswd 1.0.3; then all openvox-only: nginx 8.4.0, letsencrypt 13.4.0, epel 6.0.0, openvpn 12.0.0, rabbitmq 15.0.0
+ archive 8.1.0, gitlab 11.1.0) · 4.1c 7 syncs + 3 imports · 4.1d master fixtures (extra_files, p8test PKI, Hiera) ·
4.2 defect list, escalations, filesystem_sec fixed (PASS) · 4.3 fleet-weighted order · pf4 per-class baseline exceptions
(mysql trio at 874f854) · pf2/3 exec guards, openvpn_server, firewall_addon_hosting (8140 accept) unblocked · pf7 node
fixtures + mock-apply (user_sysmon, user_samba unblocked; both GREEN on the lab) · pf8 decision sections rewritten.

## Needed from Salatiel now
1. **Master snapshot** (ck1 ruling 4; my settings deny master snapshots). The master differs from its last snapshot by:
   puppet-lint 4.3.0 gem (agent ruby); Puppetfile + r10k: +puppetlabs-mysql 17.3.0, thias-sysctl 1.0.8, citrin-htpasswd
   1.0.3, puppet-openvpn 12.0.0, puppet-nginx 8.4.0, puppet-letsencrypt 13.4.0, puppet-epel 6.0.0, puppet-archive 8.1.0,
   puppet-rabbitmq 15.0.0, puppet-gitlab 11.1.0 (`Puppetfile.bak.*` beside it); regenerated `.resource_types/`;
   `/etc/puppetlabs/puppet/fileserver.conf` [extra_files] + `/etc/puppetlabs/code/p8test_extra_files/` (throwaway PKI);
   `hiera.yaml` level "P8 lab fixtures" + `data/p8test_fixtures.yaml` (backup `hiera.yaml.bak.*`). Rebuildable with
   `master_fixtures.sh all` + the repo Puppetfile export.
2. **Old node snapshot P8NODE_BASELINE_GREEN** — kept through checkpoint 2 as ruled; delete or keep (deletion is yours).

## Decisions requested (HQ)
1. **My reading of production-facts ruling 2** — "upstream defects fixed in infra_populi with the marker, no escalation"
   + "proceed" — as confirming (a) the user_base post-condition guard I had stopped on (escalations/user_base-exec-guard.md,
   lab-tested), and (b) option A for openvpn_server (drop our duplicate `openvpn-server@puppet_infrastructure` service).
   Both are now `ruled` in the defect list. Say if either is wrong.
2. **linux_policies_user's exec has no post-condition.** It runs the user's policy lines every agent run BY DESIGN
   (re-applying desktop policies); gate v2 will hold it RED, and ck1 ruling 2 forbids an exemption list. Options:
   (a) recommended: guard with the condition its own comment states — `onlyif` the user has an active login session
   (e.g. `loginctl show-user <user> -p State --value` = active): on a desktop with the user logged in it still runs every
   run (non-idempotent there, by design); on the lab node and with nobody logged in it is quiet. Behaviour change: the
   script no longer runs when the user is not logged in (where its GUI policies have no session to act on).
   (b) refreshonly on a policy-script change (behaviour change: no re-application each run).
   (c) a gate-v2 per-class "re-applied by design" acknowledgement (would reverse ck1 ruling 2's "no exemption list").
3. **rabbitmq / gitlab**: installed because they were in the prepared list; no infra_populi class uses them (they serve
   the company layer). Keep (my default) or remove.
4. **saz-ssh 13.1.0 / saz-sudo 9.0.2**: no longer held for a runtime reason; upgrading would change the modules under
   verified classes (ssh_secure, sftp_only; sudo users) and require their re-review. Recommendation: hold for Phase 1.
5. **Still open, production information:** the ntp and chrony module identities for node_base (58 servers) —
   escalations/ntp-module-identity.md (read-only `metadata.json` on the production master).
6. Go: resume `/migrate-next` (metrics on) after the snapshot; the 7 re-migrations run first, then the queue.

## Facts HQ should know
- My reconciliation list was wrong once: firewall_addon_xrdp's string `state` is a required firewall-8 translation (the
  array re-applies every run). Corrected and recorded (DESIGN_DECISIONS A/B entry).
- Engine defects found by the work itself and fixed with regression tests: stub tests leaked a fake GREEN stamp into the
  real logs; pregate passed silently on an empty master reply; record_green accepted a header with an unversioned module
  name; pregate read `$x.empty {` as a resource type; orientation looked up params by the wrong file name.
- openvpn_server, behind the ruled duplicate-service fix, still hits a `network_config` type-redefine conflict at
  compile (module level; the class's own investigation).
- The advisor-direct share is 16/57, not the diagnosis's "about half": most remaining classes need syntax work, a params
  or Hiera fixture, or a dependency migrated first.
- Done-criteria note: "status.py reflecting the 90-class universe" now reads 92, by ruling 4.
