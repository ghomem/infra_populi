# Design Decisions — infra_populi Puppet 5 → Vox Pupuli 8 Migration

## HOW TO USE THIS FILE (read before editing)
This is an APPEND-ONLY dated decision log. It records WHAT was decided and WHY,
as immutable history — NOT the current design state.

- Entries are IMMUTABLE. Never edit or delete an existing entry.
- To change a decision, APPEND a new dated entry that references and supersedes
  the old one (e.g. "2026-08-01 — Supersedes 2026-07-01 D3; now ..."). The old
  entry stays as-is, true as a record of what was decided then.
- This structure is deliberate: an append-only log cannot "drift" or "lie" the
  way a current-state document can, because it never claims to be current — it
  claims to be what happened, which is fixed. Do NOT "tidy" this into a
  current-state summary; that would reintroduce the exact drift risk the log
  exists to avoid.
- Nothing on the machine reads this file. Its audience is future sessions
  (which lose chat-history context on compaction) and humans. The git repo is
  the only compaction-surviving store in this project, which is why the
  rationale lives here rather than in any chat's context.

Format of each entry: `## YYYY-MM-DD — <short title>` then Decision / Rationale
/ Evidence (where applicable).

---

## 2026-07-01 — Declared upstream baseline: release-0.9.8
Decision: infra_populi is migrated FROM puppet_infrastructure `release-0.9.8`
(== 0.9.9 for manifests/; 0.9.9 added no manifest changes over 0.9.8). This is
the reconciliation target for Phase 1. Full detail in UPSTREAM_BASELINE.md.
Rationale: migration commits span 2026-02-17..04-29, predating the 0.9.8 tag
(2026-05-21); classes were migrated from the old repo's live dev HEAD, not a
tag, making the new repo a temporal patchwork of the 0.9.7→0.9.8 dev period.
0.9.8 is the first stable tag the newest work aligns with.
Evidence: logging subsystem rewrite (0.9.7 had logfiles.pp/timezone_syslog.pp;
0.9.8 has rsyslog_*), and infra_populi already carries the rsyslog_* names —
proving later migrations pulled 0.9.8-era content.

## 2026-07-01 — Ruling B: forward-only provenance annotation
Decision: the 15 historical migrations stay as plain `Done` in
migrated_classes.txt. They are NOT stamped `[from: release-0.9.8]`. Only classes
migrated going forward carry the annotation. A historical class earns the
annotation only after it is reconciled to 0.9.8 content during the end-of-Phase-1
reconciliation pass.
Rationale: the annotation must be factually true; the 15 predate the 0.9.8 tag
and came from live dev HEAD, so stamping 0.9.8 would record false provenance.
Marker semantics going forward: plain `Done` = migrated but NOT yet reconciled
to 0.9.8 (the reconciliation backlog); `Done [from: release-0.9.8]` = migrated
AND confirmed at 0.9.8 content.

## 2026-07-01 — migrated_classes.txt was already correct (no fix)
Decision: no correction commit was applied to migrated_classes.txt.
Rationale: an initial analysis reported a "7 false / 7 missing Done" discrepancy;
re-inspection with `cat -A` showed the file uses two interchangeable marker
positions — `X Done` (later Codex entries) and `Done X` (early hand entries) —
both meaning migrated. The file already matched git history 15:1. The empty
`git status`/`git diff` was conclusive: HEAD was clean, nothing to fix.
Standing rule: edit migrated_classes.txt only for real state changes, never
cosmetics. Do NOT normalize the `Done X` / `X Done` format (the position is a
mild provenance signal; editing risks reintroducing errors).
Process lesson: raw-inspect unknown file formats (`cat -A`) BEFORE proposing
edits, not after.

## 2026-07-01 — Pattern A: leaf classes self-declare prerequisite dirs inline
Decision: leaf classes declare the prerequisite `file` directories they need
INLINE (mirroring firewall.pp), rather than depending on a shared base class.
Applies to the filesystem_*/script-dropping family.
Rationale: consistent with already-GREEN firewall and sysmon_puppet_cert_status;
preserves the one-class-at-a-time harness invariant (a shared base would force
classifying base+leaf together, breaking it). The duplicate-declaration risk is
composition-time only and never fires under isolated classification.
Deferred: shared-base extraction (pattern B), IF ever wanted, is a composition-
time UNIFORM refactor — pattern-A-everywhere makes that refactor mechanical.
Requirement: inline dir declarations must match firewall.pp's structure
identically (same ensure/ownership/mode/path construction) to keep any future
refactor uniform.
Triggered by: filesystem_yum, which require'd ${localdir}/bin without declaring
it → could not compile standalone.

## 2026-07-01 — migration_plan.md: analysis-only pass, advisory, git-derived done
Decision: a one-time Codex analysis pass scores every class (two separate scores
— complexity and dep_score — plus deps), producing migration_plan.md. The pass
is READ-ONLY: no node changes, no harness, no manifest edits, no commit beyond
the plan file. Run via plain `codex exec`, NOT the codex_migrate_class wrapper
(which is built to edit+commit). Plan file carries a provenance header (date,
baseline scored against, and that scores/deps are advisory, re-validate if module
structure changes materially).
Rationale: name/line-count judgment misses hidden dependencies (the yum lesson);
systematic evidence-based scoring is needed. Two scores not one: a blended score
would rank yum "easy" and hide the dependency that governs ordering. Separating
ordering-drivers (deps) from effort-drivers (complexity) preserves the signal
that matters for sequencing.
Precedence (authority): git > migrated_classes.txt (canonical) > migration
plan/order files (advisory). The `[from: release-0.9.8]` annotation lives in
migrated_classes.txt only, never split across files.

## 2026-07-01 — Analysis pass may read master Hiera (read-only, constrained)
Decision: the analysis/scoring pass MAY read master Hiera to produce fully-
resolved dependency scores (no "verify" flags), overriding the earlier "repo-only"
steer. Constraints: (1) read-only, Hiera data files only — read/write/run nothing
else on the master; all other read-only constraints stand. (2) Read hiera.yaml
FIRST to learn the hierarchy, then the relevant data files — do NOT read only
common.yaml and assume that is the whole hierarchy (a dep resolving in a higher
tier would be silently mis-scored). (3) The plan header records which Hiera files
were read, from which host, on what date.
Rationale: in Salatiel's own test env, read access to Hiera is negligible risk
and materially improves scoring accuracy, saving future re-verification. The
"repo-only" default existed to avoid unnecessary master access; this access is
justified, so the tradeoff flips. Grant is minimum-necessary: a narrow read-only
window, not broad master sudo.

## 2026-07-01 — Model 3: migration_order.md git-authoritative + regenerated
Decision: migration_order.md's DONE/PENDING status is git-derived, always
REGENERATED from git (`git log | grep "P8: migrate"`), never hand-edited. A
committed regen script (.codex_state/gen_migration_order.py) rebuilds the file;
Codex runs it as its final loop step after each P8: migrate commit lands, so the
next PENDING row is current automatically. No `done_utc` column (git commits
carry authoritative timestamps; a hand-written timestamp is a driftable second
fact). Committing the order file is BLOCKED until the regen script is committed
alongside it.
Rationale: rejected Model 1 (Codex hand-writes DONE inline) — "drift is
detectable" is exactly what failed with migrated_classes.txt; detect-after-the-
fact is not a mitigation. The reframe: "auto-advancing next-pointer" and
"hand-written DONE status" are separable — Salatiel's efficiency goal (pointer
advances automatically, "just do the next class") is delivered by cheap
regeneration, with zero hand-written done-claims. Regen-don't-hand-maintain makes
drift impossible by construction.

