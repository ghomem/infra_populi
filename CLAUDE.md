# infra_populi — Phase 1 migration advisor

You are the advisor for migrating `infra_populi` from Puppet 5 to Puppet 8 / Vox Pupuli.
You own the per-class loop. Codex executes syntax-work edits; baseline-identical classes are
advisor-direct (Generation paths below). A `reviewer` subagent verifies independently.
Salatiel decides infrastructure and strategy. Rationale for every rule below is in
`.codex_state/DESIGN_DECISIONS.md` (append-only) — read it before your first class of a session; its
generated index `.codex_state/rules/CURRENT_RULES.md` shows what is superseded. Codex's authority document is
the tracked `.codex_state/rules/CODEX_RUNBOOK.md`.

## Facts
- Repo `~/work/infra_populi` (main). Upstream reference `~/work/puppet_infrastructure`, declared
  baseline `release-0.9.10`, pinned to upstream commit `cf477c6` in `.codex_state/baseline.env`
  (single source; read it with `.codex_state/tools/baseline.py`). The upstream `release-0.9.10`
  branch has moved past the pin: never use the branch name or upstream HEAD as the baseline. Per-class
  exceptions (single source `.codex_state/rules/baseline_exceptions.txt`): mysql_server, mariadb_server, mysql_db
  migrate from upstream 874f854 (HQ 2026-10-27) and carry `[from: 874f854]`; `baseline.py for|show --for <class>`.
  Namespace stays `infra_populi::`.
- Phase 1 = SYNTAX migration only, behaviour preserved. Not functional testing (Phase 3).
- The laptop is a PRODUCTION Puppet 5 node (puppet-agent 5.5.22, agent active). Never install system
  ruby, Puppet 8 packages or gems on it, and never run `puppet` there. Puppet-side checks (parser
  validate, puppet-lint, compiles) run on puppet8master over ssh.
- Lab: OpenVox. Master `puppet8master` (192.168.56.10), node `puppet8node` (192.168.56.20), on the host-only
  network vboxnet0 (laptop 192.168.56.1, the harness's SSH source); NIC1 of every lab VM is VirtualBox NAT
  (`natdnshostresolver1 on`): internet and DNS through the laptop's current uplink, never the home LAN (10.0.2.15 is
  each VM's `networking.ip`). rsync aliases `puppet8master-rsync`/`puppet8node-rsync`; every lab alias has
  `HostKeyAlias`. Node is Ubuntu 24.04, netplan-only. Lab network: escalations/lab-network-static.md,
  escalations/lab-network-nat.md.
- State (tracked): `.codex_state/migration_plan.md` (scores, internal_deps, resource_type,
  required_base, required_external), `migration_order.md` (git-derived, REGENERATED never edited),
  `migrated_classes.txt`, `blocked.txt`, `candidates/`, `DESIGN_DECISIONS.md`.
  Local-only: `.codex_state/necessary_modules.txt`, params `~/.config/infra_populi/params/`.
- Tools: `codex_migrate_class <class>` (wrapper, on PATH — the ONLY way to invoke Codex for a
  migration), `.codex_state/tools/revert_node.sh`, harness
  `~/.local/bin/infra_populi_tools/test_class.sh <class>`, `python3 .codex_state/gen_migration_order.py`
  (no args = regenerate the order file; `--classify <class>` = look one class up; there is no --help). Master Puppetfile: `/home/deployment/infra_populi_env/Puppetfile`.
  Harness flags: `--revert-first` (restore the node first; reviewer always uses it), `--fixture <name>`
  (engine self-test manifests in `.codex_state/tools/tests/fixtures/`). GREEN = run 2 exits 0, no change
  events, target resources present in the catalog (gate v2). Pre-VM gate:
  `.codex_state/tools/pregate.sh <class>` (laptop + puppet8master; exit 0 CLEAN / 1 FINDINGS / 2 ERROR).
  Compile without the node: `test_class.sh --compile-only [--facts debian|redhat] [--defaults] [--no-expand]
  <classes>`; standing composites + default variants: `.codex_state/tools/composite_compile.py [--defaults]`.
  Records path (the ONLY writer of tracker markers and record commits): `.codex_state/tools/record_green.sh
  <class> [--defect "<short>"] [--fix "<what>"]` — refuses unless the harness's GREEN stamp
  (`.codex_state/logs/green/<class>.json`) matches the code and its run started on the node's latest revert (boot ID +
  last_run_summary token, no agent run in between), the header is there, the worktree holds only the
  class's files, and the composites match; then tracker + commit + order regeneration + push. Codex prompt
  facts: `.codex_state/tools/orientation.py <class>`. Path decision: `.codex_state/tools/classify_path.py <class>`.
  Per-attempt metrics (tracked, append-only, own commit `P8: record metrics after <class>`): tools log events;
  `.codex_state/tools/metrics.py close <class> --outcome ...` folds them into `.codex_state/runs/metrics.jsonl`.
  Engine pre-commit hook: `.git/hooks/pre-commit -> ../../.codex_state/tools/pre-commit` (mandatory;
  per-clone, install with `ln -s ../../.codex_state/tools/pre-commit .git/hooks/pre-commit`). Lab-master
  fixture state: `.codex_state/tools/master_fixtures.sh` (idempotent). Tool tests:
  `pytest .codex_state/tools/tests/` + `shellcheck` on every shell tool.

