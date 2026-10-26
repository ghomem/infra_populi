# HQ rulings on the 2026-10-26 engine diagnosis

Applies to `.codex_state/diagnosis/2026-10-26-engine-diagnosis.md`. Section refs are to that report.
Every ruling here becomes a dated DESIGN_DECISIONS entry (one batch entry, superseding where noted).

## 1. Baseline → `release-0.9.10`
Conditional on `git diff --stat release-0.9.8 origin/release-0.9.10 -- manifests templates files` touching only docker_container and rsyslog_server (+its templates/files). If so: the declared baseline becomes `release-0.9.10` (what production runs; H4). All tools, CLAUDE.md, reviewer.md, SKILL.md, UPSTREAM_BASELINE.md and pregate reference that ref — **never HEAD** (the clone sits on an unmerged branch). Re-annotate `[from: release-0.9.8]` → `[from: release-0.9.10]` mechanically, only for classes whose manifest+templates+files are byte-identical between the two refs (script-verified, one commit). docker_container is re-migrated under the new gate. rsyslog_server migrates from 0.9.10 directly; the CTO question about it is withdrawn. The mysql rewrite stays out until released (CTO decision 5). This supersedes the 2026-10-01 baseline entry.

## 2. GREEN v2 (Epic 1) — approved in full
1.1 rc 0 required on run 2; fail on `executed successfully` and `removed`; outer `timeout` on every agent run and on `codex exec`. 1.2 revert-first for the wrapper and the reviewer. 1.3 coverage signal. 1.4 reviewer v2 (templates/files diffed; two-diff method; verdicts persisted as JSON; header module claims checked against `puppet module list`; scope check on blocked.txt/candidates). 1.5 re-review sweep of all 31 done classes under v2; output a reconciliation list as an escalation. Until the sweep is done, the 31 are "done under gate v1" and are not quoted externally as verified.

## 3. Generation model — supersedes 2026-07-01 "born via Codex"
Three paths by class category (F.8):
- Unchanged-validated: manifest+templates+files identical to baseline; pregate and compile-only pass → advisor reverts, runs harness, writes header + tracker, `record_green.sh` commits. No Codex. Reviewer verifies independently, revert-first.
- Syntax-work: Codex, with the orientation packet (3.2). One run per class is the target; a second run needs a reason in the run record.
- Records: `record_green.sh` only. Nothing writes tracker/order/annotations by hand.
Reviewer never learns who authored the change.

## 4. Pre-VM gates (Epic 2) — approved
`pregate.sh` on the laptop (drift incl. templates/files, `parser validate`, allowlisted puppet-lint never `--fix`, ERB/EPP + legacy-fact grep, static hazard scanner). `test_class.sh --compile-only` on the master, plus standing composite compiles (node_base Debian+RedHat facts, meaningful_desktop closure, default-param variants) run after every green. Install puppet-lint and the pre-commit hook; neither is optional.

## 5. Overhead (Epic 3) — approved
3.1 Tier-0 revert: confirm the GRUB cause with one console screenshot first; then `GRUB_RECORDFAIL_TIMEOUT=2` (not 0 — keep the menu reachable), disable apt-daily/unattended-upgrades timers in the baseline, hard poweroff for the node only, new node baseline snapshot `P8NODE_BASELINE_GREEN_v2`. Master keeps ACPI and its never-restore rule. 3.2 orientation packet + `record_green.sh`. 3.4 per-attempt JSONL, tracked, own commit type `P8: record metrics after <class>`, reviewer exemption. 3.5 single sources: one hazard checklist file consumed by all three; runbook moves into the repo; Puppetfile exported to the repo on every change. The host-only/static-IP network (F.1 option 4) is approved as the first project *after* the sprint, with both snapshots refreshed — not inside it.

## 6. Lab master changes — approved, with conditions
- `extra_files` fileserver mount + throwaway PKI + Hiera fixture keys: built by an idempotent script in `.codex_state/tools/`, subjects/realms obviously fake (`p8test`), nothing production-derived, then a new master snapshot. 
- Pin the 5 unpinned Puppetfile lines to the installed versions today, before anything else.
- Catalog isolation (G5/H7): decided after HQ's open question below. No sprint step touches `passwd_common` until then.