## 2026-07-01 — Option A: structured internal_deps column, not in-script graph
Decision: dependency data for ordering is a machine-readable `internal_deps`
column in migration_plan.md (comma-separated bare internal class names, true hard
deps only, empty if none, NO prose). The regen script parses ONLY internal_deps
— no regex over prose, no dep-graph curated inside the script. Order file = pure
function of (plan's structured columns + git). Generating internal_deps was a
narrow additive Codex pass (not a re-score); the parser audit's known-tricky
cases (postfix_smtp_base_config_file, user_samba, user_sysmon, firewall) are the
acceptance test — exclude reverse relations ("declared by X" ≠ dep), "-like",
external modules, substring coincidences.
Rationale: rejected Option B (curated dep-graph in the script) — it relocates a
driftable second copy of the dependency facts into the .py; when the plan is
re-scored, an in-script graph doesn't auto-update. Same failure class as tracker
drift and the done_utc column. "Derive, don't duplicate" applies to the dep-graph
too; convenience is not grounds to exempt it.
Evidence (validates Option A): Codex's structured internal_deps was MORE correct
than the hand-curated checklist — it correctly excluded `firewall` as a hard dep
for the firewall_addons, proven by those addons compiling GREEN in isolation, and
correctly handled optional/or-branch deps the hand-curation over-included.
Structured-from-source beat hand-curated on ACCURACY, not just maintainability.

## 2026-07-01 — Generation model: Codex generates in-repo, Claude verifies independently
Decision: division of labor for in-repo artifacts — Codex GENERATES + COMMITS
all in-repo artifacts (regen script, order file, trackers, this file); Claude
SPECS the behavior and VERIFIES output independently; Salatiel relays + approves.
Artifacts are born in the repo via Codex, never in Claude's scratch environment.
Rationale: refines (does not contradict) the Model 3 "commit script + order file
together" ruling — only authorship moves to Codex, where repo/commit access
lives. Closes the scratch-environment shuttle (a hidden-dependency trap: an
artifact that secretly depends on Claude handing over a file each time).

## 2026-07-01 — Standing principle P1: independent verification yardstick
Principle: when Codex generates an artifact, Claude's verification MUST derive
from an INDEPENDENT source (git, first-principles reasoning, an independently-
built model) — never from the Codex artifact being checked. Independence of the
yardstick is what makes delegated generation safe rather than circular (Codex
grading its own homework).
Basis: the internal_deps cross-check had value precisely because Claude's
comparison graph was built independently of Codex's output.

## 2026-07-01 — Standing principle P2: derive, don't duplicate
Principle: do not create a second hand-maintained copy of a fact that can drift
from its source. Prefer a single source of truth + derived views (e.g. git as
authoritative done-set; order file regenerated from git; scores structured in the
plan, not duplicated in a script). Append-only history (dated logs, forensic
records) is EXEMPT — it is not a copy-of-state that can drift; it is immutable
fact.
Basis: reaffirmed repeatedly this session — migrated_classes.txt drift, the
rejected done_utc column, the rejected in-script dep-graph.

## 2026-07-01 — Known gap: node_base → puppet_boot_run edge missing in internal_deps
Decision: leave the missing `node_base` → `puppet_boot_run` dependency edge in
internal_deps as-is (do not patch).
Rationale: ordering-irrelevant — the topology routes around it via shared
filesystem_base, so the missing edge does not change migration sequence. Recorded
here as a CONSIDERED omission, not an oversight. Revisit only if composition ever
depends on this edge directly.

## 2026-07-01 — Blocked Forge dependency is an escalation trigger, not a loop-internal decision
Decision: when a class depends on a Forge module/custom type that will not load on
Puppet 8, Codex must STOP and escalate — it does NOT silently reimplement the class's
behavior. The resolution is a genuine fork with distinct options: (a) find a
Puppet-8-compatible replacement module; (b) fix the dependency's incompatibility;
(c) reimplement without the dependency; (d) defer/mark the class blocked. Codex may
not unilaterally pick (c) — it is the most invasive (changes behavior, diverges from
upstream), and the choice has project-level implications only higher-level judgment can weigh.
Rationale: Phase 1 is SYNTAX migration with behavior preserved. "Make it functionally
different so it compiles" crosses into redesign (Phase 3 territory). GREEN in Phase 1
means "syntax compiles/applies," NOT "behavior preserved" — optimizing for GREEN via
reimplementation optimizes the wrong signal. Recurs across the module (multiple classes
use custom types from possibly-incompatible modules), so it is policy, not per-case.
Triggered by: network_dhcp — Codex reimplemented network_config as raw ifupdown file-writing
because it produced GREEN fastest, without flagging the behavior change.

## 2026-07-01 — network_dhcp: BLOCKED, reimplementation preserved as candidate (not Done)
Decision: network_dhcp is marked BLOCKED, not Done, and carries NO [from: release-0.9.8]
annotation. Codex's reimplementation (commit 48fc434) was backed out of production via a
corrective commit (03cb002, message deliberately NOT "P8: migrate"), the production manifest
restored to its pre-migration original, and the reimplementation preserved as a candidate at
.codex_state/candidates/network_dhcp.reimplemented.pp (with a header noting: diverges from
0.9.8, drops puppet-network/filemapper, behavioral-equivalence unverified).
Rationale: the reimplementation is not a faithful migration (same false-provenance problem
Option B prevents), and it was discovered as a fait accompli, not evaluated as a decision.
It is preserved (not discarded) as a candidate approach pending cluster resolution, but not
blessed as done.

## 2026-07-01 — New marker state: reimplemented/diverged
Decision: R2's two marker states (plain Done = migrated-not-reconciled; Done [from:
release-0.9.8] = migrated-and-faithful) gain a third for classes that work but deliberately
diverge in approach from upstream: Done [reimplemented: diverges from release-0.9.8 — see
DESIGN_DECISIONS.md]. It is honest about non-faithfulness — "this works, but it is NOT the
upstream approach."
Caveat: this marker is for CONSIDERED, ACCEPTED divergences only. A class does not earn it
while it has an unexamined behavioral-risk (network_dhcp does not get it — it stays blocked
until the divergence is a decided question).

## 2026-07-01 — Encode annotation discipline into the migration invocation
Decision: the marker rules (plain Done vs [from: release-0.9.8] vs [reimplemented: ...]) must
be encoded INTO the migration invocation (wrapper or per-class instruction), so the correct
marker is applied at migration time in the same commit — not hand-corrected after.
Rationale: Codex omitted the [from: release-0.9.8] annotation on BOTH forward migrations so far
(filesystem_yum, network_dhcp) because the generic wrapper prompt does not mention the marker
rules. Two misses is enough evidence to fix the cause, not keep hand-correcting.

## 2026-07-01 — Model-3 bug fix: derivation must be revert-aware (currently-migrated, not ever-migrated)
Decision: the git-derived done-set must reflect CURRENTLY-migrated, not "ever had a P8: migrate
commit." gen_migration_order.py was made revert-aware + blocked-aware:
done = (git P8:migrate classes) MINUS (blocked-list), with a supersession GUARD.
- Supersession guard: for each migrated class, if a commit LATER than its MOST-RECENT P8:migrate
  commit touched that class's manifest, the script FLAGS it "possibly superseded — verify" —
  it does NOT silently trust either reading. Catches the general revert case; its edge case
  (unrelated later edit) degrades to a flag, never a wrong answer. No commit-message parsing.
- Blocked-list (.codex_state/blocked.txt, tracked, one reason per entry): the AUTHORITATIVE
  exclusion. A blocked class is never counted done even with a P8:migrate commit.
Rationale: "count P8:migrate commits" silently assumed migrations are never reverted;
network_dhcp (migrated then backed out) proved otherwise. Rejected: message-convention detection
(fragile — human must maintain a naming pattern); pure tree-state (no reliable machine signature
for "migrated"). The two mechanisms are belt-and-suspenders with correct sourcing: blocked-list
gives the authoritative answer, the guard catches the human-error case (revert without updating
the list). Worst case the derivation flags "verify" — never a silent false Done.

## 2026-07-01 — "Done" and "blocked" are different facts with different sources (P2 clarification)
Principle clarification: "migrated" is a GIT fact (derivable). "Blocked" is a HUMAN-DECISION
fact git cannot express — git cannot distinguish "deliberately held" from "not yet reached"
from "migrated-then-reverted." So blocked REQUIRES a recorded source (blocked.txt), and this
does NOT violate P2: P2 forbids duplicating a DERIVABLE fact, not recording a NON-DERIVABLE one.
A blocked-list is the primary (only possible) home of a fact with no other source — same P2
exemption as append-only history, not a driftable copy of the done-set.

## 2026-07-01 — network_config is a module-wide blocker; block the networking cluster; resolve at module level
Decision: the entire networking/OpenVPN cluster is BLOCKED on the shared root cause that the
network_config / network_route custom types (from puppet-network, needing puppet-filemapper)
fail to load on Puppet 8. Blocked: network_dhcp, network_static, openvpn_server, network_vpn —
each verified by manifest inspection to use these types (network_dhcp: 1 resource; network_static:
network_config + network_route; openvpn_server: 4 network_config incl. br0 bridge with bridge_ports/
loopback-aliasing/subscribe refs; network_vpn: transitively, chains openvpn_server).
Resolution strategy: resolve network_config ONCE at module level — (a) a Puppet-8-compatible
network-interface module, or (b) fix filemapper's incompatibility — NOT per-class reimplementation (c).
Rationale: the network_dhcp reimplementation worked only because it was one trivial resource — a
LOCAL success masking a SYSTEMIC problem. Extrapolating (c) to openvpn_server's bridge stack would
produce four independent hand-rolled reimplementations, each diverging from upstream, high-risk on
the bridge config — multiplying the divergence problem. Fix the root, not each leaf.
Correction of an earlier inference: openvpn_server does NOT depend on network_dhcp (it declares its
own network_config for lo/lo:0/br0); the escalated "reimplementing network_dhcp breaks the OpenVPN
stack" concern was moot — they are independent. The real problem is module-wide, not a network_dhcp
quirk. (P1 discipline: the code overturned the inferred coupling.)
Open question (deferred): a-vs-b is a dedicated future investigation — (a) is there a maintained
Puppet-8-compatible network module covering dhcp/static/bridge/alias? (b) is filemapper's incompat
small/patchable or a deep rewrite? Not decided now; opened deliberately when the non-blocked queue
is exhausted or networking is prioritized.

## 2026-07-01 — Known limitation: the plan cannot predict external-type blockers
Note: migration_plan.md's internal_deps column tracks internal-CLASS dependencies, not external
custom-TYPE availability. So the plan cannot predict which classes will hit a network_config-style
"module won't load on Puppet 8" wall — those are discovered reactively by reading each manifest
before migrating it. Practice: before migrating a queued class, check its manifest for custom types
from external modules whose Puppet-8 compatibility is unverified, not just its internal_deps.

