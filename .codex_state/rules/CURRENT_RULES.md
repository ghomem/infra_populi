# Current rules digest

DERIVED from `.codex_state/DESIGN_DECISIONS.md` — never hand-edit; regenerate with `python3 .codex_state/tools/gen_rules_digest.py`. The log is authoritative: read the full entry before acting on a line here. SUPERSEDED marks are mechanical (from `supersedes <date> "<title>"` references) and may be partial.

151 entries; 6 marked superseded (in whole or part); newest first.

## 2026-11-27 — HQ: rename accepted; changes before the re-verification; after it (Salatiel reviewed the approval report)
- 1. Stale open rows: about 27 rows give as their reason a capability the runner now has (more than one params fixture
- 2. docker_container: registry login is used by 5 production node statements. Serve a private registry with
- 3. openvpn_server: test the variant with compression off; production is heading there.
- 4. user_base, ecryptfs branch: company laptops use encrypted homes. Build a fixture user with an ecryptfs home on a
- 5. Key login: a clearly labelled throwaway test keypair may live in the suite's fixtures. Use it to prove that the
- 6. Report accuracy: production counts follow the corrected rule (a conditional include counts only where it is turned
- 7. Record Salatiel's decisions in the report (2026-11-27): the three findings accepted as known; all listed accepted
- 8. A change that does not pass within its correction rounds is recorded as an open row, and you move on.
- 9. Reboot capability: a runner step that reboots the class's node and continues. Use it for network_dhcp,
- 10. letsencrypt_certificate: prepare the class side for a Let's Encrypt staging test (staging server through a
- 11. Regenerate the approval report and stop for Salatiel's Phase 1 approval."

## 2026-11-27 — The rename applied; the package cache holds; the fresh node baseline waits for its snapshot
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-27 — HQ review of the behaviour suite, items 1-5 done; the rename's tooling built and tested before it is applied
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-27 — HQ review of the behaviour suite: accepted, with rulings (the rename may start)
- 1. Logged errors (your escalation): option A. A run that logs an error line fails, in gate v2 as in the public runner.
- 2. Engine switch: the engine now runs behaviour checks through the public runner, with the lab as its provider.
- 3. Wording (your item 2): accepted for now. Add to the documentation list: before the module is promoted, one pass over
- 4. Lab power: the lab runs on mains only. `lab up` refuses on battery, and when mains is lost the guard brings the lab
- 5. Scratch: the turn-end hook lists scratch files newer than the last commit; commit them to drafts or discard them
- 6. Slow uplink: build a small package cache as its own never-reverted lab VM (not on the master, whose disk is too
- 7. Fresh node baseline (option A), taken once, including the cache setting if item 6 holds. Hand Salatiel any command
- 8. Rename, per the approved plan and its amendments: tag `pre-rename` first (Phase 1 approval is still Salatiel's, so
- 9. Re-verification after the rename, on the public runner, every class on its node kinds: Phase 1 harness and the
- 10. Failures are escalated per class and the pass continues. Stop for HQ when the pass is complete."

## 2026-11-27 — Correction to the entry above (behaviour suite, steps 5-8)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-27 — Behaviour suite, steps 5-8: fixtures, the public runner, the engine's switch sample, local apply measured (HQ review of design note F)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-26 — Behaviour suite, steps 1-4: the sets moved to spec/behaviour/checks, neutrally (HQ review of design note F)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-26 — HQ review of design note F: approved, with rulings
- 1. Location: spec/behaviour/. spec/acceptance/ is where the Puppet community's standard acceptance tools look, and this
- 2. Fixtures: fake-only params fixtures may be committed inside the suite. This is the one exception to "never commit
- 3. puppet apply: allowed as the public default only for sets shown to give the same result as the agent path. Measure
- 4. Names: runner variables get neutral names with no P8_ prefix. The suite is built under the current module name and
- 5. derived_from: becomes optional provenance that the public validator ignores. The engine keeps validating it against
- 6. Moving the sets must be provably neutral: for every set whose probes change (addresses, hostnames and paths becoming
- 7. The engine's switch to the public runner needs a sample that covers every probe helper, every node kind, a
- 8. The guide is written for an outside contributor: nothing in spec/behaviour/ refers to .codex_state, the advisor or
- 9. filesystem_apt timeout: option C now. Option A (a fresh node baseline) is done just before the rename's full
- 10. Order: build the suite now (items 1–8), then stop for HQ with the neutrality and sample results. The rename follows,

## 2026-11-26 — Test-suite design note written (ruling F); stopped for HQ review
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-26 — HQ 2026-11-24 item 4 carried out; the final approval report; stopped for Salatiel
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-25 — The lab's paravirt provider is hyperv, enforced (HQ 2026-11-24 "experiment accepted")
- 1. Salatiel has run steps 2 and 3 (node restored to v4, set to hyperv, P8NODE_BASELINE_GREEN_v5 taken without booting;
- 2. Switch p8lab-kubuntu, p8lab-dc and p8lab-puppetserver the same way, with new baselines, and measure each once.
- 3. Make it stick: lab_vm.sh sets the provider on every new clone, the inventory records it, and a revert fails if a VM
- 4. Then, in this order: the reviews with no durations; the duration list re-run by author and reviewer; the rhel9 block

## 2026-11-24 — HQ rulings (resume on mains power), and the hyperv result
- 1. First, fix the test isolation (tests never read the laptop's real battery or act on the real lab) and commit the
- 2. Clock drift: follow your lead with an experiment on ubuntu2, which lab_vm.sh may modify. With it powered off, set its
- 3. Runs made on a drifting clock do not count as evidence, whatever their result, except gnome_lock_screen's, which ran
- 4. The reviews with no durations may continue (ssl_nginx_domain onward) whenever the experiment is not using the lab.
- 5. rhel9 on this uplink: before a block of rhel9 runs, refresh its baseline once so the reverts inside that block
- 6. Master snapshot: take it with snapshot_master.sh after the clock change is settled, so one snapshot covers both
- 7. Noted: only Ubuntu 24.04 rejects the rsyslog setting. The removal stands.

## 2026-11-24 — After the cold boot: the clocks still drift (0.465% slow); HQ rulings 1 and 2 carried out
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-24 — HQ rulings for the resume
- 0. Before anything else: run lab up and measure the node's and the master's clock rate against the laptop again. If
- 1. rsyslog_client: remove the rejected setting, as you recommend. Checks: rsyslog starts with no config error on
- 2. rsyslog TLS files (cutover row 10): fix the default now; do not leave it to the cutover. Without an override, the
- 3. Backlog #14: accepted as recorded.
- 4. Correction rounds: confirmed. The sweep counts its rounds from 1, with the same caps as before (three for classes
- 5. Then as you listed: sysmon_base's re-review, the 18 remaining reviews, the DESIGN_DECISIONS entry, the filesystem_apt
- Ruling 0 carried out the same day: the drift remains (node 1.0245, master 1.0249 over 300 s), and the laptop had not

## 2026-11-23 — HQ rulings on the sweep and the escalated lifts
- 1. **Sweep: option B, done once** (the 34 sets re-run and re-reviewed a single time).
- 2. **user_lock's check set:** a third round is approved for the fixture fix (unexpire after unlock).
- 3. **letsencrypt_certificate:** no mock DNS API; it stays a stand-in for Salatiel's acceptance. A real lift needs a
- 4. **openvpn_server and network_vpn:** no new gateway VM now; they stay stand-ins for Salatiel's acceptance.
- 5. **Then** the final approval report (stop for Salatiel), the test-suite design note, and the rename.

## 2026-11-23 — HQ rulings on the user_lock stop carried out; item 6 stand-in lifts; the run stops before the sweep
- 1. **Ruling 1** (a3df1b6): record_green refuses a migrate commit that changes no class file and points to --fix;
- 2. **Ruling 2:** sysmon_mysqldump_health's third round (the create-failure check), Phase 3 PASS; escalation closed.
- 3. **Ruling 3:** drafts live in `.codex_state/drafts/` (the test-suite notes; the desktop-login fixture, since used).
- 4. **Item 6 stand-in lifts:**
- 5. **The run stops before the sweep** (~04:45 UTC): its approach is a design choice affecting 34 sets

## 2026-11-23 — HQ rulings on the user_lock stop
- 1. **user_lock: option A, kept narrow.** record_green refuses a migrate commit that changes no class file and points to
- 2. **sysmon_mysqldump_health's set:** a third correction round is approved for the one missing check (the
- 3. **Scratch is not storage:** /tmp does not survive a reboot, and the laptop is shut down for travel. The test-suite
- 4. **Continue:** the remaining stand-in lifts, the sweep, the final approval report (stop for Salatiel), the test-suite

## 2026-11-23 — item 6 started; the run stops on user_lock's Phase 1 FAIL
- 1. **user_lock's stand-in lifted** (7175bca): on the master-role node, hashman itself creates the user (node fixture
- 2. **Operator error, recorded:** to drop the tracker's mock-apply marker I re-ran record_green without a content change,
- 3. **Run stopped ~01:15 UTC** on that standing Phase 1 FAIL (escalations/user_lock.phase1.md, options A/B). Not started:

## 2026-11-23 — HQ rulings after the stop: carried out
- 1. **Ruling 3, lab down at pauses (lab_idle_down.sh, 5066ec7).** A Stop hook (`.claude/settings.json`) runs
- 2. **The fake lab writes its world atomically** (conftest.py, both writers): a stub read a half-written world file
- 3. **Ruling 2 done:** review_class.py `comments_preserved` accepts a listed comment change (559979d, 3 tests; reviewer.md
- 4. **Ruling 1 done as local change #20** (287a517): the dump's databases (header, CREATE DATABASE, USE) are listed before
- 5. **Item 4 (openvpn_set_vpn_passwd_file), local change #21:** VPN1 connects to a real OpenVPN server on the ubuntu2 peer
- 6. **Commits with a path argument** (`git commit -- <path>`) run the pre-commit hook with GIT_INDEX_FILE set to a

## 2026-11-22 — HQ rulings after the run stopped
- 1. **sysmon_mysqldump_health:** the scratch-name design is withdrawn; the advisor's design, with conditions. Before any
- 2. **sysmon_puppet_cert_status: option B.** A comment describing replaced behaviour is not kept verbatim. The mechanical
- 3. **Lab down at pauses is enforced mechanically,** not by memory: a hook that runs when the advisor's turn ends brings
- 4. **Then continue:** item 4 (openvpn_set_vpn_passwd_file), the stand-in lifts, the sweep, the final approval report

## 2026-11-22 — HQ after batch 20 (after the laptop's power-off; the lab travels)
- 0. State check first: every lab VM was in a clean poweroff (the battery guard took the lab down on 2026-11-21 at 19:43
- 1. The backfill is accepted: 90 classes with a reviewed set.
- 2. sysmon_mysqldump_health: fix now: restore into a scratch database with its own unique name, drop only that one,
- 3. sysmon_puppet_cert_status: the certregen call replaced by a direct read of the certificates' expiry dates, the
- 4. openvpn_set_vpn_passwd_file: the password through NetworkManager's own interface so it works wherever profiles are
- 5. The approval report, generated from the recorded state (approval_report.py), first version now and regenerated as
- 6. Stand-in lifts with small lab additions: user_lock, the desktop login, a lab ACME endpoint, an extra network card on
- 7. Then the sweep of open uncovered rows, the final approval report (stop for Salatiel), the test-suite design note,
- 8. Stop at a clean point and run `lab down` when Salatiel says he is closing the laptop.
- 9. **Run stopped 2026-11-22 ~22:05 UTC** on a standing Phase 1 FAIL: sysmon_puppet_cert_status's review failed twice

## 2026-11-21 — batch 19: a Phase 1 review that fails on a missing peer; masked chain failures
- 1. **A Phase 1 review of a class whose harness needs a peer** (openvpn_domain needs the dc) runs only with the peer up.
- 2. **Command chains that filter a commit's output run with `set -o pipefail`.** A trailing `grep -vE` hid a failed

## 2026-11-21 — HQ after batch 18 (batch 8 accepted)
- 1. **The three escalated check sets** (openvpn_domain, postfix_smtp_base, linux_policies_user) get one more round
- 2. **openvpn_domain's Kerberos realm is a finding with one clear fix** (policy B, a local change): the realm is
- 3. **A domain-joined node hanging on SSH while its DC is down:** no fix now; a known limitation in the approval report
- 4. **Continue with batch 9**, then straight on in the agreed order: stand-in lifts → sweep of open uncovered rows →

## 2026-11-21 — backfill batch 8: an uncovered row's "capability" is tried first
- 1. **Try before claiming.** Reviewers rejected three of my uncovered rows in batch 8 because the lab could do what the
- 2. **Restore-and-restart behaviour** (ssl_base and similar): each notifying resource gets its own drift and its own
- 3. **Peers powered off after a run** (HQ 2026-11-17 ruling 5) leave a domain-member node waiting on its DC: a by-hand

## 2026-11-20 — HQ after batch 16, items 1 and 2: the backup directory and loud failures
- 1. **Local change #14:** the backup define receives the target, so it declares the directory once for every caller
- 2. **Local change #15:** after tar, a non-zero status writes an ERROR line to stderr and syslog and exits with tar's
- 3. **sysmon_backup's set** no longer creates the backup directory (it masked the defect).
- 4. **Cutover item 7 (item 2):** check on the production master (and the monitoring server) whether archives were ever
- 5. **A commit deadlock** (Salatiel chose the fix): a FAIL review of a re-migrated checkpoint class blocked every commit

## 2026-11-20 — HQ after batch 16, item 3: lab access through a wrapper
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-20 — backfill batch 6: lessons that change how sets are written
- 1. **Declared writes are measured, not recalled.** After an author run, the paths the node changed during each
- 2. **Literal data is matched as a fixed string.** A count fed with substituted data (keys, hashes, tokens) uses
- 3. **A behaviour baseline is measured before a check relies on it.** user_kde_lock_screen's first draft assumed
- 4. **Local change #13** (puppet_boot_run, policy B): `lsof` given several files exits 0 only when all are open.
- 5. **Plan node follows production's declaring node** where the behaviour needs it (letsencrypt_base to puppetserver).

## 2026-11-20 — HQ accepts travel readiness, with three additions
- 1. **Lab power at run boundaries.** When a run stops to wait for Salatiel or HQ, `lab_power.sh down`; `lab_power.sh up`
- 2. **Battery guard.** The sleep guard, which runs exactly while lab VMs run, reads /sys/class/power_supply each poll
- 3. **Nothing is deleted.** The six VMs the lab does not use stay (three are clone sources); old snapshots and backup

## 2026-11-20 — HQ after batch 15: network_static fixed, no hand-entered authoring time, lab power commands
- 1. **network_static (HQ item 1, keep and fix).** The baseline's parameters show the gateway belongs to the interface the
- 2. **Authoring time (HQ item 2).** Computed by the tool or not recorded: phase3.py refuses an `authoring` block, and
- 3. **Lab power (HQ item 3).** `lab_power.sh down|up`, the second sanctioned master shutdown beside snapshot_master.sh

## 2026-11-20 — ifupdown alongside netplan (HQ batch-15 ruling 5): measured facts and the plan
- 1. **ifupdown is installable on Ubuntu 24.04:** 0.8.41ubuntu1 from noble/universe (apt-cache policy on the 24.04
- 2. **Why production has ifupdown and the lab does not** (the answer HQ asked to record).
- 3. **On the 24.04 node** (prototype, 2026-11-20):
- 4. **Recording.**
- 5. **Reported, not part of ruling 5.** network_static's default route is hard-coded to `interface => 'eth0'` (baseline
- 6. **Plan:** native netplan support goes on the Phase 5 backlog, and ifupdown's availability is checked in the 26.04

## 2026-11-20 — Local change #9 done; the review form for a class with a new local change
- 1. **Local change #9** (caching_nameserver, HQ batch-15 ruling 6) is done.
- 2. **The review form.** Ruling 2's order (record_green, the Phase 3 after-run, the row's after evidence, then the

## 2026-11-19 — The lab VM crash on a laptop resume, and what it changed
- 1. **The crash** (escalations/lab-vm-crash-2026-11-19.md):
- 2. **A sleep guard** (HQ batch-15 follow-up 1): lab_sleep_guard.sh blocks sleep (logind, `--what=sleep --mode=block`)
- 3. **Two defects of the lab lock** that the recovery exposed, both fixed and tested:
- 4. **The master after the restart:**
- 5. **Facter and IPv6** (for caching_nameserver, HQ batch-15 ruling 6): on the lab node, Facter reports the VirtualBox
- 6. **Uncovered rows, follow-up to ruling 3:**
- 1. the RedHat rows, on rhel9;
- 2. the parameter variants that production sets (names and counts from the fleet data);
- 3. the remaining variants, listed for Salatiel's acceptance, not tested one by one.

## 2026-11-19 — HQ rulings on batch 15
- 1. **Batch 15 is accepted** (39 approved). **Not a false PASS.** The definition, for the record: a false PASS is an error
- 2. **A class carrying a new local change gets its Phase 1 PASS only once the change's after-check has passed,** and the
- 3. **Validator rule approved, applied capability-based** (Salatiel's answer, 2026-11-19):
- 4. **Continue with batch 6 and onward** under the run rule.
- 5. **network_dhcp and network_static.**
- 6. **caching_nameserver.** The same production server has no global IPv6 address, so the IPv4-only condition is now a

## 2026-11-19 — Backfill batch 5 and the batch-14 rulings carried out
- 1. **Local changes #7 and #8 are done** (Phase 1 and Phase 3 PASS each).
- 2. **The mirror fallback is built as ruled** (revert_node.sh):
- 3. **rules/approval_conditions.md** is the single source for what HQ rules "record in the approval report". Its items:
- 4. **Fixtures moved closer to the class's defaults and purpose.** They are params and never committed:
- 5. **Proposal for HQ, not built: a validator rule against unverified uncovered reasons.**

## 2026-11-19 — HQ rulings on batch 14
- 1. **openvpn_server and network_vpn, cipher: option A approved.** The class's cipher is added to the server's accepted
- 2. **Compression: option F approved, no change.** The one-way behaviour goes into the approval report and the
- 3. **ssh_secure:** restore the idle disconnect with sshd's own idle-timeout settings on OpenSSH versions that have
- 4. **network_dhcp and network_static:** they stay escalated until Salatiel answers how the production VPN servers'
- 5. **caching_nameserver on hosts without IPv6:** keep the IPv4-only fixture for the lab and make no class change now.
- 6. **Lab IPv6:** no baseline change. It is handled per class with fixtures.
- 7. **Mirror fallback:** allowed only when the primary archive fails, for that run only, recorded in the run record,
- 8. **Go:** batch 5 starts with user_base.

## 2026-11-19 — Backfill batch 4: the peer's address for node scripts, the lab's IPv6 and named, holds on the uplink
- 1. **Node scripts get `P8_PEER_ADDR`** (phase3.py, commit e85d826, tested).
- 2. **The lab NAT's IPv6, and named.**
- 3. **Lab holds on the uplink.**
- 4. **A composite checks a component's finding on a value the composite itself passes.** network_vpn passes its own

## 2026-11-18 — HQ rulings on batch 12
- 1. **Rule 518 (firewall_secure_extra, TCP fragments):** the same handling as the RST limit (Phase 5 backlog #8,
- 2. **firewall_secure_extra's set: one more round, the last for this class.**
- 3. **sysmon_base's set:** run round 3, since the failed-run CRITICAL path is the core of the class's purpose.
- 4. **Markers:** the tracker marker lists local-change numbers generated from rules/local_changes.md. record_green
- 5. **Run rule, amended so the backfill does not wait on HQ:**
- 6. **Probe helpers:** half of the first drafts failed on probe mechanics. A small tested helper library (count, port,
- 7. **Continue with batch 3 and onward,** by production use under the corrected count, mixing classes with no set and

## 2026-11-18 — HQ rulings on batch 11 (firewall_secure_extra)
- 1. **Blacklist: fix it, option A.** A blacklist that lets a listed address in does not achieve the class's purpose.
- 2. **RST limit: no fix.** The protective effect holds through other rules (501). It is listed in the approval report
- 3. **Check set:** a third round runs together with fix 1, and it is the last. If it fails review again, escalate with
- 4. **Authoring rule for firewall classes:** take each rule's effective attributes from the compiled catalog, including
- 5. **Restart batch 2 in the re-derived order.** firewall_secure_extra goes at the end of this batch, not the end of

## 2026-11-18 — Backfill order: a conditional declaration counts only the statements that turn it on
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — HQ batch-10 ruling 8 answered: postfix_smtp_node on the Hashman master
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — HQ rulings on batch 10 (accepted: 90 done; Hashman verified end to end; 16/16 RedHat branches)
- 1. **Start rule for the backfill** (replaces the limit of three):
- 2. **Writing check sets:** first list the class's purpose as observable outcomes, taken from the baseline's code and
- 3. **Numbers:** any time or number in a set, a record or a report is measured or absent, never estimated. Authoring
- 4. **Policy B also covers purpose fixes in manifests,** under the same conditions.
- 5. **rsyslog_base (#14) approved:** the service subscribes to the three TLS files, and the check shows that a changed
- 6. **hashman_web (#8):** the backend binds to 127.0.0.1, with no firewall change. If the baseline's nginx proxies to
- 7. **Accepted:** all the capabilities listed in the batch 10 report.
- 8. **Postfix on the master:** answered from the fleet data, as a count of node statements that declare both
- 9. **Logo files:** a placeholder logo is a test asset, not a stand-in, and company logos stay out of the repo. The
- 10. **Lift** the mount_shares_desktop and user_lock stand-ins as queued. The remaining stand-ins go into the approval
- 11. **Ubuntu 26.04:** the cutover targets the newest OpenVox 8 that supports it. The lab upgrades only right before
- 12. **Order unchanged:** backfill in batches of 10 by production use, then the approval report, then the test-suite

## 2026-11-18 — Runner: `node_agent`, an agent run on the class's node after a drift-making check (backfill)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — Purpose coverage: check sets state the class's purpose; the reviewer judges it (HQ ruling C1)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — Hashman on the master-role node: a local MTA, ubuntu2 v2 with a browser, fresh handover files (C2)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — Hashman end to end: the harness deploys to a master-role node; the runner's peer agent run (HQ ruling C2)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — The master-role node p8lab-puppetserver is up (HQ ruling C2)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — HQ rulings on round 9 (accepted: 89 done, 77 verified, 12 with stand-in)
- 1. Every class has a check set that tests its purpose, passing and reviewer-reproduced. The reviewer also judges
- 2. Stand-ins and `uncovered` notes are lifted where the lab can lift them. The master-role node is built now (no
- 3. A behaviour approval report, one row per class: purpose, what the checks prove, what they do not, node kinds,
- 1. nginx_frontend_mail and the RedHat fixes;
- 2. the master-role node and Hashman;
- 3. the backfill and purpose fixes, in batches of 10 under the start rule;
- 4. the approval report;
- 5. the test-suite design note (F);
- 6. the rename (E).

## 2026-11-18 — rhel9 pass, first triage: two harness/fixture fixes
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-18 — A reviewer verdict per node (HQ batch-8 ruling 6: the RedHat branches on rhel9)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — First contact with a clone of a lab node (p8lab-dc); the node can be powered off alone
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — Phase 3 desktop sessions on kubuntu (HQ batch-8 ruling 5: the KDE checks)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — HQ batch-8 ruling 1: nginx_base, a module-compatibility change
- 1. Re-run the harness, the reviewer and the behaviour checks for every done class whose closure includes nginx_base:
- 2. Migrate nginx_frontend_mail.

## 2026-11-17 — HQ batch-8 acceptance: rulings 2 and 3
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — HQ batch-8 ruling 9: Incus on the laptop; first contact over the host-only lease
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — HQ batch-8 ruling 4: lab clocks
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — Batch 8 engine decisions (report: escalations/batch-2026-11-17-8.md)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — HQ rulings after the bring-up (rulings 1-7, second set)
- 1. **openvpn_server:** option A extended; the module owns the unit.
- 2. **Hazard 14:** a per-class "standalone by production evidence" entry (class, module, evidence reference), nothing
- 3. **Documentation list:** a production cutover section. VPN gateways: read `service_provider` and the running
- 4. **mysql_db:** the real compile confirms the baseline ties mysql_db to mysql_server (`require =>
- 5. **Master-role placeholder** (nodes.yml `puppetserver`) accepted; not built. HQ decides after batch 8 and the DC,
- 6. **user_desktop_sudoer** may run on gnome now; KDE-specific classes and checks wait for kubuntu.
- 7. **Order:**

## 2026-11-17 — Engine decisions while applying the HQ batch-7 rulings
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — HQ batch-7 acceptance: batch 7 accepted (80 verified); rulings 1-8
- 1. **linux_policies_user:** the File/File_line expected run-2 events are accepted on the apt_update basis (baseline
- 2. **Stand-ins accepted as mock-apply:** letsencrypt_cert_standin and puppet_agent_standin.
- 3. **Reporting:** "verified" splits into verified and verified with stand-in (a verified class whose plan row has a
- 4. **mariadb_server:** approved as a module-compatibility change, not a defect.
- 5. **openvpn_server:** resolved at step (b) with no master change (escalations/openvpn_server.md, "HQ ruling 5").
- 6. **openvpn_domain:** nodes.yml gains the planned kind `dc` (p8lab-dc, Samba AD DC, 192.168.56.25, capability
- 7. **No package cache:** 1.3 GB per full re-verification is acceptable. The projection stays in every batch report.
- 8. **Order:**

## 2026-11-17 — mariadb_server prerequisites (batch 7)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — linux_policies_user: first File/File_line expected run-2 events (batch 7; for HQ acceptance)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-17 — HQ batch-5 ruling 4: snapshot_master.sh `--lab-test`
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ batch-5 rulings (start rule, tail list, snapshot exercise, mysql, rhel9)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — Batch 5 engine decisions (first batch on NIC1 NAT)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — Node bring-up: p8lab-rhel9 (HQ 2026-11-16 items 4–5)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ NAT review G: a p8lab VM starts only on the lab network
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ NAT review F: bytes received on the node's NIC1, per revert and per class
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — Lab NIC1 → VirtualBox NAT (lab-network-nat.md, HQ step review A–J)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ NAT review I: tool and settings commits run the full suite
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ item 7: deferrals reviewed and lifted by a named node kind; `uncovered` notes
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ item 3: lab_vm.sh, the guarded script for new lab VMs
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ item 2: node selection from a tracked inventory
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — batch 4: engine decisions; stopped on the bridged-Wi-Fi DHCPv4 loss
- 1. **Packages as path providers.** pregate's prerequisite probe counts a package the required_base closure installs as
- 2. **Template facts only inside ERB tags** (bda7bbf): plain text is never a fact lookup.
- 3. **A define needs its params file** (641eced): classify_path reports a missing one as context-gap (hazards.md 10).
- 4. **Merged /usr** (72abaf0): the probe looks up `/bin/...`, `/sbin/...`, `/lib*/...` under `/usr` when the clean-node
- 5. **One lab run at a time; a revert proves internet** (1a24f54; see its own entry). A `REVERT_FAILED` from the
- 6. **Phase 3 deferrals are not reviewer-checked yet** (their state comes from the validated file). Proposed to HQ:

## 2026-11-16 — batch 4: one lab run at a time; a revert proves internet
- 1. **Lab lock.** I ran classify_path's compile-only for the next class while the reviewer's harness was applying, and
- 2. **A revert proves internet.** The node once got no DHCPv4 lease on the bridged Wi-Fi (IPv6 only, no default route).

## 2026-11-16 — HQ: Phase 3 in the loop from batch 4; behaviour state; backfill between batches
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ: mismatch controls in Phase 3 checks
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — lab network project complete (step 10)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — lab network step 9 (master): P8MASTER_BASELINE_GREEN_v4; snapshot_master.sh health check fixed
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — lab network step 9 (node): P8NODE_BASELINE_GREEN_v3 is the baseline; overlay and lab.env removed
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-16 — HQ: a misused `--fresh` is a usage error, not a verdict
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — lab network steps 5–7 done; host-only is the engine's path
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — lab network step 4: tracked overlay setting (HQ step review C)
- 1. Reach the restored v2 node over `puppet8node-wifi`.
- 2. Apply the overlay: enp0s8 192.168.56.20/24 via netplan, and the hosts line for puppet8master.example.com →
- 3. FAIL unless a fresh (`-S none`) SSH to `puppet8node` shows `$SSH_CONNECTION` 192.168.56.1 → 192.168.56.20 and the
- 4. Run the usual checks.
- 5. Mark the state token last; no agent run.

## 2026-11-10 — HQ: fixture PKI names the fixture domain (master_fixtures.sh pki v2)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ: Phase 3 mutating probes (opt-in)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ: Phase 5 backlog item 3, dead ssh options
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ: lab-network design approved (stop until step review)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ batch-3 acceptance B: the Phase 3 runner
- 1. **derived_from references the baseline.** Every check carries baseline references, each `{path, lines, text}`
- 2. **Probes test the node only.** The runner has one execution path, `ssh puppet8node sudo -n bash -s`, with the
- 3. **Negative controls are mandatory (≥1) and must FAIL on the freshly reverted node.** An `invariant` (holds before
- 4. **Run order:** revert → CLEAN phase → apply with the gate-v2 harness (NODE_FRESH) → APPLIED phase. A failed
- 5. **Output:** JSON + JUnit (suites `phase3.<class>.clean` / `.applied`) in `checks/results/<class>/<UTC>-<role>`.
- 6. **The reviewer re-runs the checks and spot-checks derivation.** It runs `run --role reviewer` and `spot` (3 random
- 7. **Authoring minutes:** each check file records its own measured wall clock (`authoring.minutes`, required).

## 2026-11-10 — HQ batch-3 acceptance (4/4): skipped tests carry a reason in the report
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ batch-3 acceptance (3/4): three intervention counters
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ batch-3 acceptance (2/4): notify events accepted; Phase 5 backlog file
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ batch-3 acceptance (1/4): a recorded GREEN must start on the latest revert
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — batch 3: run-2 report stage; glob refs; runbook minimal-change rule
- 1. Gate v2 gains a REPORT stage. A resource that changes below the notice log level (nginx_frontend_domain's baseline
- 2. expected_run2_events refs may contain `*` (any text) for titles built from the define title or params; everything
- 3. CODEX_RUNBOOK §2 step 3: change only what Puppet 8 / the gate rejects; inherited `(also in baseline)` lint is left;
- 4. (same day) classify_path no longer routes a baseline-identical class to syntax-work for baseline-inherited

## 2026-11-11 — HQ rulings before batch 3 (3): the pre-commit hook runs the tests
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-11 — HQ rulings before batch 3 (4): dynamic prerequisite probe in pregate
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-11 — HQ rulings before batch 3 (2): authority enforcement under a Codex run marker
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-11 — HQ rulings before batch 3 (1, 6): metrics phases; expected run-2 events stated explicitly
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-11 — HQ rulings before batch 3 (5): the desktop regex node weighs 20 machines
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ rulings before batch 2 (3/3): plan edits are the advisor's; hazard 14
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ rulings before batch 2 (2/3): SSH ControlMaster; firewall_secure fixture
- (no numbered/Rule/Decision lines; read the entry)

## 2026-11-10 — HQ rulings before batch 2 (1/3): per-class expected_run2_events
- Ruling: a plan column `expected_run2_events` (`;`-separated `Type[title]`) names the ONLY resources allowed to report

## 2026-10-27 — HQ VM-operations ruling: snapshot_master.sh and read-only VBoxManage permissions
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Master snapshot P8MASTER_BASELINE_GREEN_v3
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Checkpoint-2 rulings 3–5 applied on the lab master
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — HQ rulings at sprint checkpoint 2
- 1. Confirmed: user_base's post-condition guard (HQ confirmed 06:10; the determinism check — the command is a pure
- 2. linux_policies_user: prefer a true post-condition guard if the policy lines are queryable state
- 3. rabbitmq and gitlab (and therefore puppet-archive, pulled in only for rabbitmq) are REMOVED from the lab Puppetfile
- 4. saz-ssh 13.1.0 and saz-sudo 9.0.2 are held for Phase 1; upgraded at Phase 6 module alignment, with re-review.
- 5. ntp/chrony from production (`puppet module list` on the production master, 2026-10-27): puppetlabs-ntp v8.5.0 and
- 6. /migrate-next resumes after the master snapshot and the old node snapshot deletion. First batch: `/migrate-next 7`

## 2026-10-27 — Ruling 7 mechanics: node fixtures and the mock-apply label
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase) — **SUPERSEDED (whole or part) by** 2026-10-27 — HQ rulings at sprint checkpoint 2
- 1. STANDING FACT: the runtime is OpenVox, settled since the project started. "Runtime decision" is deleted from
- 2. Upstream defects are fixed in infra_populi only, with the `upstream defect fixed` marker; the running list lives
- 3. All production nodes are agent-mode; every catalog comes from the master. firewall_addon_hosting: find what
- 4. mysql: Issue #122 is merged at upstream 874f854 and is the code that will run. mysql_server migrates from
- 5. Migrate everything: no retire list. Fleet usage is a priority ORDER, never a filter — zero-declaration classes stay
- 6. RHEL: due diligence applies; extra_packages_el and the RedHat branches stay in scope. Post-sprint infrastructure:
- 7. Sysmon: the monitoring side lives in another repository. user_sysmon and the sysmon_* checks get synthetic node
- 8. The "Decisions needed" and "CTO" sections of the diagnosis and the checkpoint files are rewritten to reflect 1–7.

## 2026-10-27 — Step 4.3: fleet-weighted order; HQ re-migration queue in the order file
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Step 4.2a: upstream-defect registry; the reviewer may read it
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Step 4.1d: lab-master fixture state (ruling 6) built by master_fixtures.sh
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Step 4.1c: baseline-syncs (C3) and the three imports (ruling 8): 90-class universe
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Step 4.1b: Forge pins applied (non-openvox-only) and the htpasswd provider diff (ruling 7)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Step 3.5: single sources for the engine's instructions
- 1. Hazard checklist: ONE file, `.codex_state/rules/hazards.md` (13 items: CLAUDE.md's 8 + diagnosis G items
- 2. Runbook: tracked at `.codex_state/rules/CODEX_RUNBOOK.md` (moved from ~/.config/infra_populi/; the old file is
- 3. Puppetfile export on every change: record_green.sh refuses while `export_puppetfile.py --verify` finds the
- 4. Generated "current rules" digest: `.codex_state/rules/CURRENT_RULES.md`, derived by

## 2026-10-27 — Step 3.4: per-attempt metrics (ruling 5 / F.9)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — A/B reconciliation done (HQ ck1 ruling 1): 16/16 reviewer-v2 PASS; one routing correction
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-27 — Step 3.3: advisor-direct path mechanics; re-migration is a plain `P8: migrate` commit
- 1. Path decision is a tool, not a judgement: `classify_path.py <class>` → unchanged-validated (identical to
- 2. A re-migration of a done class (the A/B reconciliation now; C/D later) is a new `P8: migrate` commit made
- 3. The tracker marker of a re-migrated class becomes `[from: release-0.9.10]`: the content is now baseline +

## 2026-10-27 — HQ rulings at sprint checkpoint 1 (re-review sweep: 8 PASS / 23 FAIL)
- 1. Sweep accepted: 8 of the 31 git-done classes are verified. Git stays the fact for DONE. A DERIVED state
- 2. Unguarded execs at the baseline (user_base, user_lock, linux_policies_user, mysql_server): option (a),
- 3. Marker approved and generalised: `[from: <ref>; upstream defect fixed: <short>]`, used for
- 4. Master snapshot (puppet-lint gem installed 2026-10-26) deferred to checkpoint 2, after the
- 5. Old node snapshot P8NODE_BASELINE_GREEN kept through checkpoint 2.
- 6. filesystem_sec: fixed locally with the minimal change (assign into a new variable instead of
- 7. Reviewer: the 1.5 sweep ran general-purpose subagents carrying reviewer.md verbatim (this session had
- 8. Evidence that gate v2 catches ENGINE errors, not only class errors: the 1.5 sweep found two defects in

## 2026-10-26 — Node revert refreshes apt lists (correction to sprint step 3.1)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-26 — passwd_common (lab-local) resource listing, per ruling 6a
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-26 — HQ amendment: the laptop is a production Puppet 5 node; ruling 4 amended; baseline confirmed
- Fact: the advisor laptop is a PRODUCTION Puppet 5 node (puppet-agent 5.5.22 at /opt/puppetlabs, agent
- Ruling 1 baseline pin CONFIRMED: release-0.9.10 == upstream commit cf477c6 (not the moving branch).

## 2026-10-26 — HQ rulings on the engine diagnosis (batch entry)
- 1. Baseline → release-0.9.10. SUPERSEDES 2026-07-01 "Declared upstream baseline: release-0.9.8" and
- 2. GREEN v2 (Epic 1, 1.1–1.5) approved in full: run 2 must exit 0; `executed successfully` and
- 3. Generation model: three paths by class category. Unchanged-validated (manifest+templates+files ==
- 4. Pre-VM gates (Epic 2) approved: `pregate.sh` on the laptop; `test_class.sh --compile-only` on the
- 5. Overhead (Epic 3) approved: Tier-0 revert (confirm GRUB cause by console screenshot first;
- 6. Lab master: extra_files mount + throwaway p8test PKI + Hiera fixture keys built by an idempotent
- 7. Modules: sysctl = thias-sysctl 1.0.8 (fallback augeasproviders_sysctl with the /etc/sysctl.conf
- 8. Classes: puppet_boot_run provisional = drop `ensure => running`, keep `enable => true`, recorded as
- 9. Queue (Epic 4): plan fixes; Forge pins (non-openvox-only now, the 8 openvox-only pins prepared but
- 10. Infrastructure: second (host-only) NIC on the node VM inside the sprint. EL9 + Ubuntu Incus
- 11. Phase 3: YAML check format with mandatory `derived_from` upstream lines and negative controls that
- 12. Process: hazard items 9–13 approved. `.git/info/exclude` wholesale `.codex_state/` exclusion is
- 13. Sprint order: 0 → 3.1 → 1.1–1.3 → 2.1–2.2 → 1.4 → 1.5 + HQ checkpoint → 3.2–3.5 → 4.1–4.3 + HQ

## 2026-10-05 — Identity preconditions order a define after user_base (internal_deps), not a block
- Decision (advisor tier, plan fix): add user_base to internal_deps (test-node ordering edge, consistent

## 2026-10-01 — Ruling: baseline drift resolved by baseline-sync (option A)
- Decision (Salatiel): a pending class whose local manifest differs from release-0.9.8 is brought to

## 2026-10-01 — required_base must cover parent dirs/resources a class needs from another class
- (no numbered/Rule/Decision lines; read the entry)

## 2026-10-01 — Baseline drift: 9 pending manifests are NOT release-0.9.8 content
- Decision (advisor tier): ADDED TO THE PRE-MIGRATION CHECKLIST — diff the local manifest (and its

## 2026-10-01 — Ad-hoc `codex exec` calls must close stdin and carry a timeout
- Rule: every advisor-issued `codex exec` runs as `timeout <N> codex exec ... </dev/null > <log> 2>&1`.

## 2026-09-30 — Lab runs OpenVox, not Perforce Puppet
- Fact: openvox-agent 8.24.2 / openvox-server 8.11.0 on the lab master. Vox Pupuli modules now declare

## 2026-09-30 — Networking cluster UNBLOCKED: root cause was version pinning, not Puppet 8
- Decision: network_dhcp, network_static, openvpn_server, network_vpn come off blocked.txt. The
- 1. Always pin a module to a version INSIDE its consumer's declared range. Never leave `mod` unpinned.
- 2. After every r10k install, run `puppet module list` and treat any `invalid` as a FAILURE.
- 3. After adding a module that ships custom types, run `puppet generate types --environment

## 2026-09-30 — Production master inspected: module identities, upstream bug, dependency roadmap
- (no numbered/Rule/Decision lines; read the entry)

## 2026-07-26 — Toolchain change: Codex 0.145.0, gpt-5.6-sol, reasoning effort xhigh — **SUPERSEDED (whole or part) by** 2026-10-26 — HQ rulings on the engine diagnosis (batch entry)
- Decision: upgraded Codex 0.130.0 -> 0.145.0; model gpt-5.5 -> "gpt-5.6-sol";

## 2026-07-26 — Block-category taxonomy: three distinct causes, three resolution paths
- Decision: "blocked" alone is uninformative; blocked.txt entries must state the CATEGORY,
- 1. DEPENDENCY-INCOMPATIBILITY — an external module/custom type will not load on
- 2. REIMPLEMENTATION-DIVERGENCE — the class compiles/applies, but the migration is not
- 3. HARNESS-CAPABILITY-GAP — the migration is CORRECT and faithful, but the harness

## 2026-07-26 — Harness invariant evolves: one target class + its DECLARED required base
- Decision: the strict one-class-at-a-time classification invariant is relaxed, narrowly.

## 2026-07-01 — Known limitation: the plan cannot predict external-type blockers
- (no numbered/Rule/Decision lines; read the entry)

## 2026-07-01 — network_config is a module-wide blocker; block the networking cluster; resolve at module level — **SUPERSEDED (whole or part) by** 2026-09-30 — Networking cluster UNBLOCKED: root cause was version pinning, not Puppet 8
- Decision: the entire networking/OpenVPN cluster is BLOCKED on the shared root cause that the

## 2026-07-01 — "Done" and "blocked" are different facts with different sources (P2 clarification)
- (no numbered/Rule/Decision lines; read the entry)

## 2026-07-01 — Model-3 bug fix: derivation must be revert-aware (currently-migrated, not ever-migrated)
- Decision: the git-derived done-set must reflect CURRENTLY-migrated, not "ever had a P8: migrate

## 2026-07-01 — Encode annotation discipline into the migration invocation
- Decision: the marker rules (plain Done vs [from: release-0.9.8] vs [reimplemented: ...]) must

## 2026-07-01 — New marker state: reimplemented/diverged
- Decision: R2's two marker states (plain Done = migrated-not-reconciled; Done [from:

## 2026-07-01 — network_dhcp: BLOCKED, reimplementation preserved as candidate (not Done)
- Decision: network_dhcp is marked BLOCKED, not Done, and carries NO [from: release-0.9.8]

## 2026-07-01 — Blocked Forge dependency is an escalation trigger, not a loop-internal decision
- Decision: when a class depends on a Forge module/custom type that will not load on

## 2026-07-01 — Known gap: node_base → puppet_boot_run edge missing in internal_deps
- Decision: leave the missing `node_base` → `puppet_boot_run` dependency edge in

## 2026-07-01 — Standing principle P2: derive, don't duplicate
- (no numbered/Rule/Decision lines; read the entry)

## 2026-07-01 — Standing principle P1: independent verification yardstick
- (no numbered/Rule/Decision lines; read the entry)

## 2026-07-01 — Generation model: Codex generates in-repo, Claude verifies independently — **SUPERSEDED (whole or part) by** 2026-10-26 — HQ rulings on the engine diagnosis (batch entry)
- Decision: division of labor for in-repo artifacts — Codex GENERATES + COMMITS

## 2026-07-01 — Option A: structured internal_deps column, not in-script graph
- Decision: dependency data for ordering is a machine-readable `internal_deps`

## 2026-07-01 — Model 3: migration_order.md git-authoritative + regenerated
- Decision: migration_order.md's DONE/PENDING status is git-derived, always

## 2026-07-01 — Analysis pass may read master Hiera (read-only, constrained)
- Decision: the analysis/scoring pass MAY read master Hiera to produce fully-

## 2026-07-01 — migration_plan.md: analysis-only pass, advisory, git-derived done
- Decision: a one-time Codex analysis pass scores every class (two separate scores

## 2026-07-01 — Pattern A: leaf classes self-declare prerequisite dirs inline — **SUPERSEDED (whole or part) by** 2026-10-26 — HQ rulings on the engine diagnosis (batch entry)
- Decision: leaf classes declare the prerequisite `file` directories they need

## 2026-07-01 — migrated_classes.txt was already correct (no fix)
- Decision: no correction commit was applied to migrated_classes.txt.

## 2026-07-01 — Ruling B: forward-only provenance annotation
- Decision: the 15 historical migrations stay as plain `Done` in

## 2026-07-01 — Declared upstream baseline: release-0.9.8 — **SUPERSEDED (whole or part) by** 2026-10-26 — HQ rulings on the engine diagnosis (batch entry)
- Decision: infra_populi is migrated FROM puppet_infrastructure `release-0.9.8`

## Supersession references that match no earlier entry heading

- 2026-07-01 — Model-3 bug fix: derivation must be revert-aware (currently-migrated, not ever-migrated): supersedes (no date) " —   it does NOT silently trust either reading. Catches the general revert case; its edge case   (unrelated later edit) degrades to a flag, never a wrong answer. No commit-message parsing. - Blocked-list (.codex_state/blocked.txt, tracked, one reason per entry): the AUTHORITATIVE   exclusion. A blocked class is never counted done even with a P8:migrate commit. Rationale: "
- 2026-10-01 — Ruling: baseline drift resolved by baseline-sync (option A): supersedes (no date) "block and escalate"
- 2026-10-26 — HQ rulings on the engine diagnosis (batch entry): supersedes (no date) "practical idempotency"
- 2026-10-26 — HQ rulings on the engine diagnosis (batch entry): supersedes 2026-09-30 "candidate replacement    augeasproviders_sysctl"
- 2026-10-26 — HQ rulings on the engine diagnosis (batch entry): supersedes 2026-07-26 "candidates force-added past the .codex_state/ exclude"
- 2026-10-26 — HQ amendment: the laptop is a production Puppet 5 node; ruling 4 amended; baseline confirmed: supersedes (no date) "pregate.sh on the laptop ... parser validate, allowlisted puppet-lint"
- 2026-10-27 — Step 3.5: single sources for the engine's instructions: supersedes (no date) "<title>"
- 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase): supersedes (no date) "8 openvox-only pins prepared but unapplied until the runtime answer"
- 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase): supersedes (no date) "batched for the CTO"
- 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase): supersedes (no date) "the mysql rewrite    stays out until released (CTO decision 5)"
- 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase): supersedes (no date) "zero-declaration classes sink until the    CTO rules"
