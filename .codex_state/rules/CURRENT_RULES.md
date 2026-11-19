# Current rules digest

DERIVED from `.codex_state/DESIGN_DECISIONS.md` — never hand-edit; regenerate with `python3 .codex_state/tools/gen_rules_digest.py`. The log is authoritative: read the full entry before acting on a line here. SUPERSEDED marks are mechanical (from `supersedes <date> "<title>"` references) and may be partial.

120 entries; 6 marked superseded (in whole or part); newest first.

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