## 2026-07-26 — Harness invariant evolves: one target class + its DECLARED required base
Decision: the strict one-class-at-a-time classification invariant is relaxed, narrowly.
Default remains STRICT ISOLATION (one class, nothing else) — this is the norm and must
stay, it has caught real dependency bugs (filesystem_yum). EXCEPTION: a class that
DOCUMENTS a required base may be validated with that SPECIFIC declared base classified
alongside it. Not arbitrary extra classes — only the base the class itself declares.
Rationale: the original invariant silently assumed every class is independently
validatable. firewall_addon_hosting disproved that for a whole category — incremental
layer classes that presuppose a base. Crucially, strict isolation produced a FALSE
NEGATIVE here: it tested a state that NEVER EXISTS IN PRODUCTION (the addon is never
applied without a base firewall), so base-context testing is MORE faithful to real
behaviour, not a weakening of rigour. Rejected: repairing node state out-of-repo to
force a green (non-reproducible hack; validates nothing).
Implementation: the required base is an EXPLICIT input to the harness — Codex does not
guess which base to add; the class's own documented requirement is the source of truth.
Per the generation model: Claude specs, Codex implements, Claude verifies. Capability
WILL be built (firewall_addon_hosting is not indefinitely blocked); first validated on
that class.
Practice (parallel to the 2026-07-01 external-type-blocker note): before migrating a
queued class, also check whether it alters node->master connectivity — OUTPUT chain
policy/purge, default-drop rules, or anything that would sever the agent's NEW outbound
connection to master:8140. The plan cannot predict this either.

## 2026-07-26 — Block-category taxonomy: three distinct causes, three resolution paths
Decision: "blocked" alone is uninformative; blocked.txt entries must state the CATEGORY,
because each has a different owner and resolution path. Three categories are now proven
by real cases:
  1. DEPENDENCY-INCOMPATIBILITY — an external module/custom type will not load on
     Puppet 8. Class cannot compile. Resolution: fix at MODULE level (compatible
     replacement, or patch the dependency), never per-class reimplementation.
     Case: networking cluster (network_config via puppet-network/puppet-filemapper).
  2. REIMPLEMENTATION-DIVERGENCE — the class compiles/applies, but the migration is not
     faithful to upstream (behaviour was redesigned, not translated). Resolution: an
     explicit fork ruling on whether to accept divergence, with the candidate preserved
     but not blessed. Case: network_dhcp.
  3. HARNESS-CAPABILITY-GAP — the migration is CORRECT and faithful, but the harness
     cannot validate it. Nothing wrong with the code. Resolution: build the missing
     harness capability. Case: firewall_addon_hosting.
Rationale: conflating these would misroute the fix — e.g. treating a capability-gap as a
code problem would wrongly discard correct work, and treating a module-wide dependency
failure as a per-class problem would produce N divergent hand-rolled reimplementations.
Convention: candidates are preserved as TRACKED files under .codex_state/candidates/
(force-added past the .codex_state/ exclude). Local-only preservation is not durable
enough — a candidate must survive clone and compaction, consistent with every other
durable record in this project.

## 2026-07-26 — Toolchain change: Codex 0.145.0, gpt-5.6-sol, reasoning effort xhigh
Decision: upgraded Codex 0.130.0 -> 0.145.0; model gpt-5.5 -> "gpt-5.6-sol";
added model_reasoning_effort = "xhigh" in ~/.codex/config.toml. Previous config backed
up to ~/.codex/config.toml.bak.<ts>.
Rationale for xhigh over ultra: GPT-5.6 exposes six effort levels (low, medium, high,
xhigh, max, ultra). Published comparisons put Sol at max ~59/100 vs xhigh ~58 — about
one point for roughly 3x the tokens; ultra sits above max and decomposes work by
spawning parallel internal sub-agents. Our per-class migration tasks are small,
procedural and well-scoped — the wrong shape for ultra's decomposition, and ultra
multiplies cost because spawned subagents INHERIT the parent's model and effort. xhigh
sits at the knee of the quality/cost curve. Ultra remains available as an explicit
per-run override (-c model_reasoning_effort="ultra") for genuinely hard work: the
network_config a-vs-b module investigation, and the base-context harness build.
Verification performed (15-version jump warranted proof, not assumption): trivial run
confirmed model=gpt-5.6-sol and reasoning effort=xhigh in the session header, auth OK;
wrapper-style invocation confirmed the -c overrides STILL PARSE on 0.145.0
(sandbox: danger-full-access shown in header) and left the repo worktree unchanged.
Noted change: sandbox writable roots are now [workdir, /tmp, $TMPDIR] — the
~/.codex/memories path is no longer a writable root (was in 0.130.0). Also noted: from
Codex 0.134.0, --profile no longer reads [profiles.name] tables from config.toml
(profiles live in separate files). Does not affect us — the wrapper uses -c overrides,
not profiles.

## 2026-09-30 — Production master inspected: module identities, upstream bug, dependency roadmap
Evidence (puppet.mdops.es, Puppet 5.5.22, read-only inspection):
- network_config/network_route come from puppet-network 0.10.1 + puppet-filemapper 3.1.0 +
  puppet-boolean 2.0.2 (boolean is now deprecated/archived upstream).