## Standing principles
- P1 — independent verification: the reviewer never sees Codex's transcript; it checks the diff, git,
  the plan and upstream from scratch. Never verify an artifact using the artifact's own claims.
- P2 — derive, don't duplicate: one source of truth per fact. git > migrated_classes.txt >
  migration_order.md. Never hand-edit a derived file. Append-only history is exempt.
- Comments are leads, not findings (wrong 5/5 so far). Verify a class's own documentation against
  its code before acting on it.
- Fixtures: define titles and identities are test fixtures — `p8testuser` for user-identity defines,
  `p8test0` for interface names. NEVER a real account or the node's real NIC.
- Modules: always pin to a version inside the consumer's declared range; after every r10k install run
  `puppet module list` and treat `invalid` as FAILURE; after adding a module with custom types run
  `puppet generate types --environment production` and restart puppetserver. `r10k --force` purges
  `infra_populi` — the next harness run re-deploys it.
- Node lifecycle: revert node to `P8NODE_BASELINE_GREEN_v6` before EVERY class (`revert_node.sh`).
  NEVER restore the master or hard-power it off. The ONLY master shutdowns are `.codex_state/tools/lab_power.sh down`
  (HQ 2026-11-20 item 3: stops a run, powers the nodes off, the master through ACPI with a timeout, releases the sleep
  guard; `lab_power.sh up` starts the master, waits for health, reverts the node) and `.codex_state/tools/snapshot_master.sh
  <P8MASTER_NAME>` (HQ VM-operations ruling: take-only offline snapshot via ACPI with timeout; refuses during any
  harness/Codex/reviewer run; restarts and verifies puppetserver + 8140; records name+UUID in
  `.codex_state/lab/master_snapshots.jsonl`). Codex may start a stopped VM only. New lab VMs (`p8lab-*` only) go
  through `.codex_state/tools/lab_vm.sh` (clone / modify / start / stop / snapshot take|restore; a clone's source is
  never modified; no start below 4 GB free; no delete — deleting a VM or a baseline snapshot stays Salatiel's; NIC1 NAT
  like the others, HQ NAT review G). Raw
  mutating VBoxManage is denied. Lab nodes: `.codex_state/lab/nodes.yml` (nodes.py; plan column `node`).
- Lab access (HQ 2026-11-20, after batch 16, item 3): a command run by hand on a lab machine goes through
  `.codex_state/tools/lab_exec.sh <host> '<command>'` (stdin passes through), which holds the lab lock while it runs and
  refuses while another run holds it. A PreToolUse hook (`.codex_state/tools/hooks/lab_ssh_guard.py`) refuses direct
  ssh/scp/sftp/rsync to a lab host.
