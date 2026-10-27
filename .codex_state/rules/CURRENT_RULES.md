# Current rules digest

DERIVED from `.codex_state/DESIGN_DECISIONS.md` — never hand-edit; regenerate with `python3 .codex_state/tools/gen_rules_digest.py`. The log is authoritative: read the full entry before acting on a line here. SUPERSEDED marks are mechanical (from `supersedes <date> "<title>"` references) and may be partial.

46 entries; 5 marked superseded (in whole or part); newest first.

## 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase)
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