## 7. Modules
- sysctl: thias-sysctl **1.0.8** (production's family; 1.0.7→1.0.8 is legacy facts only). If the compile gate shows it does not load on OpenVox 8, fall back to augeasproviders_sysctl with the `/etc/sysctl.conf` persistence delta recorded as a behaviour difference.
- htpasswd: **citrin-htpasswd 1.0.3**, after the advisor diffs its providers against leinaddm 0.0.3 and records the result. Module swap with identical semantics = advisor tier.
- user_samba: stand-in script accepted, status **mock-apply only / behaviour unverified**; Zentyal deferred (lowest leverage in the table).
- All pins inside the consumer's declared range; `invalid` = failure; `puppet generate types` + restart after custom-type modules; Windows-only dependency warnings recorded as expected in the rule.

## 8. Classes
- **puppet_boot_run**: provisional ruling = drop `ensure => running`, keep `enable => true`. A unit whose job is to run the agent must not be started from inside an agent run; `RemainAfterExit` keeps that path open. Write the escalation with the unit template, `puppet_boot_run.sh`, and upstream commit 4ae2e35's message. If that message shows an intent the drop would break, stop and ask HQ; otherwise proceed and record as "upstream defect fixed locally", batched for the CTO.
- **Import** `gnome_lock_screen`, `firewall_ipv6_drop_policy_desktop`, `rsyslog_apparmor_exception` from the baseline as baseline-sync; generator adds them with fleet weights.
- **Defective done classes** (D.3): reconcile to the baseline shape via the normal loop, after the sweep. `sysmon_puppet_cert_status` is re-migrated faithfully (its apt_update replacement is a Phase-1 violation). `filesystem_yum` loses the duplicated directories and gets correct provenance. `network_dhcp` 0ecf985's extra edits are recorded, not reverted. Deleted body comments/warnings are restored where the baseline has them.
- Fixture rule enforced retroactively: `firewall_addon_caching_nameserver.json` → `p8test0`.
- `nginx_frontend_domain.pp:247` `Integer()` counts as a syntax fix (Puppet 8 strict mode); no escalation.

## 9. Queue (Epic 4) — approved
Plan fixes (C1), Forge pins (C2) once the runtime answer is known — until then pin the non-openvox-only ones and leave the 8 openvox-only pins as a prepared, unapplied list — baseline-syncs (C3), escalation files (4.2), `prod_nodes` as secondary sort key (4.3). Order: node_base closure, leaves first; then the nginx/ssl stack; composites last within their cluster. Zero-declaration classes sink to the bottom until the CTO rules.

## 10. Infrastructure to fund now
Second NIC (host-only) on the node VM: yes, in the sprint (needed for openvpn/network safety). EL9 Incus container + one Ubuntu container: after the sprint, with harness node selection. RHEL9 VM reuse: decided after the CTO gives the RHEL server count. Desktop VM: Phase 3 for the 20-laptop fleet — scheduled, not now. Samba DC: deferred.

## 11. Phase 3 — adopted
The YAML check format with mandatory `derived_from` upstream lines and **negative controls that must fail on the clean baseline** is the standard. Pilots after the sprint: backup_rsnapshot, ssh_secure, nginx_static_domain; then the node_base closure. CLAUDE.md gets a Phase-3 scoping section.

## 12. Process
Hazard items 9–13 approved. `.git/info/exclude` wholesale exclusion replaced by an explicit `.gitignore` (logs, necessary_modules.txt remain ignored; everything else under `.codex_state/` tracked normally; no more `git add -f`). Toolchain versions (Codex 0.159.2, gpt-6.1-sol, plugin, reviewer model) recorded retroactively; a 1-class canary re-run is mandatory after any toolchain change. Before committing the diagnosis files, reduce the passwd-layer class-name list to a count. A generated "current rules" digest from DESIGN_DECISIONS is approved (3.5).

## 13. Sprint sequence and checkpoints
0 (today): pin Puppetfile lines; puppet_boot_run escalation. Then 3.1 → 1.1–1.3 → 2.1–2.2 → 1.4 → **1.5 sweep → HQ checkpoint** → 3.2, 3.3, 3.4, 3.5 → 4.1–4.3 → **HQ checkpoint** → resume `/migrate-next` with metrics on. One commit per step, `P8: engine:` prefix; nothing commits while the worktree holds unrelated changes. The "6–9 h for 50 classes" figure is a target the metrics will test; it is not quoted outside the repo.

## 1 (confirmed) and 6a — catalog isolation resolved
Ruling 1 confirmed: release-0.9.8..release-0.9.10 touches only docker_container.pp, rsyslog_server.pp and four rsyslog templates. Baseline bump proceeds.
6a: `passwd_common` on puppet8master is lab-local (each master in this infrastructure carries its own; it is not a copy of production's). It stays in puppet8node.pp as part of the lab baseline, mirroring the fleet. Record its provenance in DESIGN_DECISIONS; list the resource types/titles it manages (via compile-only, never file contents) so the coverage signal (1.3) and the reviewer can separate its resources from the target class's. The engine never reads or edits it. Harness runs must not depend on anything it manages except SSH access for the harness user.