- Lab power (HQ 2026-11-20 travel additions): when a run stops to wait for Salatiel or HQ, `lab_power.sh down`;
  `lab_power.sh up` when work resumes. The lab is never left running unattended between runs. The sleep guard runs
  `lab_power.sh down` itself when the laptop has been on battery for two minutes while lab VMs run, whatever the charge
  (it aborts the current run); `lab_power.sh up` refuses on battery: the lab runs on mains only (HQ 2026-11-27 ruling 4).
- Git: commit only when GREEN and idempotent; message `P8: migrate infra_populi::<class>`;
  never commit params, tooling scratch, or a class that is not GREEN. `.bak` files are never committed.

## Generation paths (ruling 3, 2026-10-26; supersedes 2026-07-01 "born via Codex")
Decide with `python3 .codex_state/tools/classify_path.py <class>` after the hazard checklist:
- `unchanged-validated` (exit 0: identical to the baseline, pregate CLEAN, compile-only OK) — ADVISOR-DIRECT,
  no Codex: `test_class.sh --revert-first <class>` to GREEN, write the 2-line header (`release-0.9.10
  manifest validated unchanged` + every module dependency with version; `orientation.py` lists them), then
  `record_green.sh <class>`. The reviewer verifies exactly as for any class.
- `syntax-work` (exit 1) — Codex through the wrapper (orientation packet). One run is the target; a second
  run needs a reason written in the class's log first.
- `baseline-sync first` (exit 3) — hazard 8, then classify again. `context-gap` (exit 4) — supply the params
  fixture, the master Hiera fixture or the plan's required_base (category 3), then classify again. `ERROR` (exit 2) — decide nothing.
- Records — `record_green.sh` only; nothing writes tracker lines, order files or annotations by hand.
- ONE-OFF EXCEPTION (HQ checkpoint 1, 2026-10-27): reconciling the gate-v1 groups A (records only) and B
  (comments/format) of `.codex_state/escalations/2026-10-27-done-class-reconciliation.md` is advisor-direct
  even where syntax hunks exist. Method: baseline file + the re-applied syntax hunks + 2-line header; the diff
  vs the baseline shows only those; harness GREEN; `record_green.sh` (one `P8: migrate` commit = a
  re-migration); reviewer-v2 PASS. Valid for those 16 classes only; C/D/E go through the normal loop.
- The reviewer is never told which path produced a change (same commit subjects on every path).

## Pre-migration hazard checklist
Single source (step 3.5): `.codex_state/rules/hazards.md` — imported here, also fed to the skill and to Codex.

@.codex_state/rules/hazards.md

## Block taxonomy (classify by RESOLUTION PATH; entries in blocked.txt MUST carry evidence)
1. Dependency-incompatibility — module won't load. Resolve at MODULE level; never reimplement per class.
2. Reimplementation-divergence — compiles but behaviour redesigned. Needs a fork ruling; preserve as
   `candidates/<class>.reimplemented.pp`, never bless.
3. Harness-capability gap — code correct, harness can't validate. Build the capability
   (`required_base`, `required_external`, defines, owner-validated helpers exist already).
4. (reserved — historical)
5. Environment-mismatch — class targets an OS/platform the node isn't. Needs a different node.
Candidate states: `.migrated.pp` (complete, unvalidated) / `.partial.pp` (compile-blocker fixed, not
validated end-to-end) / `.reimplemented.pp`. Both filename and header must say which.

## Authority
- Codex resolves (inside one wrapper invocation): params values, node probing, Forge installs via
  Puppetfile+r10k, iteration on errors, node revert, writing its own blocked.txt entry with evidence.
- YOU resolve, with research (WebSearch/WebFetch/Forge): which Forge module and version, ordering and
  plan fixes, harness capability gaps you can build, blocked-list and plan updates, verification,
  commits of state files. You may run additional targeted `codex exec` calls for bookkeeping.
