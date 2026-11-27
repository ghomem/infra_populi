# Behaviour suite built (HQ review of design note F, items 1-8): stop for HQ

Commits 57e3f2e .. e3c954c (DESIGN_DECISIONS 2026-11-26 steps 1-4, 2026-11-27 steps 5-8). Phase 1 approval is not touched (Salatiel's). The rename has not started.

## What was built, by ruling
| ruling | where | evidence |
|---|---|---|
| 1 location | spec/behaviour/ (checks, kinds.yml, fixtures, lib, run, probe_helpers.sh, tests, README.md) | af8befc, e7379fb |
| 2 fake-only fixtures | spec/behaviour/fixtures/params (98 files), fixtures/node (8); suite_check.py in the pre-commit hook refuses lab values, engine references and non-fake values | 8c48593, eb6d730 |
| 3 puppet apply | runner `--apply local`; measured on every set (below): 65 identical, 23 declare `apply.requires: [server]` + `requires_why` and are skipped in local mode, 1 unmeasured (uplink) | 5d55a5b, 1875440, 9d117d9 |
| 4 names | runner variables without P8_ ({{NODE_ADDR}}, {{PEER_ADDR}}, $PEER_ADDR, ...); built under the current module name | 57e3f2e |
| 5 derived_from | ignored by the public validator (setfile.py), still validated by the engine; purpose and outcomes table required | 60b6ab6 |
| 6 neutral move | all 90 sets: template rendered with the lab's values = old file, string for string (behaviour_move.py verify, from git); 106 fixtures the same (fixtures_move.py verify); the public manifest = the harness's for all 146 runs of the 89 runnable sets (manifest_compare.py) | af8befc, eb6d730 |
| 7 engine switch sample | 7 sets, 9 runs: identical to the engine check for check (below) | 5555f98 |
| 8 outside contributor | nothing in spec/behaviour names .codex_state, the advisor or Codex (suite_check.py, in the hook) | 8c48593 |

## Neutrality
- Sets: 90 neutral, 0 not neutral. Every review still holds: behaviour state unchanged (86 pass, 3 finding,
  1 deferred), approval report regenerates identical.
- Fixtures: 98 params + 8 node fixtures neutral for every run that uses them. Stay outside git: 5 params files
  (dns_client, the clientdns and other variants: public resolvers; mariadb_server, user_samba: hashes not provably fake)
  and 4 node fixtures no set uses.
- Manifests: 146 of 146 runs equal, after three converter fixes the comparison found (a base define's title, the plan's
  per-OS-family bases, params looked up level by level).

## Sample (ruling 7)
| set | covers | outcome | differences |
|---|---|---|---|
| hello_world_flask_common | ubuntu, mutating, p8_http, p8_tcp | ALL_PASS | 0 |
| hashman_web | puppetserver, ubuntu2 peer, browser flow (Playwright), peer agent, node agent, mismatch | ALL_PASS | 0 |
| firewall_secure | ubuntu2 peer, p8_hold, p8_established, p8_digest, 2 variants | ALL_PASS | 0 |
| linux_policies_user | kubuntu, KDE session | ALL_PASS | 0 |
| extra_packages_el | rhel9, mutating | ALL_PASS | 0 |
| mount_shares_desktop | gnome, ubuntu2 peer | ALL_PASS | 0 |
| openvpn_domain | dc peer, mismatch | ALL_PASS | 0 |
Every helper a set uses, every node kind. p8_rc and p8_tls are used by no set (their unit tests cover them).

## Local apply (ruling 3)
Every runnable set was run by the public runner with `puppet apply` on a fresh node (`behaviour_lab.py run --local`;
records `.codex_state/checks/public/local/`, 9d117d9) and compared check for check with the engine's reviewed run
(`behaviour_sample.py measure`):

- **89 sets measured: 65 identical to the engine** (local apply is the public default for them).
- **23 differ and declare `apply.requires: [server]`** (5d55a5b, 1875440), each with the cause read from its run; no
  declared set is identical. 15 take files from the server's mount `puppet:///extra_files`; 8 depend on the agent
  or the server otherwise (the agent's cached catalog, its state files, its daemon or `puppet agent --test`,
  `$server_facts`, or a peer using the node as its server).
  Declaring them changes no engine view (`behaviour_move.py verify`: 90 neutral), so every review holds.
- **1 unmeasured: filesystem_yum** (local FINDINGS, engine ALL_PASS): its mutating check runs the class's full
  `dnf update` and hit the check's 600 s limit twice (action rc 124) on the 180 kB/s uplink. Not a local-apply
  difference and not declared; it is re-measured when the uplink allows.
- Three differences the measurement found were converter or runner faults, fixed (4351682, 5d55a5b): the expected
  run-2 events of the whole catalog (filesystem_apt, sysmon_base), a corrupted tar stream (the master's alias forces a
  terminal), and a run 2 exiting 2 with no change line (now read from the last-run report). The sets they touched
  were re-run: filesystem_apt, linux_policies_user and mariadb_server are identical; sysmon_base differs for another
  reason (its Puppet check runs the agent) and is declared.

| set | local | engine | differing checks | why it needs a server (requires_why) |
|---|---|---|---|---|
| dns_client | FINDINGS | ALL_PASS | 3 | the empty variant's check reads the catalog the agent cached (client_data/catalog), which puppet apply does not write |
| firewall_addon_hosting | FINDINGS | ALL_PASS | 6 | its master rule's destination is the server fact $server_facts['servername'] |
| hashman_base | FINDINGS | ALL_PASS | 3 | a second machine runs an agent against the node as its Puppet server, which must serve the module |
| hashman_web | APPLY_FAILED | ALL_PASS | 31 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| mysql_db | APPLY_FAILED | ALL_PASS | 12 | mysql_server takes its TLS files from the server's file mount puppet:///extra_files |
| mysql_server | APPLY_FAILED | ALL_PASS | 12 | it takes its TLS files from the server's file mount puppet:///extra_files |
| network_vpn | APPLY_FAILED | ALL_PASS | 23 | openvpn_server takes its keys from the server's file mount puppet:///extra_files |
| nginx_frontend | APPLY_FAILED | ALL_PASS | 28 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| nginx_frontend_domain | APPLY_FAILED | ALL_PASS | 24 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| nginx_frontend_mail | APPLY_FAILED | ALL_PASS | 24 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| nginx_static_domain | APPLY_FAILED | ALL_PASS | 19 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| node_base_desktop | FINDINGS | ALL_PASS | 2 | a check restarts the agent daemon, whose own run asks the server for the node's catalog |
| node_base_domain_desktop | FINDINGS | ALL_PASS | 2 | a check restarts the agent daemon, whose own run asks the server for the node's catalog |
| openvpn_nm_connection | APPLY_FAILED | ALL_PASS | 23 | the OpenVPN CA certificate comes from the server's file mount puppet:///extra_files |
| openvpn_server | APPLY_FAILED | FINDINGS | 25 | the OpenVPN keys, certificates and DH parameters come from the server's file mount puppet:///extra_files |
| packages_base | APPLY_FAILED | ALL_PASS | 5 | a check reads the agent's resource list (state/resources.txt); after puppet apply it did not list the catalog's exec |
| postfix_smtp_base | APPLY_FAILED | ALL_PASS | 21 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| rsyslog_base | FINDINGS | ALL_PASS | 16 | its checks read the catalog the agent cached (client_data/catalog) and depend on the node's own agent runs |
| ssl_base | APPLY_FAILED | ALL_PASS | 20 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| ssl_nginx | APPLY_FAILED | ALL_PASS | 14 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| ssl_nginx_domain | APPLY_FAILED | ALL_PASS | 27 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| ssl_postfix | APPLY_FAILED | ALL_PASS | 14 | ssl_base takes the key and certificates from the server's file mount puppet:///extra_files |
| sysmon_base | APPLY_FAILED | ALL_PASS | 8 | a check runs the class's Puppet check, which runs puppet agent --test against the server |

## For HQ
1. Escalation `harness-gate-run2-errors.md`: gate v2 passes a run 2 that logged a resource error (Puppet exits 0 when an
   exec's check times out). No recorded GREEN found on one. Recommend option A (refuse `Error:` lines). The public runner
   already does.
2. Ruling 8 as read: engine records cited in prose are `{{SITE:...}}` placeholders; "plan" and HQ rulings stay as words.
3. The public runner's gate is stricter than gate v2 in two ways: it refuses logged errors (1.) and it counts changes
   from Puppet's last-run report, not only from log lines (found: run 2 exiting 2 with no change line under local
   apply). Whether gate v2 should also read the report is a question for HQ.
4. Lab uplink: from 2026-11-26 09:30 the laptop's uplink fell to 9.5 kB/s, later 100-180 kB/s; reverts work at the
   latter. Three sample re-runs and two measurement re-runs were environment failures.
5. filesystem_yum's local-apply measurement waits for a faster uplink (above). The filesystem_apt timeout stays as
   ruled (option C now; option A, a fresh node baseline, before the rename's re-verification).
6. Lab: the master's root filesystem took an ext4 error when the laptop's battery died with it running (2026-11-26);
   Salatiel repaired it with a manual fsck, no restore; packages, CA and modules verified. The sleep guard had shut
   the master down cleanly at the first power cut; the damage came from a later boot on a battery that then died.
   Whether the guard's 25% threshold should rise is Salatiel's.

Next, after HQ: the rename (and option A's fresh node baseline before its re-verification). Phase 1 approval stays
Salatiel's.