- sysctl comes from thias-sysctl 1.0.7 — a DEFINE (sysctl/manifests/init.pp), not a native type.
  Earlier inference "rules out thias" was wrong: comments-as-leads, now applied to our own inference.
  thias-sysctl has an open unresolved Puppet 8 legacy-facts issue (#80, Nov 2023). Candidate
  replacement (same call shape): puppet/augeasproviders_sysctl — VERIFY its requirement before adopting.
- htpasswd comes from leinaddm-htpasswd 0.0.3 (on disk since Aug 2014, pre-Puppet-4). Dead; needs a
  replacement, to be found in the batch audit.
- fqdn_rand_uuid: UPSTREAM BUG CONFIRMED. The only occurrence on the production master is the caller
  (openvpn_nm_connection.pp); it is defined nowhere (not stdlib 4.25.1, not any module). That class
  cannot compile in production. Almost certainly a typo for stdlib's fqdn_uuid. Fix belongs upstream
  (maintained by Salatiel/Gustavo), not worked around in the migration.
- Production has NO Puppetfile and NO r10k: modules are hand-deployed (root-owned dirs 2014–2021;
  puppet_infrastructure/meaningful_puppet/docker owned by `deployment`). This is why upstream
  metadata.json declares only stdlib. Our Puppetfile discipline is a real improvement, not tidiness.
- Production runs puppet_infrastructure 0.9.10 (deployed 2026-09-09) — past the declared 0.9.8
  baseline. Reconciliation-pass material.
- stdlib is 4.25.1 in production vs 9.7.0 in the lab; stdlib 9 removed validate_*/is_*. ADDED TO THE
  PRE-MIGRATION CHECKLIST: grep the class for stdlib-4-era functions.
- The full production module list (nginx 0.15, letsencrypt 9.2, openvpn 8.3, mysql 10.5, postgresql,
  rabbitmq, gitlab, camptocamp-systemd 3.0, saz-ssh, apt 7.7, docker 3.14, ...) is the dependency
  roadmap for the remaining Phase 1 classes. Decision: run ONE batch Forge compatibility audit against
  this list, converting future Category-1 blocks into predictions.

## 2026-09-30 — Networking cluster UNBLOCKED: root cause was version pinning, not Puppet 8
Supersedes the 2026-07-01 "network_config is a module-wide blocker" entry (that entry stays as history).
Decision: network_dhcp, network_static, openvpn_server, network_vpn come off blocked.txt. The
network_dhcp reimplementation candidate is retired.
Evidence: puppet-network 2.2.1 declares openvox >= 8.19 (a Puppet-8-API module) and depends on
filemapper < 5.0.0 and kmod < 5.0.0. Unpinned `mod` lines made r10k install filemapper 5.0.0 and
kmod 5.0.0, which `puppet module list` flagged `invalid`. That is the mechanism behind the July
"puppetx/filemapper won't load" error — a major-version bump outside the consumer's declared range,
not an incompatibility. Pinned to filemapper 4.0.0 + kmod 4.1.0, ran `puppet generate types` and
restarted puppetserver, and network_dhcp went GREEN with the ORIGINAL manifest (fixture iface).
Standing rules (all three):
  1. Always pin a module to a version INSIDE its consumer's declared range. Never leave `mod` unpinned.
  2. After every r10k install, run `puppet module list` and treat any `invalid` as a FAILURE.
  3. After adding a module that ships custom types, run `puppet generate types --environment
     production` AND restart puppetserver before testing.
Fixture rule extended: interface names are fixtures too — `p8test0` for network_* classes (the node is
netplan-only; pointing ifupdown at the real NIC is a connectivity hazard).
Lesson: "unverified diagnosis stood for two months" — a Category-1 block must record the exact module
versions installed and whether puppetserver was restarted, or it is not a diagnosis.

## 2026-09-30 — Lab runs OpenVox, not Perforce Puppet
Fact: openvox-agent 8.24.2 / openvox-server 8.11.0 on the lab master. Vox Pupuli modules now declare
`openvox` (not `puppet`) in metadata.json requirements; the lab satisfies them natively.
Implication: no Phase 1 impact (same API). For Phase 6, "Puppet 8 vs OpenVox 8" is a production
runtime decision that belongs with Gustavo — flagged now so it is not a surprise later.

## 2026-10-01 — Ad-hoc `codex exec` calls must close stdin and carry a timeout
Evidence: the network_static header-fix bookkeeping call (`codex exec ... '<prompt>'`, run from the
advisor's shell with stdin an open socket) sat idle in ep_poll for ~47 minutes with no file change.
`codex exec` reads extra prompt input from stdin when stdin is not a TTY; the socket never reached
EOF. Re-run with `</dev/null` completed in under a minute (commit 1e846b7).
Rule: every advisor-issued `codex exec` runs as `timeout <N> codex exec ... </dev/null > <log> 2>&1`.
Never pipe it through `tail` (buffers all output until exit, hiding a hang). The wrapper
`codex_migrate_class` is unaffected in practice but should gain `</dev/null` too — tooling change for
Salatiel to approve.
Also recorded: headers for "validated unchanged" classes MUST name module deps + versions in the
manifest (network_static failed review on this; network_dhcp's header has the same gap — historical,
not retro-annotated here, flagged for the reconciliation pass).

## 2026-10-01 — Baseline drift: 9 pending manifests are NOT release-0.9.8 content
Finding: `d93f147 Baseline import` carried older upstream revisions for 9 pending classes. Verified
byte-identical matches: rsyslog_server == upstream 3fa2cc1 (2025-06-25); ssl_base == 2388bd7
(2025-02-20). Also differing from release-0.9.8: user_kde_lock_screen, puppet_boot_run,
letsencrypt_base, filesystem_apt, user_desktop, user_desktop_sudoer, node_base_desktop. The other
pending manifests are identical to 0.9.8.
Why it matters: the wrapper runbook never tells Codex to bring a class to 0.9.8 content, and the
reviewer diffs against 0.9.8. A "validated unchanged" run on drifted content either fails review or
stamps false `[from: release-0.9.8]` provenance (violates Ruling B).
Decision (advisor tier): ADDED TO THE PRE-MIGRATION CHECKLIST — diff the local manifest (and its
templates/files) against release-0.9.8 before invoking Codex. Drifted classes are blocked pre-Codex
with evidence and escalated. Whether to baseline-sync (option A), defer to reconciliation (B) or use
a distinct marker (C) is Salatiel's ruling: .codex_state/escalations/rsyslog_server.md.
Blocked so far: rsyslog_server, ssl_base (ssl_base gates 7 dependents).

## 2026-10-01 — required_base must cover parent dirs/resources a class needs from another class
puppet_commush (`require => File["${localdir}/bin"]`) and hello_world_flask_common (dir under
/opt/puppet-infrastructure, absent on the baseline node) both list filesystem_base in internal_deps
but had empty required_base, which is the ONLY column the harness expands. internal_deps is ordering
metadata; it does not put the base in the test catalog. Set required_base=filesystem_base for both
pre-Codex; both went GREEN and passed review. Expect the same for the other filesystem_base consumers
(backup_rsnapshot_pre, filesystem_apt, filesystem_yum, firewall_secure*, hashman_base,
hello_world_flask) — check each at hazard item 4 rather than bulk-editing the plan.
Convention observed: Codex now titles its order commit `P8: record migration order after <class>`;
reviewers have accepted it as the regenerate commit. The reviewer's check 1 still names
`P8: regenerate migration order` literally — align the wording (Salatiel's tooling).

## 2026-10-01 — Ruling: baseline drift resolved by baseline-sync (option A)
Decision (Salatiel): a pending class whose local manifest differs from release-0.9.8 is brought to
0.9.8 content BEFORE migration, in its own commit `P8: baseline-sync <class> to release-0.9.8`,
then migrated through the normal wrapper/reviewer loop. Supersedes "block and escalate" from the
baseline-drift entry above (that entry stays as history).
Procedure (advisor tier; it is a verbatim copy, so no Codex call):
  - `git -C ~/work/puppet_infrastructure show release-0.9.8:<path> > <path>` for the manifest and
    every template/file the 0.9.8 manifest references; verify each with diff -q afterwards.
  - Sync a template/file automatically only if no OTHER class (per release-0.9.8 `git grep`) uses it.
    A shared template whose 0.9.8 content differs from local, consumed by an already-Done class, is
    still Salatiel-tier: escalate (it changes a migrated class's behaviour).
  - Check that the 0.9.8 manifest does not rely on 0.9.8-only content of an internal dependency
    (params, resources) that our local copy lacks; if it does, escalate.
Applied: rsyslog_server (manifest + listener_simple.conf.epp + new rsyslog-hosts.logrotate.epp;
0.9.8 server needs only include rsyslog_base + Service['rsyslog'] from base) and ssl_base (manifest
only). Both unblocked. Remaining drifted pending classes are synced as the loop reaches them.
CLAUDE.md hazard checklist gains item 8 to carry this into every class.

## 2026-10-05 — Identity preconditions order a define after user_base (internal_deps), not a block
Finding: user_kde_lock_screen's exec runs `user => $title` (fixture p8testuser). The fixture account
is deliberately absent on the baseline node, so the exec/unless cannot execute until something
creates the user. In code the define does not depend on user_base (production callers user_desktop*,
node_base_desktop supply the account); on the test node it does.
Decision (advisor tier, plan fix): add user_base to internal_deps (test-node ordering edge, consistent
with internal_deps being an environment-specific projection) and set required_base=filesystem_base,user_base.
Rationale: a required_base must itself be validated first; user_base is pending (complexity 7), so
borrowing it earlier would test an unproven base. required_base does not affect ordering in
gen_migration_order.py — only internal_deps does. Prose depends_on unchanged.
Apply the same check to any define with `user =>`/home-path consumption of its title (hazard item 4).
Also: baseline-sync of files/user_kde_lock_screen/configure_lock_screen.sh (dd3e1dc) was done with
user_kde_lock_screen_common; its other consumer is user_kde_lock_screen (pending). When that define is
synced, 0.9.8 renames mytimeout/mylockgrace -> screenlock_timeout_minutes/screenlock_grace_seconds;
its local callers user_desktop, user_desktop_sudoer, node_base_desktop are pending AND drifted, and their
0.9.8 versions already use the new names — sync each at its turn; none is Done, so no escalation.

## 2026-10-26 — HQ rulings on the engine diagnosis (batch entry)
Source: `.codex_state/escalations/2026-10-26-engine-rulings.md` (authoritative text; section refs
are to `.codex_state/diagnosis/2026-10-26-engine-diagnosis.md`). One entry per ruling batch, as HQ asked.
1. Baseline → release-0.9.10. SUPERSEDES 2026-07-01 "Declared upstream baseline: release-0.9.8" and
   the UPSTREAM_BASELINE.md "do not chase 0.9.10+ mid-phase" policy. Condition confirmed:
   release-0.9.8..release-0.9.10 touches only docker_container.pp, rsyslog_server.pp and four rsyslog
   templates. Tools and instructions name release-0.9.10, never upstream HEAD. `[from: release-0.9.8]`
   → `[from: release-0.9.10]` only where manifest+templates+files are byte-identical between the refs
   (script-verified, one commit). docker_container is re-migrated under the new gate; rsyslog_server
   migrates from 0.9.10 directly (SUPERSEDES its 2026-10-01 sync-to-0.9.8 and withdraws the CTO
   question). The Issue #122 mysql rewrite stays out until released (CTO decision 5).
2. GREEN v2 (Epic 1, 1.1–1.5) approved in full: run 2 must exit 0; `executed successfully` and
   `removed` on run 2 fail; outer `timeout` on every agent run and every `codex exec`; revert-first in
   wrapper and reviewer; coverage signal; reviewer v2 (templates/files diffed, two-diff method, JSON
   verdicts, header module claims vs `puppet module list`, scope check on blocked.txt/candidates);
   re-review sweep of the 31 done classes. SUPERSEDES the "practical idempotency" GREEN (run-2 regex,
   rc 2 accepted). Until the sweep ends the 31 are "done under gate v1", not quoted externally as verified.
3. Generation model: three paths by class category. Unchanged-validated (manifest+templates+files ==
   baseline, pregate + compile-only pass) → advisor reverts, runs harness, writes header + tracker,
   `record_green.sh` commits, no Codex. Syntax-work → Codex with the orientation packet; one run per
   class is the target, a second needs a reason in the run record. Records → `record_green.sh` only.
   The reviewer never learns who authored a change. SUPERSEDES 2026-07-01 "Generation model: Codex
   generates in-repo" (artifacts "born via Codex"), which practice had already departed from.
4. Pre-VM gates (Epic 2) approved: `pregate.sh` on the laptop; `test_class.sh --compile-only` on the
   master plus standing composite compiles after every green. puppet-lint and the pre-commit hook are
   mandatory.
5. Overhead (Epic 3) approved: Tier-0 revert (confirm GRUB cause by console screenshot first;
   GRUB_RECORDFAIL_TIMEOUT=2, not 0; apt-daily/unattended-upgrades timers off in the baseline; hard
   poweroff for the NODE ONLY; new snapshot P8NODE_BASELINE_GREEN_v2). The master keeps ACPI and its
   never-restore rule. Orientation packet + record_green.sh; per-attempt metrics JSONL (tracked, own
   commit `P8: record metrics after <class>`, reviewer-exempt); single sources (one hazard checklist
   file, runbook in the repo, Puppetfile exported on every change, generated rules digest).
   Host-only/static-IP network is the first project AFTER the sprint.
6. Lab master: extra_files mount + throwaway p8test PKI + Hiera fixture keys built by an idempotent
   script in `.codex_state/tools/`, nothing production-derived, then a new master snapshot. Pin the 5
   unpinned Puppetfile lines to today's installed versions first. 6a: `passwd_common` on puppet8master
   is LAB-LOCAL (every master carries its own; not a copy of production's) and stays in puppet8node.pp
   as part of the lab baseline. Its resource types/titles are listed via compile-only (never file
   contents) so coverage and the reviewer can separate them from the target's. The engine never reads
   or edits it; harness runs depend on nothing it manages except the harness user's SSH access.
7. Modules: sysctl = thias-sysctl 1.0.8 (fallback augeasproviders_sysctl with the /etc/sysctl.conf
   delta recorded as a behaviour difference) — SUPERSEDES the 2026-09-30 "candidate replacement
   augeasproviders_sysctl" lead and blocked.txt's "no Puppet 8 module" text. htpasswd = citrin-htpasswd
   1.0.3 after the advisor diffs its providers against leinaddm 0.0.3 (identical-semantics swap =
   advisor tier). user_samba stand-in script accepted, status "mock-apply only / behaviour unverified".
   Pins inside the consumer's range; `invalid` = failure; generate types + restart after custom types;
   Windows-only dependency warnings (puppetlabs-powershell, puppetlabs-reboot via docker) are EXPECTED.
8. Classes: puppet_boot_run provisional = drop `ensure => running`, keep `enable => true`, recorded as
   "upstream defect fixed locally" unless upstream 4ae2e35 shows a conflicting intent (then ask HQ).
   Import gnome_lock_screen, firewall_ipv6_drop_policy_desktop, rsyslog_apparmor_exception as
   baseline-sync. Defective done classes reconcile to the baseline shape via the normal loop after the
   sweep: sysmon_puppet_cert_status re-migrated faithfully (its apt_update replacement is a Phase-1
   violation); filesystem_yum loses its duplicated directories and gets correct provenance — this
   SUPERSEDES 2026-07-01 "Pattern A: leaf classes self-declare prerequisite dirs inline" (now superseded
   by required_base); network_dhcp 0ecf985's extra edits are recorded, not reverted; deleted body
   comments/warnings restored where the baseline has them. Fixture rule enforced retroactively
   (firewall_addon_caching_nameserver.json → p8test0). `nginx_frontend_domain.pp:247` `Integer()` is a
   syntax fix (Puppet 8 strict mode).
9. Queue (Epic 4): plan fixes; Forge pins (non-openvox-only now, the 8 openvox-only pins prepared but
   unapplied until the CTO runtime answer); baseline-syncs; escalation files; `prod_nodes` secondary
   sort key. Order: node_base closure leaves first, then nginx/ssl, composites last within their cluster;
   zero-declaration classes sink to the bottom until the CTO rules.
10. Infrastructure: second (host-only) NIC on the node VM inside the sprint. EL9 + Ubuntu Incus
    containers after the sprint. RHEL9 VM after the CTO's RHEL count. Desktop VM in Phase 3. Samba DC deferred.
11. Phase 3: YAML check format with mandatory `derived_from` upstream lines and negative controls that
    must fail on the clean baseline. Pilots after the sprint: backup_rsnapshot, ssh_secure,
    nginx_static_domain; then the node_base closure. CLAUDE.md gains a Phase-3 scoping section.
12. Process: hazard items 9–13 approved. `.git/info/exclude` wholesale `.codex_state/` exclusion is
    replaced by an explicit `.gitignore` (logs and necessary_modules.txt stay ignored, everything else
    under .codex_state/ tracked, no more `git add -f`) — SUPERSEDES the 2026-07-26 convention
    "candidates force-added past the .codex_state/ exclude". Toolchain recorded retroactively (below);
    a 1-class canary re-run is mandatory after any toolchain change. Diagnosis files are committed only
    after the passwd-layer class-name list is reduced to a count. A generated "current rules" digest is approved.
13. Sprint order: 0 → 3.1 → 1.1–1.3 → 2.1–2.2 → 1.4 → 1.5 + HQ checkpoint → 3.2–3.5 → 4.1–4.3 + HQ
    checkpoint → resume /migrate-next with metrics. One commit per step (`P8: engine:`), never with
    unrelated worktree changes. "6–9 h for 50 classes" is a target to be tested, not quoted outside.
Toolchain (retroactive record; SUPERSEDES 2026-07-26 "Codex 0.145.0, gpt-5.6-sol" as current state):
codex-cli 0.159.2, model gpt-6.1-sol (changed 2026-09-30 per ~/.codex/config.toml.bak.20260930_234019,
no entry at the time), reasoning effort xhigh, Codex plugin skill "superpowers" 6.4.2
(openai-curated-remote) observed loaded in runs; advisor claude-opus-5-5; reviewer subagent
`model: opus` (unpinned alias in .claude/agents/reviewer.md).

## 2026-10-26 — HQ amendment: the laptop is a production Puppet 5 node; ruling 4 amended; baseline confirmed
Fact: the advisor laptop is a PRODUCTION Puppet 5 node (puppet-agent 5.5.22 at /opt/puppetlabs, agent
service active). Rule: no system ruby, no Puppet 8 packages, no gems are installed on it; nothing in the
engine runs `puppet` on the laptop. (The advisor's earlier request to `apt install puppet puppet-lint`
there is withdrawn; shellcheck 0.11.0 and bats 1.13.0 were installed instead.)
Ruling 4 AMENDED (supersedes "pregate.sh on the laptop ... parser validate, allowlisted puppet-lint" as
to WHERE): `puppet parser validate` and puppet-lint run on puppet8master over ssh. puppet-lint is
installed with /opt/puppetlabs/puppet/bin/gem at a pinned version by the master-fixtures script
(ruling 6). pregate prints the tool versions it used. Everything else in pregate stays laptop-side.
Ruling 1 baseline pin CONFIRMED: release-0.9.10 == upstream commit cf477c6 (not the moving branch).

## 2026-10-26 — passwd_common (lab-local) resource listing, per ruling 6a
Provenance (ruling 6a): `passwd_common` on puppet8master is lab-local, part of the lab baseline in
puppet8node.pp, not a copy of production's; the engine never reads or edits its source.
Listing via compile-only (`test_class.sh --compile-only`, filter `.codex_state/tools/compile/filter.rb`,
types/titles only): Class[Passwd_common] is in puppet8node's catalog and declares **0 resources**
(every compile on 2026-10-26: puppet_backup, node_base debian/redhat attempts, meaningful_desktop
closure). Coverage (harness and compile) selects a target's resources by class tag, so passwd_common's
resources — if it ever gains any — are never attributed to a target; the filter prints a PASSWD_COMMON
count/title line on every compile so a change is visible. Harness dependence on it: none observed beyond
the harness user's SSH access (it manages nothing on the node today).
Incident (recorded for honesty): while prototyping, a ruby JSON parse error echoed one full puppet8node
catalog into the advisor's terminal. With Passwd_common empty, no passwd content was exposed. The shipped
filter withholds the input on every error path (lab-tested with a marker string).

## 2026-10-26 — Node revert refreshes apt lists (correction to sprint step 3.1)
Finding (1.5 sweep, caching_nameserver): on P8NODE_BASELINE_GREEN_v2 `Package[bind]` failed with mirror
404s (`bind9_9.18.39-0ubuntu0.24.04.2` no longer in the pool). The snapshot's /var/lib/apt/lists date
from 2026-02-17; under the old baseline the apt-daily timer refreshed them shortly after each boot (the
diagnosis saw lists dated 10-15/10-18 on restored nodes). Disabling the timers (ruling 5) froze them.
Decision (advisor tier; keeps the ruled snapshot unchanged): revert_node.sh runs a synchronous
`apt-get -q update` (timeout 180 s) after boot and before any harness run, and fails the revert if it
fails. This keeps the ruling's intent — no apt activity concurrent with a harness run — and restores
current lists. Cost: ~12 s per revert (measured 12.2 s; revert 39 s total). REVERT_METRICS gains apt_update_s.
Any verdict recorded on the frozen lists before this fix (caching_nameserver) is superseded by a re-review.

## 2026-10-27 — HQ rulings at sprint checkpoint 1 (re-review sweep: 8 PASS / 23 FAIL)
1. Sweep accepted: 8 of the 31 git-done classes are verified. Git stays the fact for DONE. A DERIVED state
   is added (status.py, from the persisted reviewer-v2 verdicts in `.codex_state/reviews/`): "verified
   (gate v2)" = the latest verdict for the class's current effective commit is PASS; otherwise "done (gate
   v1, reconciliation pending)". A class returns to verified only through a reviewer-v2 PASS recorded
   after its fix commit.
   - Groups A (records only, 3) and B (comments/format, 13): advisor-direct, as a RECORDED ONE-OFF
     EXCEPTION to ruling 3 (2026-10-26), valid for gate-v1 reconciliation only. Method for B: the baseline
     file + the re-applied syntax hunks + a 2-line header; the diff vs the baseline shows only those;
     reviewer-v2 PASS per class; one commit per class. Done after 3.2 and 3.3 exist.
   - C, D, E: the normal loop after the sprint, at the head of the queue in this order: rsyslog_base →
     rsyslog_client → docker_container → filesystem_yum. firewall and sysmon_puppet_cert_status sink with
     the zero-declaration classes. E's plan fix (backup_rsnapshot_pre required_base) goes into 4.1.
2. Unguarded execs at the baseline (user_base, user_lock, linux_policies_user, mysql_server): option (a),
   per class, NO exemption list. The added guard must test the command's post-condition so the effect is
   preserved. One escalation per class (command, guard, why the effect is unchanged), marker per 3,
   batched for the CTO. user_base's escalation is written first and HQ confirms that one before it is
   applied; mysql_server: record whether upstream 874f854 already guards it.
3. Marker approved and generalised: `[from: <ref>; upstream defect fixed: <short>]`, used for
   puppet_boot_run, the exec guards, fqdn_rand_uuid and filesystem_sec. The generator and status.py parse
   it (with a test). Word order on the tracker line stays the CLAUDE.md loop-invariant form
   `<class> Done [...]`; the parser also accepts the historical `Done <class> [...]` lines.
4. Master snapshot (puppet-lint gem installed 2026-10-26) deferred to checkpoint 2, after the
   master-fixtures script has run; Salatiel takes it then.
5. Old node snapshot P8NODE_BASELINE_GREEN kept through checkpoint 2.
6. filesystem_sec: fixed locally with the minimal change (assign into a new variable instead of
   reassigning the parameter), marker per 3; on the CTO upstream-defect list with the note that the
   production nodes must all pass the parameter explicitly (the default branch never compiled on Puppet 8).
7. Reviewer: the 1.5 sweep ran general-purpose subagents carrying reviewer.md verbatim (this session had
   loaded the pre-v2 agent definition); a fresh session uses `subagent_type: reviewer`.
8. Evidence that gate v2 catches ENGINE errors, not only class errors: the 1.5 sweep found two defects in
   the engine itself, both fixed in place and the affected classes re-reviewed — (a) the v2 node snapshot
   froze apt lists at 2026-02-17 because ruling 5 disabled the apt timers, so `Package[bind]` 404'd
   (revert-first made it visible; fix 6947198, revert now refreshes lists); (b) the run-1 count and run-2
   regex missed puppetlabs-firewall 8 Resource-API creations (`defined 'ensure' as 'present'`), so a
   created rule showed 0 events (fix 90a8a44; the exit-0 rule still protected run 2).
Sequence from here: 3.2 → 3.3 → A/B reconciliation → 3.4 → 3.5 → 4.1–4.3 (E plan fix, exec-guard and
filesystem_sec escalations, master-fixtures script) → checkpoint 2.

## 2026-10-27 — Step 3.3: advisor-direct path mechanics; re-migration is a plain `P8: migrate` commit
1. Path decision is a tool, not a judgement: `classify_path.py <class>` → unchanged-validated (identical to
   the baseline + pregate CLEAN + compile-only OK; advisor-direct, no Codex), syntax-work (Codex),
   baseline-sync first (hazard 8), context-gap (a Hiera key, a mandatory-parameter fixture or a
   required_base the compile lacks: block category 3 resolutions), or ERROR (decide nothing). An
   inherited (also-in-baseline) pregate finding counts as a finding: such a class is syntax-work, because
   ruling 3 requires pregate to pass. An advisor-direct class that is not GREEN falls back to Codex.
2. A re-migration of a done class (the A/B reconciliation now; C/D later) is a new `P8: migrate` commit made
   by record_green.sh, not a new commit type: the subject is identical on every path, so the reviewer
   cannot tell who or which path produced it (ruling 3, P1). review_class treats a class with an earlier
   migrate commit as a re-migration: pre-existing drift is what the commit replaces (provenance ok, with
   the replaced paths in the detail) and DIFF A (final vs baseline) carries the whole claim. A first
   migration still fails provenance on pre-existing drift. Effective commit = the newest migrate commit
   (generator, status.py "verified", reviewer — unchanged code paths).
3. The tracker marker of a re-migrated class becomes `[from: release-0.9.10]`: the content is now baseline +
   reviewed translations. This is a new migration, not the retro-annotation CLAUDE.md forbids.

## 2026-10-27 — A/B reconciliation done (HQ ck1 ruling 1): 16/16 reviewer-v2 PASS; one routing correction
All 16 group-A/B classes were re-migrated advisor-direct (baseline text + attribute-rename hunks + 2-line
header → revert-first harness GREEN → record_green.sh → reviewer v2, `--fresh`): every one PASS. status.py:
24 verified (gate v2) / 7 done (gate v1, reconciliation pending) = groups C, D, E, left for the normal loop.
Correction to the reconciliation list (2026-10-27): firewall_addon_xrdp's `state => ['ESTABLISHED']` →
`'ESTABLISHED'` is NOT noise to revert. With puppetlabs-firewall 8.3.0 the one-element array is re-applied on
every run (`state changed 'ESTABLISHED' to ['ESTABLISHED'] (corrective)`, gate v2 RED): the provider parses a
one-element state back as a String. The string form produces the same `--state ESTABLISHED` rule, so it is
an API translation and was kept, with the reason in the header; the reviewer verified it in the module source.
Translation choice for firewall attributes: rename only, values kept (`provider => 'ip6tables'` →
`protocol => 'ip6tables'`, `action => drop` → `jump => drop`; the type accepts both and upcases jump values).
One reviewer FAIL on the way (firewall_addon_caching_nameserver header named `puppetlabs-firewall` without a
version) → fixed via `record_green.sh --fix`, re-reviewed PASS; record_green's header-check now refuses it (b15d041).
dns_client's params fixture was reordered (8.8.8.8, 1.1.1.1) so run 1 is not a no-op; nginx_default_removal's
empty run 1 was justified by the reviewer (nginx absent on the baseline node).

## 2026-10-27 — Step 3.4: per-attempt metrics (ruling 5 / F.9)
Events, not hand-written records: every tool appends what it measured to the untracked
`.codex_state/logs/metrics/events.jsonl` — classify_path (path), the harness on EVERY exit (rc, revert-first,
run-1 events, duration, die reason, and per agent run the node's last_run_summary: transaction_uuid,
resources total/changed/failed, time), revert (REVERT_METRICS), the wrapper (codex rc/seconds/timeout and token
usage from ~/.codex/sessions rollouts — tokens, tool calls, model, effort, cli version; account ids are never
copied), record_green (commits) and review_class verdict (verdict, failed checks, check seconds).
`metrics.py close <class> --outcome ...` folds the events since the class's previous close into ONE record in
the TRACKED `.codex_state/runs/metrics.jsonl` (append-only history, P2-exempt) and commits it alone as
`P8: record metrics after <class>` (refused if anything else is dirty). Reviewer exemption: reviewer.md forbids
`.codex_state/runs/` (the records name the generation path, i.e. who authored) and states that metrics
commits are never part of a review; the reviewer tool already ignores `P8: record` subjects. Two token figures
are kept: `codex_tokens` (Codex's total_tokens, which recounts cached input every turn) and
`codex_tokens_uncached` (fresh input + output); the diagnosis's "68 k/class" must be re-derived against one of
them, stated. Metrics never change a verdict: every emitter is best-effort.

## 2026-10-27 — Step 3.5: single sources for the engine's instructions
1. Hazard checklist: ONE file, `.codex_state/rules/hazards.md` (13 items: CLAUDE.md's 8 + diagnosis G items
   9–13 approved by ruling 12, with the runbook §5 lessons folded in). CLAUDE.md @-imports it, the skill
   points to it, the wrapper appends it to every Codex prompt. Edit only there.
2. Runbook: tracked at `.codex_state/rules/CODEX_RUNBOOK.md` (moved from ~/.config/infra_populi/; the old file is
   renamed `CODEX_RUNBOOK.md.moved-to-repo-2026-10-27`, not deleted). §2 now records through record_green.sh
   only; §5 defers to the hazard file; the wrapper's own recording override is removed (no second copy).
3. Puppetfile export on every change: record_green.sh refuses while `export_puppetfile.py --verify` finds the
   master's Puppetfile different from `.codex_state/lab/Puppetfile`; an updated export may ride in the class's
   migrate commit (record_green allows it; the reviewer's scope check counts it as a state file).
4. Generated "current rules" digest: `.codex_state/rules/CURRENT_RULES.md`, derived by
   `gen_rules_digest.py` (rule lines per entry, newest first; SUPERSEDED marks from `supersedes <date>
   "<title>"` references; unmatched references listed). The engine pre-commit hook refuses a staged
   DESIGN_DECISIONS.md whose digest is not regenerated and staged with it. Read it as an index into this log,
   never instead of it.

## 2026-10-27 — Step 4.1b: Forge pins applied (non-openvox-only) and the htpasswd provider diff (ruling 7)
Applied to the lab master's Puppetfile (r10k; `puppet module list` before/after: +4 modules, 0 invalid; r10k
purged puppet_infrastructure as always, redeployed by the next harness run; `puppet generate types` +
puppetserver restart for the custom types): puppetlabs-mysql 17.3.0 (puppet >=8 <10), thias-sysctl 1.0.8
(ruling 7; puppet <9), citrin-htpasswd 1.0.3 (ruling 7), puppet-openvpn 11.0.1 (declares puppet AND openvox
>=7 <9; 12.0.0 is the openvox-only line). Repo export updated (22 pins).
htpasswd provider diff, as ruling 7 requires (leinaddm-htpasswd 0.0.3 vs citrin-htpasswd 1.0.3, Forge tarballs
sha256 c492bb7e… / fbd0b3c5…): providers htpasswd/parsed.rb and htgroup/parsed.rb BYTE-IDENTICAL; types
identical once whitespace is ignored except the Puppet-3 wrapper `module Puppet; newtype(...)` →
`Puppet::Type.newtype(...)` (the very API Puppet 8 removed); functions ht_crypt/ht_md5/ht_sha1 moved from 3.x
`Puppet::Parser::Functions` to 4.x `htpasswd::ht_*` with the same algorithms (user_sysmon calls none of them).
Result: identical semantics for user_sysmon → module swap, advisor tier. Caveat recorded: citrin's metadata
declares puppet >=5.5.10 <8.0.0 (informational; the types load: user_sysmon COMPILE OK on OpenVox 8.24.2).
sysctl: thias-sysctl 1.0.8 loads on OpenVox 8 (firewall_addon_openvpn_server compiles with
Sysctl[net.ipv4.ip_forward] once its 3 `action` are probed as `jump`) → ruling 7's augeasproviders fallback is
not triggered. blocked.txt: firewall_addon_openvpn_server UNBLOCKED (remaining work is syntax); user_sysmon
re-categorized 1 → 5 (needs a Naemon/Thruk monitoring-server node; module blocker resolved).
Prepared, not applied (ruling 9): `.codex_state/lab/Puppetfile.openvox-only.prepared` (puppet-nginx 8.4.0,
puppet-letsencrypt 13.4.0 + puppet-epel 6.0.0, puppet-openvpn 12.0.0, rabbitmq/gitlab outside the 87; saz-ssh and
saz-sudo held; saz-resolv_conf 8.0.1 already in the lab is openvox-only — flagged). ntp: no pin until production's
ntp module is read (escalation, 4.2).

## 2026-10-27 — Step 4.1c: baseline-syncs (C3) and the three imports (ruling 8): 90-class universe
Baseline-synced verbatim to release-0.9.10 (cf477c6), one `P8: baseline-sync` commit each, none shares a drifted
template/file with a done class (`git grep` in the baseline): filesystem_apt (+files/apt/apt-update-kernel.sh),
letsencrypt_base, puppet_boot_run (+files/etc/puppet_boot_run.sh), rsyslog_server (+4 templates; ruling 1:
migrates from 0.9.10 directly), user_kde_lock_screen, user_desktop, user_desktop_sudoer.
NOT synced: node_base_desktop — its baseline passes parameters to rsyslog_client, whose local copy is the
pre-baseline (group D) version, i.e. "the baseline needs newer dep content" (hazard 8) → escalation (4.2).
Imported from the baseline as baseline-syncs: gnome_lock_screen, firewall_ipv6_drop_policy_desktop,
rsyslog_apparmor_exception, each with an advisor-scored plan row (rsyslog_apparmor_exception:
required_base=rsyslog_base for Service['rsyslog']) and a pending tracker line → 90 classes. Composite
meaningful_desktop now compiles its full 7-class direct closure (same expected first error, now from
firewall_ipv6_drop_policy_desktop.pp:13).

## 2026-10-27 — Step 4.1d: lab-master fixture state (ruling 6) built by master_fixtures.sh
`.codex_state/tools/master_fixtures.sh all` (idempotent; second run = OK x4) on puppet8master:
- extra_files: `[extra_files]` mount in /etc/puppetlabs/puppet/fileserver.conf → /etc/puppetlabs/code/
  p8test_extra_files (root:puppet 0750); puppetserver restarted once (mount change only). The default auth.conf
  already allows /puppet/v3/file_content to every node.
- pki: a self-signed "p8test throwaway CA" (O = "p8test lab fixture (THROWAWAY, not a real CA)") and one server
  cert CN p8test.invalid (SANs *.p8test.invalid, star.example.com), 10 years; 2048-bit DH; laid out under every
  name the manifests source (ssl/<prefix>.{crt,key,pem,intermediate.crt}, -key.pem, -chain.pem for prefixes
  p8test and star.example.com — the lab Hiera's example hashman::sslprefix; ssl/db/*; openvpn/keys/*). 19 files,
  keys 0640 root:puppet. The CA key never leaves the temp dir and is discarded. Marker records the cert sha256.
- hiera: data/p8test_fixtures.yaml (sysmon::basedir/address/backdir/backdays,
  puppet8node::postfix_smtp_node::relayuser/relaypass — fake values) as a hierarchy level AFTER Common, so it
  can never override an existing lab key. hiera.yaml was rewritten by Ruby YAML (backup kept beside it).
Verified on the real lab: sysmon_backup COMPILE OK (was: lookup of sysmon::basedir failed); engine fixture
`extra_files_probe` (revert-first) fetched puppet:///extra_files/ssl/p8test.crt to the node and went GREEN.
Nothing is production-derived. The master now differs from its last snapshot (puppet-lint gem, 4 Forge modules,
these fixtures): HQ takes the new master snapshot at checkpoint 2 (ck1 ruling 4).

## 2026-10-27 — Step 4.2a: upstream-defect registry; the reviewer may read it
`.codex_state/rules/upstream_defects.md` lists every class whose marker is (or will be) `upstream defect fixed`:
defect, the RULED change (or none yet), status (`ruled` / `applied <commit>` / `pending HQ`), CTO note. It is a
rules file, not an escalation: the reviewer may read it (reviewer.md), review_class prints the ruled change with
the diffs, and `records` fails a defect marker whose class has no `ruled`/`applied` entry. With such a marker
DIFF A may contain exactly the ruled change in addition to ordinary translations. It doubles as the CTO batch.
Entries now: filesystem_sec (ruled, ck1 ruling 6), puppet_boot_run (ruled, ruling 8), openvpn_nm_connection
(ruled per ck1 ruling 3: fqdn_rand_uuid → stdlib fqdn_uuid; class still blocked otherwise), user_base (pending HQ —
its escalation is written last in 4.x and HQ confirms it), user_lock / linux_policies_user / mysql_server
(pending; ruling 2's mysql question answered: upstream 874f854 does NOT guard the cert-generation exec, it moves it
verbatim into the new mariadb_server.pp:99-102).

## 2026-10-27 — Step 4.3: fleet-weighted order; HQ re-migration queue in the order file
Pending order = dependencies first (unchanged topological rule), then `prod` DESCENDING, then cx/dep/p8/name.
`prod` is read live from `.codex_state/diagnosis/fleet_class_usage.md` (production node statements, composites
propagated) — the generator's single source, NOT a copied plan column (P2). Result, as ruling 9 asks without any
cluster list: the node_base closure first (packages_base 59, firewall_secure 59, puppet_boot_run, filesystem_apt,
sysmon_base, firewall_secure_extra, then node_base itself), then the ssl/nginx stack (ssl_base 38 …
nginx_frontend 24), prod-0 classes last. The HQ ck1 re-migration order lives in
`.codex_state/rules/remigration_order.txt` (`first` = ahead of the pending queue: rsyslog_base → rsyslog_client →
docker_container → filesystem_yum → backup_rsnapshot_pre; `sink` = after it: firewall,
sysmon_puppet_cert_status); the order file renders the still-unverified ones and `Next class` follows that order.
The "verified (gate v2)" derivation moved into the generator; status.py uses it (one implementation).

## 2026-10-27 — HQ rulings: production facts settled (no CTO tier for this phase)
1. STANDING FACT: the runtime is OpenVox, settled since the project started. "Runtime decision" is deleted from
   every open list. SUPERSEDES ruling 9's "8 openvox-only pins prepared but unapplied until the runtime answer"
   (2026-10-26 "HQ rulings on the engine diagnosis") and the hold in "Step 4.1b": the prepared openvox-only pins are
   applied now (inside declared ranges; generate types + puppetserver restart; clean `puppet module list`). The
   nginx/ssl stack is unparked.
2. Upstream defects are fixed in infra_populi only, with the `upstream defect fixed` marker; the running list lives
   in `.codex_state/upstream_defects.md` for reference; no upstream patches and no escalation of these to anyone.
   SUPERSEDES "batched for the CTO" in ruling 8 (puppet_boot_run), ck1 rulings 2 and 6, and "Step 4.2a" (the registry
   moves from .codex_state/rules/ to that path and loses its CTO wording). Reading (advisor, flagged at checkpoint 2):
   this also confirms the proposed user_base post-condition guard (escalations/user_base-exec-guard.md) and makes
   option A of escalations/openvpn_server-upstream-defects.md the rule (drop our duplicate service; marker).
3. All production nodes are agent-mode; every catalog comes from the master. firewall_addon_hosting: find what
   permits outbound to the master on 8140 (with firewall_secure); if present the lab failure was fixture/ordering —
   rebuild the test; if absent add the OUTPUT accept for the master on 8140 with the marker. Unblock either way.
4. mysql: Issue #122 is merged at upstream 874f854 and is the code that will run. mysql_server migrates from
   874f854; mariadb_server and mysql_db are imported from it; each is annotated `[from: 874f854]` as a per-class
   baseline exception (like docker_container's `[from: release-0.9.8]`). SUPERSEDES ruling 1's "the mysql rewrite
   stays out until released (CTO decision 5)" and 4.2a's remark on 874f854. Universe: 92 classes.
5. Migrate everything: no retire list. Fleet usage is a priority ORDER, never a filter — zero-declaration classes stay
   in the queue, sorted last. hello_world_flask* stays. SUPERSEDES ruling 9's "zero-declaration classes sink until the
   CTO rules" (they sink, permanently in the queue) and every "retire/park" option (diagnosis C14).
6. RHEL: due diligence applies; extra_packages_el and the RedHat branches stay in scope. Post-sprint infrastructure:
   revive the existing RHEL9 VM (re-base, install OpenVox, check `subscription-manager status`) alongside the EL9 container.
7. Sysmon: the monitoring side lives in another repository. user_sysmon and the sysmon_* checks get synthetic node
   fixtures for the paths/users the classes expect, labelled mock-apply where the real service is absent — the same
   rule as user_samba (ruling 7, 2026-10-26).
8. The "Decisions needed" and "CTO" sections of the diagnosis and the checkpoint files are rewritten to reflect 1–7.

## 2026-10-27 — Ruling 7 mechanics: node fixtures and the mock-apply label
New optional plan column `node_fixture` = a synthetic node fixture manifest
`.codex_state/tools/tests/fixtures/node/<name>.pp` that the harness renders into the managed block BEFORE the class
(the generator fails if the file is missing; coverage still counts only class-tagged resources). A GREEN with a
node fixture is MOCK-APPLY: syntax and idempotency proven, behaviour not. The tracker marker gains
`; mock-apply: <short>` (parser/generator/status/records), written by `record_green.sh --mock-apply`, which is
REQUIRED exactly when the plan names a node_fixture; review_class `records` fails a mismatch either way and shows
the label to the reviewer (reviewer.md). Fixtures: `sysmon_server` (naemon system user/group, /etc/thruk,
/etc/naemon/conf.d/contacts — user_sysmon) and `samba_dc_standin` (stateful stand-ins for pdbedit, ldbsearch,
create-user.pl, set-user-samba-hash.sh keeping a fake store, so user_samba's unless-guards see its own effect;
the 2026-10-26 ruling-7 stand-in). The sysmon_* check classes need no fixture: they are node-side NRPE checks whose
prerequisites (nagios plugins, lib64 symlink) come from packages_base / filesystem_lib64.
REAL LAB: user_sysmon revert-first GREEN with its fixture (Htpasswd + contact file created, run 2 clean);
user_samba GREEN with its stand-in once a throwaway probe added the repository-standard
`$localdir = lookup('filesystem::localdir')` (hazard 7; the real fix is the class's own syntax work; probe
reverted, its GREEN stamp deleted). blocked.txt: user_sysmon and user_samba UNBLOCKED (3 remain:
extra_packages_el — RHEL node, post-sprint; mount_shares_desktop — desktop fixture; openvpn_nm_connection —
NetworkManager).

## 2026-10-27 — HQ rulings at sprint checkpoint 2
1. Confirmed: user_base's post-condition guard (HQ confirmed 06:10; the determinism check — the command is a pure
   decode of the .b64 file — is recorded in escalations/user_base-exec-guard.md) and openvpn_server option A (drop our
   duplicate service, notify the module's resource).
2. linux_policies_user: prefer a true post-condition guard if the policy lines are queryable state
   (dconf/gsettings/xdg): guard = "any current value differs from desired". If the lines are opaque, a login-session
   guard is acceptable only if the exec cannot take effect without a session anyway — then say so in the marker. One
   attempt; if neither holds, block it as "intentionally non-idempotent; needs a logged-in desktop fixture (Phase 3)".
3. rabbitmq and gitlab (and therefore puppet-archive, pulled in only for rabbitmq) are REMOVED from the lab Puppetfile
   (r10k --force, clean module list): meaningful_puppet's dependencies, not infra_populi's, and extra modules add noise
   to the reviewer's header oracle. Their pins are kept in a note for the company-layer upgrade.
   SUPERSEDES the rabbitmq/gitlab part of "HQ rulings: production facts settled" ruling 1 as applied in pf1.
4. saz-ssh 13.1.0 and saz-sudo 9.0.2 are held for Phase 1; upgraded at Phase 6 module alignment, with re-review.
5. ntp/chrony from production (`puppet module list` on the production master, 2026-10-27): puppetlabs-ntp v8.5.0 and
   puppet-chrony v1.0.0. Pin the OpenVox-compatible release of each inside its declared range; confirm from node_base.pp
   which one is included under which condition; record the parameter renames between production's versions and the
   pins for the parameters node_base passes.
6. /migrate-next resumes after the master snapshot and the old node snapshot deletion. First batch: `/migrate-next 7`
   (the gate-v1 re-migrations, rsyslog_base first), then stop with a batch report built from the per-attempt metrics
   (wall per class, Codex runs per green, reviewer verdicts, reverts) — the engine's first measurement.

## 2026-10-27 — Checkpoint-2 rulings 3–5 applied on the lab master
- Removed rabbitmq 15.0.0, gitlab 11.1.0 and archive 8.1.0 (r10k --force; their 12 generated pcore types removed from
  .resource_types/ so nothing stale remains); pins kept as a note in .codex_state/lab/Puppetfile.openvox-only.prepared.
- ntp/chrony (production: puppetlabs-ntp 8.5.0, puppet-chrony 1.0.0): pinned the newest releases declaring a range that
  includes the lab runtime — puppetlabs-ntp 11.2.0 (puppet >=8 <10; stdlib >=4.13.1 <11) and puppet-chrony 6.0.0
  (openvox >=8.19 <10; stdlib >=4.25.1 <11); lab stdlib 9.7.0 is inside both. node_base.pp:134-160: chrony on
  `os.family == RedHat`, ntp on every other family; with `$custom_ntp` it passes only `servers => $ntp_servers`, else a
  plain include. Parameter diff, production → pin (from the Forge tarballs): ntp `servers` is Array[String] in 8.5.0
  and 11.2.0 with identical Debian defaults; the class lost `config_template` and gained `logfile_user`/`logfile_group`
  — node_base passes neither. chrony `servers` is `Chrony::Servers` (Hash[Host, Optional[Array]] | Array[Host]) with the
  same default pool hash in 1.0.0 and 6.0.0; 6.0.0's Debian.yaml sets `servers: {}`, which never applies (node_base uses
  chrony only on RedHat). → no rename affects node_base. Module list: 0 invalid (only the known Windows-only docker
  warnings). Composite node_base_debian now compiles past ntp; its expected first error is firewall_secure's pending
  `action` syntax (composites.txt updated).
- saz-ssh 13.1.0 / saz-sudo 9.0.2 held for Phase 1 (ruling 4).
- Observed: the old node snapshot P8NODE_BASELINE_GREEN is gone from the node's snapshot tree (v2 now hangs under
  "Codex Setup Done"); the node was found powered off and was brought back by revert_node.sh.

## 2026-10-27 — Master snapshot P8MASTER_BASELINE_GREEN_v3
HQ took the master snapshot `P8MASTER_BASELINE_GREEN_v3` OFFLINE after commit 0a71977 (master state: puppet-lint 4.3.0,
the 27 Puppetfile pins of .codex_state/lab/Puppetfile, regenerated .resource_types/, the master_fixtures.sh state:
[extra_files] mount + p8test PKI + Hiera fixture level). The previous master snapshot v2 was deleted by HQ. The old node
snapshot P8NODE_BASELINE_GREEN was deleted by HQ; the node baseline is P8NODE_BASELINE_GREEN_v2. The master is still
never restored by the engine (standing rule); the snapshot is HQ's recovery point.
Next: `/migrate-next 7` (the gate-v1 re-migrations), then snapshot_master.sh + read-only VBoxManage permissions
(HQ VM-operations ruling) in one engine commit.

## 2026-10-27 — HQ VM-operations ruling: snapshot_master.sh and read-only VBoxManage permissions
`.codex_state/tools/snapshot_master.sh <P8MASTER_NAME> [--dry-run]` is the only master shutdown the engine performs:
take-only (never restore/delete/edit), offline via ACPI with a timeout (on timeout it refuses and leaves the master
running — never a hard poweroff), refused while any engine run is live (test_class.sh, codex_migrate_class/codex
exec, review_class check, composite_compile, record_green, revert_node), while the master is not running, when the
name exists or is malformed, when the worktree is dirty, or when the master Puppetfile differs from the repo export.
The description is generated: repo HEAD, pinned baseline, Puppetfile sha256, `puppet module list` sha256 + count.
After the take it starts the master headless and verifies SSH, puppetserver active and 8140 status running; name +
UUID are appended to `.codex_state/lab/master_snapshots.jsonl` (commit it). `.claude/settings.json`: the blanket
`VBoxManage *` allow is replaced by read-only `list`, `showvminfo` and `snapshot <vm> list` on both VMs plus the
script; denied on both VMs: snapshot restore/restorecurrent/delete/edit, unregistervm, modifyvm; on the master also
direct snapshot take, controlvm poweroff and acpipowerbutton (shutdown only through the script). revert_node.sh keeps
its own node operations (script internals are not Bash-tool commands). CLAUDE.md "Node lifecycle" updated.