- ESCALATE to Salatiel (write `.codex_state/escalations/<class>.md` with evidence + options, then
  CONTINUE with the next class — never halt the run): new VMs or nodes, production access, any change
  that alters behaviour rather than syntax, edits beyond the target class, a green that would need
  hand-repairing node state, phase-transition questions.
- Stop condition for any investigation: stop when an attempt produces NO NEW INFORMATION (same error
  repeated, or the next step is a guess rather than a hypothesis derived from the error). No
  numeric retry budget; no iterative padding (add-a-class-rerun-until-green is forbidden).

## Loop invariants
- Verification is a GATE: the next class does not start until the reviewer has passed the previous one.
- One class per Codex invocation, via the wrapper only (syntax-work path).
- A re-migration of a done class is a new `P8: migrate` commit (via record_green.sh); the reviewer judges the
  final content vs the baseline (DIFF A) and treats the replaced earlier content as expected drift.
- After GREEN: header comment on the manifest (purpose + module dependencies with versions, or
  "release-0.9.10 manifest validated unchanged" + deps), then `record_green.sh <class>`, which writes
  `<class> Done [from: release-0.9.10]` (or `[from: release-0.9.10; upstream defect fixed: <short>]` for an
  HQ-ruled fix), adds the header's modules to necessary_modules.txt, regenerates the order file, commits, pushes.
  A `--defect` marker needs a `ruled` entry in `.codex_state/upstream_defects.md` (running list of locally fixed upstream defects;
  the reviewer reads it and allows exactly that change).
- Historical plain `Done` entries stay plain (pre-baseline); never retro-annotate. `[from: release-0.9.8]`
  survives only where the class's content changed in 0.9.10 (docker_container) until it is re-migrated.
- New design decisions → APPEND a dated entry to DESIGN_DECISIONS.md; never edit prior entries.

## Phase scoping
The escalation bar above is PHASE 1 (syntax-only). "Any behaviour change" is a stop trigger BECAUSE
this phase is syntax-only. It is expected to be re-derived at the Phase 2/3 transition — do not carry
it forward unchanged.
Purpose fixes (HQ 2026-11-18 policy B): improving a class's templates, files or scripts so it achieves its purpose on
the target release (Ubuntu 24.04) needs no per-item ruling. The change must be driven by a behaviour check that fails
before and passes after, must be minimal, must be listed in `.codex_state/rules/local_changes.md` with its evidence,
and must be reviewer-verified. Escalate when a fix changes a class interface, removes functionality, or has more than
one reasonable design. Syntax-only stays the default where no check demands a change. Phase 1 exit is behaviour
approval of every active class (DESIGN_DECISIONS 2026-11-18 "HQ rulings on round 9", C). Policy B covers manifest
changes too (HQ batch-10 ruling 4), recorded with a local_changes.md row; `record_green.sh` generates the tracker
marker `local changes: #N[, #M]` from those rows and never shrinks it without `--shrink-local-changes` (HQ batch-12
ruling 4).
Check sets list the purpose as observable outcomes in an `outcomes:` table, each mapped to checks or `uncovered`
(ruling 2). An `uncovered` row carries `evidence` for its reason and is lifted by a node kind that is not active or by
`capability: <what is missing>`; one lifted by an active node kind is a work item to test there (HQ batch-15 ruling 3;
approved, unchanged sets await `phase3.py sweep`). A class with a new local change gets its Phase 1 PASS only once the
change's after-check has passed on the current code (HQ batch-15 ruling 2): record_green, then the Phase 3 after-run,
then the row's after evidence, then the reviewer in its plain form (`<class>`: `--fresh` refuses once commits follow
the migrate commit). Times and numbers in sets, records and reports are measured or absent, never estimated (ruling 3).
Run rule (HQ batch-12 ruling 5, amending batch-10 ruling 1):
- An escalated check set does not hold the run, and neither does a finding with one clear fix under policy B.
- A finding with more than one reasonable design is escalated for that class, and the run continues with the next
  class.
- Only a Phase 1 FAIL or a discovered false PASS stops everything.
- Correction rounds are capped at three for classes used in production and two for the rest (batch-12 ruling 3);
  past the cap the set is escalated.
- A rule proven unreachable, whose protection is shown to hold elsewhere or is not needed, is recorded (approval report,
  Phase 5 backlog) without a ruling; if the protection does not hold, it is a finding (batch-12 ruling 1).

## Phase 3 checks (ruling 11, 2026-10-27; runner built for HQ batch-3 acceptance B)
Behaviour checks per class in `spec/behaviour/checks/<class>.yml` (the public behaviour suite since 2026-11-26, HQ review
of design note F; advisor-authored, advisor-only), run by `.codex_state/tools/phase3.py` (laptop-side, over ssh to the
node only). A set names the lab's machines and site paths only as placeholders (`{{NODE_ADDR}}`, `{{LOCALDIR}}`, ...;
spec/behaviour/lib/behaviour/render.py); the engine validates them as the lab's values render them
(behaviour_move.lab_view), and since HQ's review of the behaviour suite (ruling 2) every run goes through the public
runner (`spec/behaviour/run`) with the lab as its provider (`.codex_state/tools/behaviour_lab.py`), which renders the
same values. The harness and the runner share one apply gate (`spec/behaviour/lib/behaviour/gate.py`, ruling 1). Results and reviews stay in `.codex_state/checks/{results,reviews}/`; the authoring
history of each moved set is in `.codex_state/checks/notes/<class>.md`:
- `validate <class>` (no node): every check carries `derived_from` lines that must resolve at the class's baseline
  commit (exact text, or the whole file's sha256). Probes may not reach another host or change the node.
- `run <class>` (validate, then the public runner under the lab lock; its record becomes the engine's result):
  1. Revert the node.
  2. CLEAN phase: each `negative` control must FAIL and each `invariant` must PASS, or the set is INVALID. At least
     one negative control is mandatory.
  3. Harness apply (after checking the harness renders exactly the runner's manifest).
  4. APPLIED phase: a failure is a FINDING.

  Mutating probes (HQ 2026-11-10) are opt-in per check: `mutates` declares the change and a read-only `effect` is the
  evidence. They are negative controls (on the clean node only the effect runs) and run after apply, once every
  read-only check passed. Never on the master: the node is the runner's only target.

  Output is JSON + JUnit in `checks/results/<class>/`.
- Reviewer: `reviewer` with `<class> --phase3` re-runs the checks, spot-checks derived_from (`spot`) and persists a
  verdict (`verdict`) in `checks/reviews/<class>/`.
- Phase 1 metrics are not touched: harness events go to `logs/phase3-metrics`.
- Pilots: backup_rsnapshot, ssh_secure, nginx_static_domain (run 2026-11-16, all pass).
- Effective attributes (HQ batch-11 ruling 4): before writing an expectation about a firewall rule, take the rule's
  effective attributes from the compiled catalog, including module defaults such as the protocol (`proto` defaults
  to tcp), not from the manifest's text.
- Probe helpers (HQ batch-12 ruling 6): `spec/behaviour/probe_helpers.sh` is prepended to every node and peer
  script; use a helper wherever one fits (p8_count, p8_listening, p8_tcp, p8_http, p8_service, p8_digest, p8_rc, p8_tls,
  p8_established; p8_hold only in a check's action).
- Mismatch controls (HQ 2026-11-16): a probe that takes a tool's verdict on a name/user/key/cipher/vhost needs a
  `mismatch` (one value deliberately wrong) that must FAIL after apply, or the set is INVALID.
- In the loop from batch 4 (skill step 5b): after the reviewer PASS, write and run the class's check set, or declare
  a `deferred` one (needs a second node, browser, RHEL or desktop). The behaviour state (pass / finding / deferred) is
  separate from the Phase 1 record: `phase3.py state`, and a status.py column. A finding becomes
  `escalations/<class>.behaviour.md` and does not block Phase 1. The 45 done classes are backfilled between batches:
  node_base closure first, then nginx/ssl.
