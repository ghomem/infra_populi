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

## 2026-11-10 — HQ rulings before batch 2 (1/3): per-class expected_run2_events
Ruling: a plan column `expected_run2_events` (`;`-separated `Type[title]`) names the ONLY resources allowed to report
events on harness run 2, for a class whose upstream design re-runs something every agent run. Not a general
exemption: every entry needs a class-header justification line `# Expected run-2 events: <refs> — <why>` (enforced by
record_green's header-check and review_class `records`, which also rejects a justification line without a plan
entry) and the reviewer verifies the justification independently against the code/module (reviewer.md).
Mechanics: the harness unions the entries of the target and its expanded required_base (a base's justified events
travel with it); run 2 is GREEN only if every event line belongs to one of those resources; exit 2 is accepted only
when caused solely by expected events; any other exit stays RED; it prints `RUN2_EXPECTED_EVENTS: N from <refs>`.
First use: packages_base `Exec[apt_update]` — packages_base.pp:19 `class { 'apt': update => { frequency =>
'always' } }`, the comment at :11 states the intent ("make sure apt-get update ... runs on each puppet run"), and
puppetlabs-apt 11.3.2 update.pp:13-15/89-93 turns 'always' into `refreshonly => false` (module-documented).
Phase 5 question for HQ (recorded, not acted on): `frequency => 'daily'` instead of 'always'.

## 2026-11-10 — HQ rulings before batch 2 (2/3): SSH ControlMaster; firewall_secure fixture
`.codex_state/tools/sshmux/ssh` adds `ControlMaster=auto`, `ControlPath=~/.ssh/p8-cm/%C`, `ControlPersist=300` and execs
the next ssh on PATH; test_class.sh and revert_node.sh put it first on PATH (so `timeout … ssh` and `rsync -e ssh` are
multiplexed; the reviewer is covered because review_class runs the harness). revert_node.sh sends `ssh -O exit` to the
node before the hard poweroff so no stale control socket outlives a revert. Real lab: revert-first fixture run GREEN
with live masters for node and master. firewall_secure's fixture `acl` = the harness SSH source as the node sees it
(192.168.77.203 via `$SSH_CLIENT`), so rule 100 accepts the harness before the 15/min NEW-connection limit; that
address is DHCP-assigned — re-checked before every dispatch (hazards.md item 12). firewall_secure_extra: if
xtables-addons/geoip cannot be installed on the node → escalate and continue (ruling).

## 2026-11-10 — HQ rulings before batch 2 (3/3): plan edits are the advisor's; hazard 14
Codex's plan commit 7bc4be6 (firewall required_external=firewall) stands. Runbook §2b: plan columns are advisor
authority; Codex reports a missing prerequisite as one structured line
`MISSING_PREREQUISITE: <column>=<value> — <evidence>` and stops; the advisor verifies, commits `plan(<class>)` and
dispatches again (skill step 6b; it is that class's second Codex run, with the reason in the metrics note).
Hazard 14 (hazards.md, mechanised in pregate as `hazard14-module-base`): a class using a Puppetfile module's
defines or native types (inventory now maps each type to its module and env/vendored) or `Exec['apt_update']`
without declaring the module's base class and without plan required_external for it. classify_path routes a class
whose ONLY finding is hazard 14 to context-gap (a plan fix), not to Codex. Real lab: flags firewall_secure (and,
informationally, the verified firewall addons, which went GREEN without Class['firewall']); clean for
sysmon_puppet_cert_status, nginx_proxy_smtp_auth_ppa, packages_base.

## 2026-11-11 — HQ rulings before batch 3 (5): the desktop regex node weighs 20 machines
`prod` (secondary sort key after dependencies) is now production MACHINES = servers + 20 × desktop statements
(fleet_class_usage.md columns; the desktops/ regex node covers 20 laptops per the production document). firewall_secure
78, gnome_lock_screen 20, openvpn_server 3: the desktop closure sorts above the three-node tier (dependencies still first).

## 2026-11-11 — HQ rulings before batch 3 (1, 6): metrics phases; expected run-2 events stated explicitly
Every event now carries a duration (pregate, path, harness, codex, record, revert; review = mechanical check start →
verdict), so `metrics.py close` stores `phases`: wall = dispatch (first harness/Codex/revert start) → verdict (last
review end); within it every second goes to the highest-priority covering phase (review > codex > record > harness),
the rest is `wait`; prep (first event → dispatch, incl. classification and pregate before dispatch) and pregate_s
are reported separately. A harness run inside a review or a Codex run counts as that phase (no double counting).
The harness records where each expected run-2 ref comes from — the target's own plan entry or inherited via an
expanded required_base class — prints `[own: …; inherited: <ref> via <class>]` and puts it in the harness event; the
run record keeps it (`run2_expected`) and `metrics.py batch-report <classes>` renders the batch table with phases
and the run-2 expectations spelled out. Batch-1/2 records predate this and show no phases.

## 2026-11-11 — HQ rulings before batch 3 (2): authority enforcement under a Codex run marker
`.codex_state/rules/advisor_only.txt` (single source, globs): migration_plan, blocked.txt, DESIGN_DECISIONS,
upstream_defects, baseline.env, rules/* (runbook, hazards, digest, exceptions, remigration order, this list), tools/*
(engine code incl. compile/composites.txt), escalations/*, diagnosis/*, sprint/*, reviews/*, runs/*, .claude/*,
CLAUDE.md. The wrapper exports CODEX_RUN=1 around `codex exec`; the engine pre-commit hook refuses any staged
advisor-only path under it. Because `--no-verify` bypasses hooks, the wrapper also audits after the run: every commit
since the run started and every advisor-only file whose content changed during the run (files already dirty before
the run are compared by blob hash, so the advisor's own work in progress is not flagged) → `AUTHORITY_VIOLATION` on
stderr and exit 5. blocked.txt is now advisor-only: the runbook (§1, §4) has Codex report `BLOCKED: category <N> —
…` + evidence and stop; the advisor writes the entry (SKILL step 6). record_green's commits (class files, tracker,
order file, Puppetfile export) are outside the list. The wrapper derives its repo from its own location.

## 2026-11-11 — HQ rulings before batch 3 (4): dynamic prerequisite probe in pregate
`node_inventory.py --refresh` reverts the node and records every path of the clean P8NODE_BASELINE_GREEN_v2 root
filesystem (find -xdev; 146,292 paths, 50 s) into an untracked cache; pregate answers "exists on the clean reverted
node?" from it (one revert per snapshot, not per class). pregate extracts the absolute paths a class consumes —
parents of its file resources (literal, interpolated, $var and array titles), link targets, local sources, exec/cron
command paths — resolving `lookup()` variables against the master's Hiera (sent in the same ssh round trip), and
reports `hazard4-prereq` for each missing path that no class of the required_base closure declares and that no
provider listed in `.codex_state/rules/provided_paths.txt` (advisor-maintained, evidence per line; first entry
/etc/nginx ← class nginx) creates. classify_path routes probe-only findings to context-gap. Validation: the sysmon_base
case is flagged with filesystem_lib64 removed from the closure and clears with it; 0 findings over all 38 done classes
(no false positives); batch-3 pre-scan flags nginx_frontend (`/opt/puppet-infrastructure/bin`, missing
required_base=filesystem_base — a real catch).

## 2026-11-11 — HQ rulings before batch 3 (3): the pre-commit hook runs the tests
No commit lands with a failing test. The engine pre-commit hook runs the fast subset on every commit
(`pytest -m "not slow and not repo_state"`, 139 tests, ~7 s) and the full suite when a batch report
(`.codex_state/escalations/batch-*.md`) is staged; a failure rejects the commit. `slow` = clone and stub-lab
harness tests (6 files); `repo_state` = the live tracker-vs-git consistency test, which is inconsistent by design
while record_green's own commit is being made. Codex commits through record_green go through the same gate.

## 2026-11-10 — batch 3: run-2 report stage; glob refs; runbook minimal-change rule
1. Gate v2 gains a REPORT stage. A resource that changes below the notice log level (nginx_frontend_domain's baseline
   `notify { "Generated Upstream members ...": loglevel => 'debug' }`) makes run 2 exit 2 with no console line, so the
   console filter could neither excuse it nor name it (Codex run 1 BLOCKED cat 3, correctly). When run 2 exits 2 and the
   console shows nothing unexpected, test_class.sh reads the run's `last_run_report.yaml` with the node's own Puppet
   ruby and lists changed resources that have no console event; each must match the plan's expected_run2_events or the
   run is RED. An unreadable report fails closed.
2. expected_run2_events refs may contain `*` (any text) for titles built from the define title or params; everything
   else matches literally. First user: `Notify[Generated Upstream members for *]` (nginx_frontend_domain; a notify
   resource changes on every run in production too, so this is the baseline's behaviour, not a migration artefact).
3. CODEX_RUNBOOK §2 step 3: change only what Puppet 8 / the gate rejects; inherited `(also in baseline)` lint is left;
   baseline comment lines are never deleted or rewritten (add a line beside a stale one); an `HQ ruling for this class`
   packet line fixes the change's shape. Evidence: run 1 also reordered parameters (parameter_order lint, baseline-
   inherited, not a compile error) and replaced the two baseline comment lines above the ruled `Integer()` change —
   both would fail review (comments_preserved). Run 1's edits were discarded; run 2 is dispatched with this runbook.
4. (same day) classify_path no longer routes a baseline-identical class to syntax-work for baseline-inherited
   `lint:parameter_order` alone (COSMETIC_INHERITED): Puppet 8 accepts the order (compile-only still decides) and §2.3
   tells Codex to leave it, so a dispatch would be empty. Other inherited lint (legacy_facts, top_scope_facts, ...) stays
   syntax-work — those are real Puppet 8 breaks. First case: nginx_frontend.

## 2026-11-10 — HQ batch-3 acceptance (1/4): a recorded GREEN must start on the latest revert
record_green.sh refuses any GREEN whose harness run did not start after the node's latest revert. Mechanism: every
successful revert_node.sh run ends by reading the node's state token — kernel boot ID (`/proc/sys/kernel/random/boot_id`)
and the sha256 of `last_run_summary.yaml` (`absent` if none) — and `records.py revert-mark` writes it as the latest revert
(`.codex_state/logs/node_revert.json`, local). Right before run 1 the harness reads the token again (`revert_node.sh
--node-state`, no VM action) and `records.py fresh-check` compares: a different boot ID = rebooted or reverted elsewhere,
a different last_run hash = an agent run in between. The verdict goes into the GREEN stamp (`revert: {fresh, boot_id |
reason}`) and is printed as `NODE_FRESH: yes|no`. record_green's `verify-fresh` requires `fresh` AND the stamp's boot ID
equal to the latest revert's, so a revert after the GREEN (e.g. a reviewer run) also voids it; a pre-rule stamp without
revert state is refused. Strict for `--fix` records too (re-run `--revert-first`; ~2 min). The harness still reports a
stale run GREEN — it is evidence, just not recordable. CODEX_RUNBOOK §2.4: after iterating on a used node, finish with
`test_class.sh --revert-first`. Evidence for the rule: firewall_ipv6_drop_policy_desktop's recorded GREEN (batch 3) was
"not reverted first". Real node token read OK (boot aa9bd922…, last_run present in the snapshot).

## 2026-11-10 — HQ batch-3 acceptance (2/4): notify events accepted; Phase 5 backlog file
`Notify[...]` expected run-2 events are accepted on the same basis as `Exec[apt_update]`: upstream behaviour that
reports a change on every agent run, allowed only through a plan expected_run2_events entry with a header
justification. The Phase 5 list now has a single source, `.codex_state/rules/phase5_backlog.md` (advisor-only via
rules/*): item 1 apt frequency 'always' → 'daily' (moved from the 2026-11-10 batch-2 entry's "Phase 5 question"),
item 2 replace notify resources with notice()/debug() calls, with every carrier found by grep (nginx_frontend_domain
:256/:262, mariadb_server :64 — pending, will need the same plan entry —, ssl_base :98 conditional).

## 2026-11-10 — HQ batch-3 acceptance (3/4): three intervention counters
Metrics records (schema 2) carry `interventions: {codex, advisor, human}` instead of one `human_interventions`; `close
--interventions codex=N,advisor=N,human=N` (a bare number is refused: say whose action it was). Each counts EPISODES
after dispatch (prep before dispatch is not one): codex = Codex stopped and handed back, repaired its environment, or
overstepped its authority; advisor = the advisor stepped in (fix after a RED or a stop, recording on Codex's behalf, a
second dispatch); human = Salatiel/HQ acted. `summary` and `batch-report` show the three. The 22 schema-1 records
(batches 1–3) are append-only; their counters come from `.codex_state/runs/interventions_backfill.jsonl`, one line per
attempt citing its basis from the record's note: zero human (HQ), codex 4 (firewall and firewall_secure: plan /
composites commits beyond authority, before the 2026-11-11 marker; nginx_frontend_domain run 1 stop;
firewall_ipv6_drop_policy_desktop's refused record), advisor 5 (filesystem_yum, packages_base, sysmon_base,
nginx_frontend_domain, firewall_ipv6_drop_policy_desktop). The schema-1 field was named human but was used for advisor
actions (packages_base, firewall_ipv6 = 1 each); both read as advisor now.

## 2026-11-10 — HQ batch-3 acceptance (4/4): skipped tests carry a reason in the report
The engine pre-commit hook runs pytest with a JUnit XML and reads each skipped test's reason from it.
- **Reasons are mandatory.** A skip without one (`@pytest.mark.skip` with no reason, i.e. "unconditional skip")
  rejects the commit.
- **Each skip is printed.** The hook prints `TESTS: skipped <module>::<test> — <reason>` for every skip.
- **Batch reports must name them.** When a batch report is staged, the full suite runs, and the report must name
  every skipped test (it then states the reason beside it). Otherwise the hook rejects the commit and prints the
  lines to add.

Today's only skips are the three opt-in LAB tests in test_compile.py ("needs puppet8master (set P8_LAB_TESTS=1)").
They run the compile filter on the real master and were run on demand today: 11/11 passed. The batch-3 report gains
a "Skipped tests" addendum, and the skill's END OF RUN step requires that section.

## 2026-11-10 — HQ batch-3 acceptance B: the Phase 3 runner
`.codex_state/tools/phase3.py` implements ruling 11 (2026-10-27): checks per class in `.codex_state/checks/<class>.yml`
(advisor-only), laptop-side Python over ssh.

1. **derived_from references the baseline.** Every check carries baseline references, each `{path, lines, text}`
   (the text must be an exact substring of those lines) or `{path, sha256}`. They resolve at the class's baseline
   commit through baseline.py, never at the local tree. The file's `baseline:` must equal `baseline.py for <class>`.
2. **Probes test the node only.** The runner has one execution path, `ssh puppet8node sudo -n bash -s`, with the
   probe on stdin and the ControlMaster shim. `validate` refuses:
   - any other lab host or address, scp/sftp/rsync, and ssh to anything but 127.0.0.1/localhost;
   - Puppet runs, service or package changes, rm/tee/chmod-style edits, and redirects into a file.
3. **Negative controls are mandatory (≥1) and must FAIL on the freshly reverted node.** An `invariant` (holds before
   and after) needs `why_invariant` and must PASS on the clean node. Any miss makes the set INVALID, and the class is
   never applied.
4. **Run order:** revert → CLEAN phase → apply with the gate-v2 harness (NODE_FRESH) → APPLIED phase. A failed
   check after apply is a FINDING (exit 1). An invalid set exits 2, an apply or environment failure 3.
5. **Output:** JSON + JUnit (suites `phase3.<class>.clean` / `.applied`) in `checks/results/<class>/<UTC>-<role>`.
   Harness metrics events go to `logs/phase3-metrics`, never into Phase 1 records.
6. **The reviewer re-runs the checks and spot-checks derivation.** It runs `run --role reviewer` and `spot` (3 random
   references printed beside the baseline lines read fresh), then records a `verdict`. PASS = both runs valid +
   identical per-check outcomes on the same check file + derivation ok. Findings do not fail a review.
7. **Authoring minutes:** each check file records its own measured wall clock (`authoring.minutes`, required).

Pilots authored and validated (backup_rsnapshot 5 checks, ssh_secure 14, nginx_static_domain 8; 59 baseline
references), not run: per HQ they run after the network change, as its canary. Report:
`escalations/phase3-pilots.md`. CLAUDE.md gains the Phase-3 section that ruling 11 asked for.

## 2026-11-10 — HQ: lab-network design approved (stop until step review)
HQ approved the host-only/static-IP design (escalations/lab-network-static.md):
- **Addresses:** 192.168.56.10 (master) / .20 (node).
- **NIC1:** stays bridged for internet. NAT is a follow-up plan, written once host-only control is proven.
- **Canary:** firewall_secure + rsyslog_client re-verification, plus the three Phase 3 pilots.
- **Added to the plan:**
  - step 0 verifies that the master certificate's SANs are name-only (read today: DNS only);
  - the `puppet8master-wifi` / `puppet8node-wifi` fallback aliases are added in step 4 and kept until both snapshots
    are refreshed and verified (step 9).

No step runs until HQ's step review returns; step 1 (`modifyvm`) is Salatiel's.

## 2026-11-10 — HQ: Phase 5 backlog item 3, dead ssh options
`Protocol 2` and `UsePrivilegeSeparation yes` in ssh_secure (local :59/:79, baseline :57/:77) are ignored by OpenSSH
≥ 7.5; the node runs 9.6p1. They go to `rules/phase5_backlog.md` as item 3 (removal). Phase 1 keeps them verbatim.

## 2026-11-10 — HQ: Phase 3 mutating probes (opt-in)
A check may change the node only if it opts in.
- **Declaration:** `mutates: <declared change>`. Its `probe` is then the action, and `effect` is a read-only probe
  that `expect` is matched against. The evidence is the effect, never the action's own output; the action's rc and
  output are recorded alongside.
- **Validation:**
  - the action keeps the host rules (no other host, nothing master-ish, no Puppet runs);
  - the effect keeps every read-only rule;
  - a mutating check must be a negative control;
  - an `effect` without `mutates` is refused.
- **Clean phase:** only the effect runs, and it must fail. The action never runs before apply, so the node the harness
  applies to stays the reverted baseline.
- **Applied phase:** read-only checks first. Mutating checks follow in file order, only if every read-only check
  passed; otherwise each one is recorded `not_run` (exit 1, JUnit skipped).
- **Never on the master:** the runner's only execution path is the node.
- **First use:** backup_rsnapshot `daily-backup-executes` runs the cron's command once and checks daily.0 for a
  byte-identical /etc/hostname.
- **Reviewer:** reviewer.md now judges the declaration against the action. 11 new runner tests.

## 2026-11-10 — HQ: fixture PKI names the fixture domain (master_fixtures.sh pki v2)
The throwaway p8test server certificate gains `DNS:p8test.example.com` and `DNS:*.p8test.example.com` (the harness
fixture domain of the nginx/ssl classes), keeping p8test.invalid, *.p8test.invalid and star.example.com.
- **How:** the pki section's marker moves to `.p8test_pki_v2`. A v1 layout is replaced as a whole (new CA, new server
  cert, same file names, CA key discarded), and the v1 marker is removed only after v2 is written.
- **Applied to the master 2026-11-10 16:21Z** (ruling-6 fixture state; nothing else touched):
  - CHANGED 19 files, `openssl verify` OK, and a second run reports OK.
  - The new server cert's sha256 is 29:34:A9:…:81:E7 (replaces 50:DF:0A:…:AC:99 of 2026-10-27).
  - The next master snapshot (network plan step 9, v4) captures it.
- **The first run exited 2 after doing all its work:** I had left a stray quote on the script's last line.
  - shellcheck never sees the REMOTE heredocs, so a new test runs `bash -n` over every remote script. It is proven to
    catch that error.
- **New pilot check:** nginx_static_domain `https-name-verifies`, a hostname-verified TLS handshake against the
  bundle's CA.

## 2026-11-10 — lab network step 4: tracked overlay setting (HQ step review C)
`.codex_state/lab/lab.env` `NODE_NET=bridged|hostonly` is read by revert_node.sh; `P8_NODE_NET` overrides it in tests
only; an unknown value fails before any VM action; an absent file means bridged.
- **`bridged`:** unchanged behaviour, proven by tests and one real revert.
- **`hostonly`:**
  1. Reach the restored v2 node over `puppet8node-wifi`.
  2. Apply the overlay: enp0s8 192.168.56.20/24 via netplan, and the hosts line for puppet8master.example.com →
     192.168.56.10.
  3. FAIL unless a fresh (`-S none`) SSH to `puppet8node` shows `$SSH_CONNECTION` 192.168.56.1 → 192.168.56.20 and the
     node resolves the master to 192.168.56.10.
  4. Run the usual checks.
  5. Mark the state token last; no agent run.

The setting flips to hostonly in step 6 with the aliases, and is removed with the overlay in step 9.

Steps executed so far (escalations/lab-network-static.md):
- step 0 PASS;
- step 1 (Salatiel: master NIC2) verified;
- step 1a (HostKeyAlias on all lab aliases, seeded from the trusted address entries; `-wifi` fallbacks; BatchMode
  connects) PASS;
- step 2 (master enp0s8 192.168.56.10 under the dead-man timer, disarmed after the path-asserted checks) PASS;
- step 3 (one-off node trial: 8140 and getent asserted over host-only, noop agent rc 0, apt over NIC1) PASS, node
  reverted.

## 2026-11-10 — lab network steps 5–7 done; host-only is the engine's path
- **Addresses:** the main aliases now resolve to 192.168.56.10 (master) and .20 (node), and lab.env is `hostonly`.
  revert_node.sh applies the v2 overlay and proves the path on every revert.
- **Params:** the harness-source ACL params are 192.168.56.1, and rsyslog_client's `target_ip` is 192.168.56.10.
- **Master:** `/etc/hosts` resolves the node to .20, and — found by the step 7 sweep — its own name to .10 (was its
  Wi-Fi .166).
- **Documents:** CLAUDE.md Facts, hazards.md item 12 and the revert_node.sh header follow.
- **Next:** the canary (step 8), then the snapshot refresh (step 9) and the Wi-Fi-off proof (step 10). The `-wifi`
  aliases stay until step 10 passes.

## 2026-11-16 — HQ: a misused `--fresh` is a usage error, not a verdict
`review_class.py check <class> --fresh` is the post-migration mode. It is valid only while the class's migrate commit
is HEAD, or followed by nothing but record_green's own record/regenerate commits (at most 3).
- **Anything else is refused before any check or harness run** (so no node revert happens) with `USAGE ERROR … Re-run
  without --fresh`, exit 2, and no draft.
- **No verdict from an older draft:** a `<class>.refused` marker makes `verdict` refuse until a new valid `check`
  writes a newer draft.
- **reviewer.md:** on a USAGE ERROR, record no verdict and report the line.
- **Cause:** the 2026-11-10 canary verdict for firewall_secure (FAIL on `git` only, 27b6cdf), where the mode, not the
  class, was invalid. Proven on the real repo: `check firewall_secure --fresh` now exits 2 and the node is not
  reverted. 6 tests.

## 2026-11-16 — lab network step 9 (node): P8NODE_BASELINE_GREEN_v3 is the baseline; overlay and lab.env removed
- **The snapshot.** P8NODE_BASELINE_GREEN_v3 (UUID 00832142-4600-491e-a6a6-f11612254934) was taken offline after a
  clean poweroff from v2 plus the host-only overlay: enp0s8 192.168.56.20/24 (netplan 60-p8-hostonly.yaml) and hosts
  puppet8master.example.com → 192.168.56.10.
- **No agent run in between (HQ D).** Only non-mutating checks ran between the overlay and the poweroff (ping, path
  assert, node→master 8140, getent, default route via enp0s3), and the state token's last_run was still the snapshot's
  (a78c35bc7dc9…).
- **revert_node.sh** restores v3 and, after every restore, fails unless a fresh SSH (`-S none`) comes 192.168.56.1 →
  .20, enp0s8 holds .20/24, and the node resolves the master to .10. The overlay mode and `.codex_state/lab/lab.env`
  are gone (HQ C), and so is the tests' `P8_NODE_NET`.
- **node_inventory.py** reads the snapshot name from revert_node.sh (P2: one source); the inventory was refreshed for
  v3 (146,320 paths).
- **Verified:** two consecutive real reverts, then the `guarded_exec` fixture GREEN with NODE_FRESH yes.
- **v2 is kept** until HQ rules on deletion.

## 2026-11-16 — lab network step 9 (master): P8MASTER_BASELINE_GREEN_v4; snapshot_master.sh health check fixed
- **The snapshot.** snapshot_master.sh's first real run took P8MASTER_BASELINE_GREEN_v4 (UUID
  0d267a84-3ff8-4645-950c-6454b3b298f7). It shut the master down by ACPI in 5 s, took the snapshot offline and
  restarted the master. The description names what changed since v3 via the new `--note`: enp0s8 192.168.56.10, the
  hosts entries for the node (.20) and the master's own name (.10, the step-7 fix), and pki v2.
- **The refusal.** The script then refused at its health check: it matched `active running ` exactly (with a trailing
  space), which only a stub ending in a newline produces. The real `status/v1/simple` prints `running` with no
  newline.
- **Fix.** Whitespace-normalised comparison (also tolerating a TTY's `\r`); 5 tests with the real output shapes.
- **Record.** Because of the refusal, the record line in `.codex_state/lab/master_snapshots.jsonl` was appended after
  the fact from VBoxManage's own listing (name, UUID, description), marked `recorded: after the fact …`.
- **HQ item 6 asserts** on the restarted master, all PASS over the path-asserted helper: enp0s8 = 192.168.56.10/24;
  puppet8master.example.com → .10; puppet8node.example.com → .20; puppetserver active and 8140 running;
  node→master:8140.
- **v3 is kept** until HQ rules on deletion.

## 2026-11-16 — lab network project complete (step 10)
With the laptop's Wi-Fi off (`wlo1` down, no default route), every lab path held over host-only:
- SSH to both VMs, with the path asserted (192.168.56.1 → .10 / .20);
- node → master:8140;
- a compile on the master.

When Wi-Fi came back, the laptop's DHCP address had changed (.203 → .200). That would have broken the old
harness-source ACL fixtures, and no longer matters. The `-wifi` fallback aliases are removed (backup
`~/.ssh/config.pre-p8net-step10`).

Final lab facts:
- master 192.168.56.10 and node 192.168.56.20 on vboxnet0; laptop 192.168.56.1;
- NIC1 bridged for internet only;
- baselines P8NODE_BASELINE_GREEN_v3 / P8MASTER_BASELINE_GREEN_v4;
- v2 / v3 kept until HQ rules on deletion.

Leftover backups, kept until HQ says otherwise:
- `~/.ssh/config.pre-p8net-step{1a,6,10}` and `~/.ssh/known_hosts.pre-p8net-step1a`;
- `/etc/hosts.pre-p8net` and `/etc/hosts.pre-p8net-step7` on the master.

Next, per HQ: a separate NIC1 → NAT plan.

## 2026-11-16 — HQ: mismatch controls in Phase 3 checks
A check may carry `mismatch: {varies, probe}`: the same probe with one value deliberately wrong, judged against the
same `expect`.
- **Mandatory** where the probe hands a name, user, key, cipher or vhost to a tool and takes its verdict. Validation
  detects this: openssl s_client; curl with a Host header or `--resolve`; ssh with user@host or a
  Ciphers/KexAlgorithms/MACs/HostKeyAlgorithms/authentication option; su/runuser/`sudo -u`; mysql/psql/smbclient/
  ldapsearch with a user. Such a probe without a mismatch is refused.
- **Optional** for direct state reads.
- **When it runs:** after apply, for each passing check, and it must FAIL. If one passes, the check does not
  discriminate: the set is INVALID, exit 2, and mutating actions are not run. A failed check does not run its
  mismatch. It is never run on the clean node.
- **Reporting:** results and JUnit carry `<id>.mismatch`. The verdict's `reproduced` compares mismatch outcomes too.
  reviewer.md: a mismatch that only breaks the command is a derivation failure.
- **Cause:** pilot finding 9, OpenSSL 3's `Verify return code: 0 (ok)` on a failed hostname check.
- **Pilots updated:** ssh_secure (3 mismatches; password-auth-off reduced to its state read) and nginx_static_domain
  (8 mismatches, never varying the Host header: each port has a single server).
- **Re-runs:** both are re-run and re-reviewed because their check files changed. 16 new runner tests.

## 2026-11-16 — HQ: Phase 3 in the loop from batch 4; behaviour state; backfill between batches
After the Phase 1 reviewer PASS (skill step 5b), the advisor writes the class's check set from the baseline.
- **Running it:** validate, run, reviewer `--phase3`; results and reviews are committed.
- **Deferral:** a class that cannot be tested in this lab declares `deferred: {needs: second-node|browser|rhel|desktop,
  why}` with derived_from lines showing why; `run` refuses it.
- **Behaviour state:** pass / finding / deferred (plus none, unreviewed, stale, review-failed, invalid), DERIVED by
  `phase3.py state` from the check, result and review files (P2; no separate record file). It is shown in status.py
  beside the Phase 1 state.
  - stale = the check file changed after its review.
  - finding = the reviewer reproduced a failing check. It must have `escalations/<class>.behaviour.md` (flagged if
    missing) and never blocks the Phase 1 record.
- **Batch report:** a Behaviour section with the state table, authoring minutes, author/reviewer run times
  (`duration_s` in results, new) and review time (`review_s` in verdicts, new).
- **Backfill of the 45 done classes:** between batches, node_base closure first, then nginx/ssl.
- **Retention (HQ):** node v2 and master v3 stay through batch 4, then Salatiel deletes both. After the batch 4
  report, the advisor deletes its own lab-network backups (`~/.ssh/config.pre-p8net-*`,
  `~/.ssh/known_hosts.pre-p8net-step1a`, the master's `/etc/hosts.pre-p8net*`). 8 new tests.

## 2026-11-16 — batch 4: one lab run at a time; a revert proves internet
Two engine gaps surfaced by gnome_lock_screen's first Phase 3 review (FAIL, environment, 8f78d87).
1. **Lab lock.** I ran classify_path's compile-only for the next class while the reviewer's harness was applying, and
   it rewrote the master's node file mid-run.
   - `lab_lock.sh take|release|holder` holds a pid line in a lock file, read and written under a short flock on a
     mutex, so no descriptor is left open for a lingering ssh ControlMaster or VBoxSVC to inherit. A dead holder is
     replaced.
   - test_class.sh (every mode but --render-only), revert_node.sh and phase3.py run take it and refuse at once while
     another live run holds it. P8_LAB_LOCKED=1 passes it to their children: the nested revert, and the harness
     inside a phase3 run.
   - Advisor rule: while any run holds the lab, run nothing that writes the master's node file or touches the node,
     and write new check sets outside the worktree (the reviewer's `git` check requires a clean worktree).
2. **A revert proves internet.** The node once got no DHCPv4 lease on the bridged Wi-Fi (IPv6 only, no default route).
   apt-get update exited 0 on its fetch failures, so the revert reported SUCCESS and the reviewer's apply then could
   not install dconf-cli. revert_node.sh now waits up to 60 s for an IPv4 default route and fails without one, and
   fails on apt fetch or resolve errors. The intermittent lease loss is itself a home-LAN dependency (NAT plan, open
   for review).

9 + 3 tests; a real revert passes and leaves no lock behind.

## 2026-11-16 — batch 4: engine decisions; stopped on the bridged-Wi-Fi DHCPv4 loss
1. **Packages as path providers.** pregate's prerequisite probe counts a package the required_base closure installs as
   a provider (`provided_paths.txt` `package:<name>`, de8ef3a). A class that installs a package and runs its binary is
   no longer a context gap.
2. **Template facts only inside ERB tags** (bda7bbf): plain text is never a fact lookup.
3. **A define needs its params file** (641eced): classify_path reports a missing one as context-gap (hazards.md 10).
   The harness never renders a define from defaults, whatever compile-only does.
4. **Merged /usr** (72abaf0): the probe looks up `/bin/...`, `/sbin/...`, `/lib*/...` under `/usr` when the clean-node
   inventory shows the top directory as a symlink.
5. **One lab run at a time; a revert proves internet** (1a24f54; see its own entry). A `REVERT_FAILED` from the
   internet check stops the run like any other.
6. **Phase 3 deferrals are not reviewer-checked yet** (their state comes from the validated file). Proposed to HQ:
   `--phase3` on a deferred set.

Batch 4 stopped at 5/7 on the second DHCPv4 loss of the day: `escalations/lab-dhcp-bridged-wifi.md`, with the NAT plan
as the recommended fix. openvpn_server is prepared and waits.

## 2026-11-16 — HQ item 2: node selection from a tracked inventory
`.codex_state/lab/nodes.yml` (advisor-only) is the single source for the lab nodes. `nodes.py` is its only reader.
- **Per kind:** status, vm, alias, certname, hostname, hostonly_ip, baseline_snapshot, os_family, os, capabilities.
- **The kinds:** `ubuntu` is the current node, active and the default. `rhel9`, `kubuntu`, `gnome` and `ubuntu2` are
  planned p8lab-* VMs on host-only .21-.24, refused by the engine until brought up.
- **Selection:** `--node KIND`, else the plan row's new `node` column, else `P8_NODE`, else the default.
- **Who follows it:**
  - revert_node.sh: VM, snapshot, alias, address and hostname. Only ubuntu24-puppet8-Node or p8lab-* VMs, never the
    master. RedHat nodes assert a valid subscription and refresh dnf.
  - records.py: one latest-revert record per node; the stamps carry the node.
  - node_inventory.py: a cache per node.
  - pregate: the class's node.
  - test_class.sh in every mode: the alias; the master's node file `nodes/<certname>.pp`; the catalog, facts and
    compile certname; revert, fresh-check and stamp; per-node params `params/<kind>/<class>.json` before the shared
    fixture; compile-only on a RedHat node uses its own facts (`native`) and refuses `--facts debian`.
  - review_class.py: the node identities and the params of the class's node.
  - codex_migrate_class: reverts the class's node.
  - phase3.py: probes and reverts the class's node; a probe may name no lab node.
- **Steps:** n1 2417aca, n2 4714217, n3 b3ed59f, n4 69ca59b, n5 (this commit). 26 new tests.

## 2026-11-16 — HQ item 3: lab_vm.sh, the guarded script for new lab VMs
`lab_vm.sh` acts only on VMs named `p8lab-*`, like snapshot_master.sh does for the master. Every refusal changes
nothing, and every refusal path is tested (22 tests).
- **clone** a source VM into a new p8lab-* VM:
  - the source must be powered off, or cloned from one of its named snapshots;
  - its configuration and snapshot list are fingerprinted before and after, and a difference is an error;
  - the master is never a source.
- **modify:** powered-off only; a `--name` must stay p8lab-*.
- **start:** refused if MemAvailable minus the VM's memory would leave under 4096 MB.
- **stop:** ACPI with a timeout, or `--hard`.
- **snapshot take|restore:** offline only.
- **No delete verb:** deleting a VM or a baseline snapshot stays Salatiel's.
- **Settings:** allow the script; deny raw clonevm, createvm, startvm, controlvm, storageattach, and snapshot
  take/restore/delete/edit on any VM, beside the existing modifyvm and unregistervm denies. The master and
  ubuntu24-puppet8-Node keep their rules.

## 2026-11-16 — HQ item 7: deferrals reviewed and lifted by a named node kind; `uncovered` notes
- **Deferrals:** every deferral names `lifted_by: <node kind>`. The kind must exist in nodes.yml and have the needed
  capability: desktop/browser → desktop, rhel → rhel-subscription, second-node → second-node.
- **Reviewing a deferral:** the reviewer judges it with `phase3.py spot` (the reason and the cited lines read fresh)
  and `verdict` (a deferral record: deferral_valid + derived_from). Its state is `deferred` only after a PASS on the
  current file; otherwise `unreviewed` or `review-failed`.
- **`uncovered` notes:** any check set may list `uncovered: [{what, why, lifted_by}]`.
- **Applied to the two existing sets:**
  - user_kde_lock_screen is lifted by `kubuntu`;
  - user_base notes its ecryptfs branch with the ruled guard as uncovered, lifted by `kubuntu` (an ecryptfs fixture
    user once a desktop node exists, item 7a). Its check file changed, so its state is `stale` until its Phase 3 set
    is re-run when the Ubuntu node has internet again.
- **Phase 5 backlog item 4:** postfix compatibility_level (item 7c).

## 2026-11-16 — HQ NAT review I: tool and settings commits run the full suite
The pre-commit hook runs the full suite, not the fast subset, when the commit stages anything under
`.codex_state/tools/` (the tools and their tests) or `.claude/settings*.json`. A staged batch report still runs it
too; other commits keep the fast subset. Cause: the lab_vm.sh commit (516b455) landed while the full suite was red
(a stale rules digest), because only the fast subset gated it.

## 2026-11-16 — Lab NIC1 → VirtualBox NAT (lab-network-nat.md, HQ step review A–J)
- **What changed:** NIC1 of the master and the node is VirtualBox NAT with `natdnshostresolver1 on`, so the VMs'
  internet and DNS go through the laptop's current uplink and never the home LAN. Each VM's enp0s3 is 10.0.2.15
  (gateway 10.0.2.2); the master's DNS is the NAT proxy 10.0.2.3; the node keeps its static public resolvers
  (1.1.1.1, 8.8.8.8; HQ). Lab control is unchanged (host-only vboxnet0).
- **Node baseline P8NODE_BASELINE_GREEN_v4** (798dd0e5…): v3 + NIC1 NAT + package lists refreshed through NAT, one
  clean boot, no agent run (state token unchanged). The node went to NAT from a manual restore of v3, never through a
  bridged revert (HQ A); the snapshot take was Salatiel's (HQ H). revert_node.sh asserts after every restore: the
  default route is via 10.0.2.2 on the interface holding 10.0.2.15/24, and no address is on 192.168.77.0/24.
- **Facts (HQ B):** networking.hostname, fqdn and domain did not move with the uplink. Node: puppet8node /
  puppet8node.lan / lan (from a static `domain lan` line in the snapshot's /etc/resolv.conf). Master: puppet8master /
  puppet8master.example.com / example.com (its own-name /etc/hosts line). `networking.ip` is 10.0.2.15 on both, as
  expected.
- **Classes reading the VM's own address or server facts (step 0, HQ C):** none. `network_static`'s `$ipaddress` is a
  class parameter, not the fact; nothing uses `server_facts` or `serverip`.
- **firewall_addon_hosting's ruled fix (HQ C):** the master rule's destination is `$server_facts['servername']`,
  resolved on the agent by puppetlabs-firewall 8.3.0, instead of `serverip` (the master's primary address, 10.0.2.15
  on NAT, not the 192.168.56.10 the node uses). Proof and limit in upstream_defects.md.
- **New lab VMs (HQ G):** every `p8lab-*` VM gets NIC1 NAT with the host resolver, and NIC2 host-only vboxnet0.
- **Non-A DNS (HQ D):** MX and TXT queries resolve through the NAT proxy on the master.

## 2026-11-16 — HQ NAT review F: bytes received on the node's NIC1, per revert and per class
- **revert_node.sh** adds `nic1_rx_bytes` to REVERT_METRICS: the default-route interface's `rx_bytes` at the end of the
  revert, so the boot and the package refresh after a restore.
- **test_class.sh** adds `nic1_rx_bytes` to the harness event: the counter's change from just before agent run 1 to
  the end of the harness, so what the agent runs downloaded. A counter that went down (a reboot) gives null.
- **metrics.py close** folds both lists into the record, `nic1_rx_bytes: {reverts, harness}`. The batch report has a
  column "NIC1 rx MB reverts / harness"; records from before this change show –.
- **Purpose:** the data for HQ's package-cache decision before the 23rd. These are metrics only: an unreadable counter
  is null and never fails a revert or a run.

## 2026-11-16 — HQ NAT review G: a p8lab VM starts only on the lab network
- **The guard:** `lab_vm.sh start` refuses, and changes nothing, unless the VM has:
  - NIC1 VirtualBox NAT with the host resolver (`natdnshostresolver1 on`);
  - NIC2 host-only on vboxnet0.
- **The fix it names:** the refusal prints the `lab_vm.sh modify` command that sets the lab network.
- **Where the host-resolver flag is read:** `showvminfo` does not print it, so it comes from the VM's `.vbox` file:
  the current machine's adapter 0, never a snapshot's.
- **Real VMs:** all three VMs (p8lab-rhel9, set through lab_vm.sh modify; the master and the node, set by hand in the
  NAT plan) satisfy the check.

## 2026-11-16 — Node bring-up: p8lab-rhel9 (HQ 2026-11-16 items 4–5)
- **VM:** p8lab-rhel9 (cloned by Salatiel from RHEL9's clean snapshot, registered).
- **Lab network, via lab_vm.sh:** NIC1 NAT with the host resolver; NIC2 vboxnet0 static 192.168.56.21/24 (NetworkManager
  `p8-hostonly`, never-default); /etc/hosts master → 192.168.56.10; hostname p8lab-rhel9.
- **Key and sudo:** Salatiel's one command, over a temporary NAT port forward bound to 127.0.0.1:2221 that was removed
  before the snapshot; he accepted the host key by fingerprint.
- **Domain pinned (as for HQ NAT review B):** NAT's DHCP passes the laptop's current domain, so NIC1 ignores DHCP DNS,
  with DNS 10.0.2.3 set explicitly (still the NAT proxy, so it follows the uplink live) and search `lan`. Domain `lan`,
  fqdn p8lab-rhel9.lan, matching the Ubuntu node's domain.
- **Agent:** openvox-agent 8.24.2-1.el9 (the lab's version) from openvox8-release, service disabled. Puppet.conf as on
  puppet8node: server puppet8master.example.com, certname p8lab-rhel9, node_name cert.
- **Cert:** CSR public key compared on both ends before signing, signed on the master, bootstrap verified.
- **Master:** node file `nodes/p8lab-rhel9.pp` (include passwd_common plus the CODEX markers, as puppet8node's). No
  per-node Hiera is needed (the hierarchy has no node level).
- **Baseline P8LAB_RHEL9_BASELINE_v1** (472b026a…): offline via lab_vm.sh; no agent run before it.
- **Repositories (item 5):** an enabled repository DOES survive a snapshot revert. It is a content override kept on the
  subscription server: CodeReady Builder was enabled again right after restoring a baseline taken before it was
  enabled. revert_node.sh therefore clears the overrides after every RedHat restore and fails unless none remain
  (e5da727); the registration is asserted after every restore too.
- **Verified:** two real reverts SUCCESS (33.8 s each); `--revert-first --fixture guarded_exec` GREEN (NODE_FRESH yes);
  native RedHat compile OK; clean-node inventory taken (49,499 paths).
- **Activated:** nodes.yml rhel9 → active.

## 2026-11-16 — Batch 5 engine decisions (first batch on NIC1 NAT)
- **puppetserver vs the CLI compiler for module Ruby (openvpn_server, category 1):** compile-only and classify_path use
  `puppet catalog compile`, which puts module lib dirs on Ruby's load path. puppetserver's JRuby does not. A
  relationship on a `network_config` resource makes puppetserver load the type's Ruby, and its
  `require 'puppetx/filemapper'` fails. So a compile-only OK does not prove a module's Ruby loads on the server; the
  harness run does. Ruling requested (escalations/openvpn_server.md).
- **Dependency defaults that moved (mysql_server, category 1):** the Puppet 8 line of puppetlabs-mysql (14+) defaults
  Ubuntu ≥ 20.04 to MariaDB. A class relying on the module default for its service now manages the wrong service.
  Ruling requested (escalations/mysql_server.md); the upstream_defects entry is pending HQ.
- **Ruling-7 node fixtures beyond services:** hashman_base and hashman_web run on the Puppet master (the user
  database lives in its code tree). Fixtures `puppetserver_code_tree` and `hashman_master_standin` (adding the lab
  Hiera's example logo files) supply what an agent node lacks; their GREENs are mock-apply. Applying them to the lab
  master is ruled out: it would write the database into the master's live site manifests.
- **pregate hazard 4:** the plan's node_fixture counts as a path provider, and paths are compared as Puppet manages
  them (repeated slashes from Hiera interpolation collapsed). Cases: adb74d6, provided_paths `/etc/mysql`
  (mysql::server's package).
- **Master Hiera fixture for an included class:** `puppet_infrastructure::rsyslog_base::ssldir_override` binds the
  OpenVox ssldir where a class does a bare `include` of rsyslog_base (rsyslog_server). It is a stock path, the one
  named exception to "obviously fake" in master_fixtures.sh.
- **review_class.py reads class files as bytes:** binary files (hashman_web's PNGs) are compared exactly, and a
  binary change counts as a code change (ad12459). The crash produced no verdict. The re-verify ran without `--fresh`
  because the fix commit followed the migrate commit (the reviewer refused `--fresh` as designed).
- **firewall_addon_hosting re-migrated** with the amended ruled fix (destination `$server_facts['servername']`): a
  class_rulings line carries the exact change to the executor; upstream_defects entry applied (bd0529a).
- **Phase 3 authoring lessons** (all corrected with dated notes; failed runs kept):
  - output ordering (`systemctl show` and `dpkg-query` sort their output);
  - line counts;
  - stderr merged into a parsed probe;
  - `mutates` must declare every effect, including stock routing (the rsyslog_server Phase 3 review FAIL);
  - the validator forbids lab host names, `puppet` invocations and `>` in probes, so probes read the certname from
    the node and avoid literal redirects.

## 2026-11-16 — HQ batch-5 rulings (start rule, tail list, snapshot exercise, mysql, rhel9)
- **Start rule (ruling 3):** the next batch may start without HQ unless the batch had any of:
  - a Phase 1 reviewer FAIL;
  - a Phase 3 behaviour finding;
  - three or more Phase 3 authoring FAILs.

  A Phase 3 authoring FAIL that was corrected and re-reviewed PASS doesn't stop it alone, but the report lists every
  one. Skill BATCHES updated.
- **Tail list (ruling 6):** hashman_base and hashman_web are listed as lifted by a master-role node (not blocked; PASS
  mock-apply).
- **mysql_server (ruling 2):** a module-compatibility change (like the firewall-8 renames), not an upstream defect.
  Before dispatch, every puppetlabs-mysql default that differs between the MySQL and MariaDB flavours on Ubuntu 24.04
  is listed and the class sets each one it needs; this goes in class_rulings.txt and the header. Its Phase 3 must show
  a MySQL (not MariaDB) server running from the managed config.
- **extra_packages_el (ruling 5):** unblocked and routed to rhel9 (plan `node` column), the first class on the new
  node; its run is reported in detail.
- **openvpn_server (ruling 1):** stays blocked until Salatiel's production check; network_vpn waits with it.
- **Master snapshot (ruling 4):** taken with the node set, no later than 2026-11-17 evening. Before that,
  snapshot_master.sh's full path (take → restart → health check → record) is exercised against a disposable p8lab
  VM.
- **Batch reports (ruling 7):** add the projected download for re-verifying all done classes, from the per-class byte
  counts.

## 2026-11-17 — HQ batch-5 ruling 4: snapshot_master.sh `--lab-test`
`snapshot_master.sh <P8LABTEST_name> --lab-test <p8lab-vm> <ssh-alias>` runs the script's full path against a
disposable `p8lab-*` VM: busy check, description, ACPI shutdown, offline take, restart, health check, UUID from the
snapshot list, record.
- **Target:** never the master or ubuntu24-puppet8-Node; names `P8LABTEST_*` only.
- **Record:** `.codex_state/logs/lab_snapshot_tests.jsonl` (untracked).
- **Stand-in:** the VM runs a puppetserver stand-in, a systemd unit `puppetserver` serving
  `https://localhost:8140/status/v1/simple` = running. The health check's real command and parsing are exercised
  without a 2 GB puppetserver.
- **Why:** both real runs failed after the take (v4 at the health check, v5 at the UUID lookup).

## 2026-11-17 — linux_policies_user: first File/File_line expected run-2 events (batch 7; for HQ acceptance)
- Evidence run of the unmodified baseline define (fresh node, log .codex_state/logs/linux_policies_user.*.log, run-2
  report read on the node): run 2 changes `Exec[Execute linux policies for: p8testuser]` (no guard; ruled at checkpoint
  2) AND `File[<localdir>/linux-policies/TMP/p8testuser.sh.tmp]` plus both `File_line[...sh.tmp_0/_1]`, at debug log
  level. `tidy` skips a file the catalog manages, so the TMP file persists; each run File resets it to the header and
  file_line re-appends the policy lines. Baseline comment linux_policies_user.pp:35-37 states the intent ("the agent
  will report every time that this file changed because this file is generated dinamically").
- So the ruled session guard alone cannot make the define GREEN. Applied the 2026-11-10 mechanism (plan
  expected_run2_events + header justification, reviewer verifies): `File[*/linux-policies/TMP/*.sh.tmp];
  File_line[*/linux-policies/TMP/*.sh.tmp_*]`, the same basis as Exec[apt_update] and Notify (upstream design that
  reports a change every run). New resource kinds for the mechanism: listed in the batch-7 report for HQ acceptance.
- class_rulings.txt gains the exact form of checkpoint-2 ruling 2's guard (absolute paths; no path parameter needed).

## 2026-11-17 — mariadb_server prerequisites (batch 7)
- Lab Hiera fixture keys `db::organization`, `db::cname`, `db::email` (fake p8test values; master_fixtures.sh hiera):
  the class looks them up for its self-signed certificates' subject and the lab Hiera lacked them.
- class_rulings.txt carries the exact form of the ruled guard (upstream_defects.md mariadb_server): an absolute
  `/usr/bin/test`, since the exec has no `path` (the user_lock lesson: a bare command fails before it guards).
- Plan expected_run2_events `Notify[Produced configs: *]`: the baseline's debug notify at mariadb_server.pp:64 (874f854)
  reports on every run, the case HQ accepted on 2026-11-10 (batch-3 acceptance 2/4); phase5_backlog item 2 already
  lists it ("will need the same plan entry").

## 2026-11-17 — HQ batch-7 acceptance: batch 7 accepted (80 verified); rulings 1-8
1. **linux_policies_user:** the File/File_line expected run-2 events are accepted on the apt_update basis (baseline
   behaviour, stated in upstream's own comment). Conditions:
   - the plan names each resource exactly. For the p8testuser fixture these are
     `File[/opt/puppet-infrastructure/linux-policies/TMP/p8testuser.sh.tmp]` and `File_line[...sh.tmp_0]`,
     `File_line[...sh.tmp_1]`; header updated with `record_green.sh --fix`; the reviewer re-verifies;
   - phase5_backlog item 5: make the temporary script idempotent;
   - the check set's `uncovered` note (policy applied under a login session, lifted_by kubuntu) was already there.
2. **Stand-ins accepted as mock-apply:** letsencrypt_cert_standin and puppet_agent_standin.
   - puppet_agent_standin may replace only the unit's start command; the reviewer confirms it touches nothing else.
     reviewer.md now has the reviewer read the fixture of any mock-apply GREEN and check it against its header's scope,
     and node_base_domain_desktop is re-reviewed under that rule.
   - Tail list: an ACME test endpoint lifts the first, a harness mode that tolerates a running agent lifts the second.
3. **Reporting:** "verified" splits into verified and verified with stand-in (a verified class whose plan row has a
   node_fixture). status.py prints the split and a Stand-ins table (class, fixture, lifted by).
   - **Single source for "lifted by":** each node fixture's one `# Lifted by:` header line.
   - The pre-commit hook rejects a staged batch report whose `## Stand-ins` section misses a stand-in class.
4. **mariadb_server:** approved as a module-compatibility change, not a defect.
   - puppetlabs-mysql 17.3.0 has no parameter for the directory's mode: installdb.pp:16 hard-codes `$log_dir`, and
     :34-38 sets no mode.
   - So the change is a collector override on the exact title, setting the two attributes the module's resource lacks
     (mode 0755, require Package['mysql-server']). The compiled catalog must show the baseline's attributes.
   - Recorded in class_rulings.txt; the class is unblocked. The ruled certificate-exec guard still applies.
5. **openvpn_server:** resolved at step (b) with no master change (escalations/openvpn_server.md, "HQ ruling 5").
   - Production's closure is network_dhcp on the primary interface, never class network (plan corrected, 30c1ea7).
   - The filemapper load came from a relationship target missing from the lab catalog (`Catalog#resource` builds a
     `Puppet::Resource`, and so loads the type, only when its direct lookup misses).
   - Two class-level puppet-openvpn/systemd defects remain for HQ: `Service['openvpn']` at :208, and option A's notify
     on `openvpn::server`, which is a dependency cycle.
   - This corrects the 2026-10-27 escalation's item 3, a compile-only artefact (no `service_provider` fact).
6. **openvpn_domain:** nodes.yml gains the planned kind `dc` (p8lab-dc, Samba AD DC, 192.168.56.25, capability
   `ad-dc`), brought up after kubuntu, gnome and ubuntu2. nginx_proxy_smtp_auth_ppa stays blocked until Salatiel
   decides.
7. **No package cache:** 1.3 GB per full re-verification is acceptable. The projection stays in every batch report.
8. **Order:**
   - bring up kubuntu, gnome and ubuntu2 with Salatiel present;
   - then the master snapshot;
   - then batch 8 with every reachable class.
   The mysql_db and hashman stand-in rulings follow once HQ has read the batch-6 report.

## 2026-11-17 — Engine decisions while applying the HQ batch-7 rulings
- **Fixture scope is a verdict field, not an instruction:** node_base_domain_desktop's first re-review passed with no
  word on puppet_agent_standin. review_class.py now lists a mock-apply fixture's resources, and `verdict` refuses
  without `--fixture-scope`, which is persisted (2dc81c3). The confirmed re-review: 20261117T071317Z.
- **record_green.sh keeps ruled-defect markers:** a `--fix` without `--defect` had rewritten linux_policies_user's
  marker away (f1d4625; restored by the next record). tracker-set now refuses unless `--defect` repeats it (b5df9e0).
- **Header claims skip path segments:** `/opt/puppet-infrastructure/` in exact expected run-2 titles read as an
  unversioned `puppet-infrastructure` dependency claim (aff6ba3).
- **Lab runs block sleep:** KDE's idle suspend paused the VMs during a harness run 2, which hung 557 s and failed.
  test_class.sh and `phase3.py run` hold a logind sleep/idle inhibitor (c36039a); a lid close still suspends.

## 2026-11-17 — HQ rulings after the bring-up (rulings 1-7, second set)
1. **openvpn_server:** option A extended; the module owns the unit.
   - Drop the class's service, drop the define's own notify (:186, a cycle), and retarget :208 to the module's unit.
   - upstream_defects.md is rewritten; class_rulings.txt gains a superseding line; blocked.txt entry removed.
   - Required evidence: a server-config change restarts the unit exactly once, an up-script change restarts it, and
     run 2 is clean. Phase 3 uses ubuntu2 as the client: connect, pool address, server side reachable, wrong password
     rejected. network_vpn follows.
2. **Hazard 14:** a per-class "standalone by production evidence" entry (class, module, evidence reference), nothing
   broader. Built in pregate (rules/hazard14_standalone.txt).
3. **Documentation list:** a production cutover section. VPN gateways: read `service_provider` and the running
   OpenVPN unit first.
4. **mysql_db:** the real compile confirms the baseline ties mysql_db to mysql_server (`require =>
   Class['puppet_infrastructure::mysql_server']`, mysql_db.pp:26). With mariadb_server alone: "Could not find resource
   'Class[Puppet_infrastructure::Mysql_server]'"; with the plan expansion: `Duplicate declaration: Class[Mysql::Server]`.
   - The mariadb pairing is dropped from ruling 1, and mysql_db is MySQL-only by baseline design (class_rulings.txt).
   - mysql_server owns the client: `class { '::mysql::client': package_name => 'mysql-client' }`, a re-migration.
     mariadb_server is unchanged (it already declares mysql::client with its MariaDB library).
   - Standing composite: mysql_server + mysql_db only.
5. **Master-role placeholder** (nodes.yml `puppetserver`) accepted; not built. HQ decides after batch 8 and the DC,
   before the 23rd.
6. **user_desktop_sudoer** may run on gnome now; KDE-specific classes and checks wait for kubuntu.
7. **Order:**
   - kubuntu, once Salatiel has its account;
   - then the master snapshot;
   - then batch 8;
   - then p8lab-dc;
   - then the RedHat branches on rhel9.
   If kubuntu is not up when the rest is ready, the snapshot and batch 8 go ahead without it.
- **Observed (lab):** the laptop's idle suspend between runs paused every VM; 09:20-11:57, while Salatiel was away.
  - The master's clock came back 2 h 26 min behind, with timesyncd still "synchronized". A restart of
    systemd-timesyncd stepped it.
  - Lab runs already block sleep (c36039a). A whole batch now also holds one inhibitor, released at batch end. The
    master's clock offset is checked before the snapshot and before each batch.

## 2026-11-17 — Batch 8 engine decisions (report: escalations/batch-2026-11-17-8.md)
- **Re-migration of a done class:** orientation reads hazard-8 drift from before the first `P8: migrate` commit, and
  states that the earlier migration's differences are expected (d93c02d; mysql_server's ruled client change).
- **Real NICs are device-backed:** the reviewer's fixture check ignores veths, bridges and taps, whatever state the node
  is in (4a4dd82; openvpn_server's false-positive FAIL).
- **Stand-in primary interface `p8test_dhcp_primary`** (mock-apply; HQ acceptance requested): a veth whose peer, in a
  network namespace, runs dnsmasq serving 203.0.113.50 with no router and no DNS. Classes that take over the primary
  interface (openvpn_server, network_vpn) manage it as production manages the real one.
- **Phase 3 peer node:** `peer: {kind, why, files}` and `host: peer` (f184406, 9533f8e).
  - The peer is reverted with the node, receives node files under /run/p8test-from-node, and is powered off after the
    run.
  - Its probes may name only the class node's host-only address.
  - `on:` is not used because YAML 1.1 reads a bare `on` key as true; boolean keys are refused.
- **Per-target base fixtures:** params/for/<target>/<base>.json is preferred when the harness applies that base for that
  target (c8b4965, b1159ae). The reviewer's fixture check uses the same precedence.
- **pregate:**
  - strings and comments are scanned in one pass (d588d7d);
  - declared classes and defines are walked (05552e4);
  - hazard-14 "standalone" entries per class (2d731bc).
- **Lab Hiera:** openvpn_server's local/local_interface for network_vpn (the stand-in interface). The batch-7 `db::`
  keys were removed: common.yaml defines them first, so they never took effect. This corrects the 2026-11-17
  "mariadb_server prerequisites" entry.
- **network_vpn's params fixture** uses RFC 5737 198.51.100.0/24 for the VPN network, so peer probes name no 192.168
  address (the probe host rule is unchanged).
- **Batch-long sleep inhibitor:** the harness and phase3 runs already held one. Batch 8 also held one for its whole
  length, after the 09:20–11:57 suspend left the master's clock 2 h 26 min behind.

## 2026-11-17 — HQ batch-8 ruling 4: lab clocks
- **Why the master did not correct itself:**
  - It has no VirtualBox guest time service. The kernel's vboxguest module is loaded, but VBoxService is not installed.
  - systemd-timesyncd was its only clock discipline. Its poll interval had backed off to the 34 min 8 s maximum.
  - A laptop suspend pauses the VM, and the guest's clock and its timers pause with it. After the 09:20–11:57 suspend the
    master's next poll was still up to 34 min of guest time away. I restarted timesyncd 7 min after the resume.
- **Reproduced on p8lab-ubuntu2.** I paused it for 300 s with a new `lab_vm.sh pause <p8lab-vm> <seconds>`, the same
  thing a suspend does to a VM. Its clock came back exactly 300.0 s behind the laptop's, which is the master's failure
  mode in small.
- **Fix:** master_fixtures.sh has a `clock` section, a timesyncd drop-in `PollIntervalMinSec=32` / `PollIntervalMaxSec=64`
  (idempotent; it restarts timesyncd only on change).
  - On p8lab-ubuntu2 with the same drop-in: after the 300 s pause the clock stepped back to +0.2 s within 65 s.
  - Applied to the master: CHANGED, then OK on the second run. Offset +0.08 s. NTP traffic stays negligible, one query a
    minute.
  - The p8lab nodes and puppet8node boot from offline snapshots for every run, so they start with the host's time.
    Their check is below.
- **The lab refuses skewed clocks:** clock_check.py reads `date -u +%s.%N` over ssh and compares it with the laptop
  clock's midpoint around the call. Half the round trip counts in the host's favour. The limit is 5 s
  (P8_CLOCK_MAX_SKEW).
  - `lab_lock.sh take` refuses while the master is off, so no harness, revert or phase3 run starts.
  - revert_node.sh fails when the restored node is off.
  - test_class.sh refuses to run the agent on an off node; this covers a run without --revert-first.
  - A clock that cannot be read is refused too.
- **Tests:** 13 (clock_check, lock, revert, harness, the master fixture, lab_vm pause). The fake lab answers the clock
  probe with the current time and leaves it out of the call log by default.

## 2026-11-17 — HQ batch-8 ruling 9: Incus on the laptop; first contact over the host-only lease
- **Fact:** Incus runs on the laptop (`incusd`, active, managed by the laptop's own Puppet) and holds 127.0.0.1:2222.
  The lab must not assume that any localhost port is free.
- **What happened:** kubuntu's bring-up used a NAT port forward 127.0.0.1:2222 → 22 (`p8tmpssh`). The forward never
  bound, because Incus already had the port, so every attempt reached Incus. As a result:
  - the "Permission denied" was Incus's sshd, not kubuntu's;
  - the fingerprint I quoted for kubuntu (SHA256:lqe0zo6S…) was Incus's.
  gnome's forward (2223) did bind, so its key, pinned at bring-up, is gnome's own (every later connection to its
  host-only address .23 verified against it).
- **Rule:**
  - A new VM is first reached at the host-only address that vboxnet0's DHCP server leased to that VM's own NIC2 MAC.
  - No fingerprint obtained through a forwarded port is ever quoted.
  - No NAT port forward is added to a lab VM.
- **Tools:**
  - `first_contact.py <p8lab-vm> [--alias] [--user] [--pin]`:
    - reads NIC2's MAC from VBoxManage and finds its acked lease in the vboxnet0 lease file;
    - keyscans that address, prints the fingerprints for comparison on the VM's console, and prints Salatiel's two
      commands (key install, sudo) for that address;
    - reports any forward with the command to remove it;
    - `--pin` writes the keys under the alias after a backup.
  - `lab_vm.sh modify` refuses `--natpfN <rule>`; `--natpfN delete` stays allowed.
- **kubuntu:**
  - First contact went over the host-only address (lease 192.168.56.102). Its keyscan matched HQ's console fingerprint
    SHA256:bYpyVI9T….
  - The wrong known_hosts entry was replaced, and the p8tmpssh forward was removed while the VM was powered off.
  - The bring-up then completed as P8LAB_KUBUNTU_BASELINE_v1 (a9f5707).
- **Tests:** 13, for first_contact and the forward refusal.

## 2026-11-17 — HQ batch-8 acceptance: rulings 2 and 3
- **Start rule, amended (ruling 2):**
  - A reviewer FAIL that an engine bug caused in the safe direction (a false FAIL) does not stop the next batch when the
    bug is fixed with a test and the re-review PASSes. The batch report lists it.
  - batch 8's openvpn_server FAIL is such a case (4a4dd82, re-review PASS).
  - Any discovered false PASS stops everything and goes to HQ.
- **Accepted (ruling 3):**
  - **The stand-in primary interface p8test_dhcp_primary.** The label stays stand-in. Its `Lifted by` line and the tail
    list now name a dedicated real NIC the class may take over (openvpn_server, network_vpn).
  - **The second-node mode for behaviour checks**, with both nodes fresh and both recorded in the verdict.
    - `phase3.py run` records `nodes.{node,peer}`: kind, baseline snapshot, the boot ID read right after its revert,
      the boot ID read at the end of the run, and `fresh`. The boot must be unchanged, and the class node also needs
      the harness's NODE_FRESH.
    - `verdict` adds `nodes_fresh` (every node of the reviewer's run fresh; for a set with a peer, both node and peer)
      and copies `nodes` into the verdict file.
    - Verdicts written before this keep their PASS. The next re-run of openvpn_server's and network_vpn's sets records
      both nodes.
  - **Per-target settings for a base class** (params/for/<target>/<base>.json).

## 2026-11-17 — HQ batch-8 ruling 1: nginx_base, a module-compatibility change
- **The ruling:** the module does the single include of /etc/nginx/modules-enabled, and nginx_base's own include is
  dropped. No production read is needed.
- **The change** (class_rulings.txt): in `$default_configs`, `nginx_cfg_prepend => {'include' =>
  '/etc/nginx/modules-enabled/*'}` becomes `include_modules_enabled => true`.
  - It is explicit, so RedHat keeps the include the baseline had. The module's default is true on Debian only.
  - The rhel9 pass checks the RedHat path.
- **Evidence against the baseline** (the 3268e9a check set, phase3 run 1, 20261117T205451Z, before the re-migration):
  four read-only checks pass. With libnginx-mod-stream installed the result is: 2 includes,
  `module "ngx_stream_module" is already loaded`, nginx -t failed, the service failed.
- **The same set must pass after the change.**
- **Then:**
  1. Re-run the harness, the reviewer and the behaviour checks for every done class whose closure includes nginx_base:
     hashman_web, nginx_frontend, nginx_frontend_domain, nginx_static, nginx_static_domain (code), and ssl_nginx and
     ssl_nginx_domain (plan required_base).
  2. Migrate nginx_frontend_mail.

## 2026-11-17 — Phase 3 desktop sessions on kubuntu (HQ batch-8 ruling 5: the KDE checks)
- **Experiment on p8lab-kubuntu** (a clean revert, a throwaway account). An SDDM autologin drop-in plus a restart of
  sddm brings up a real Plasma X11 session on seat0 in about 25 s:
  - startplasma-x11, kwin_x11, ksmserver and plasmashell run;
  - `who` lists the user on `:0`;
  - `/run/user/<uid>/bus` answers `org.freedesktop.ScreenSaver.GetActive`, and `qdbus org.kde.screensaver /ScreenSaver
    configure` returns 0.

  The headless VM needs nothing more. 1.8 GB stays free.
- **Why a runner step:** the KDE behaviours wait for "an agent run while the user is logged in":
  - user_kde_lock_screen's exec, guarded by `who` in configure_lock_screen.sh;
  - linux_policies_user's exec;
  - linux_policies_common's autostart, which runs at a login.

  The harness applies before any login, and probes may not run Puppet. So the login is a runner step, not a probe.
- **Built:** a `session: {user, desktop: plasma, why}` block in phase3.py.
  - The class's node must have the `kde` capability, and the user must be a p8test* fixture account.
  - After the harness apply, the runner logs the user in (SDDM autologin drop-in, sddm restarted). The session is up
    when `who` lists the user and plasmashell runs, within 120 s; otherwise the run is ENVIRONMENT_FAILED.
  - Then the runner makes two agent runs, as the harness does. Run 1 may apply what needs the session. Run 2 must pass
    the harness's run-2 gate (exit 0 and no events, or only the plan's expected_run2_events); otherwise APPLY_FAILED.
  - Both runs are recorded under `session` in the result, and then the APPLIED phase runs.
- **Tests:** 5. The fake lab now also logs what a tool sends on stdin, so the test can check the order: clean phase,
  apply, login, two runs, APPLIED.
- **For HQ acceptance:** like the peer mode, this is a new capability of the behaviour runner.

## 2026-11-17 — First contact with a clone of a lab node (p8lab-dc); the node can be powered off alone
- **The problem:** p8lab-dc is cloned from puppet8node's baseline, as ubuntu2 was. A clone of the node boots with the
  node's static host-only address (.20) and the node's host keys. It takes no DHCP lease, so first_contact.py's lease
  path cannot find it. ubuntu2's bring-up used a NAT port forward instead, which ruling 9 now forbids.
- **`revert_node.sh --power-off`** powers the node off and stops there: no restore and no start. The next revert brings
  the node back. Lab lock and clock check as for a revert. 2 tests.
- **`first_contact.py <vm> --static <address>`** is the forward-free first contact for such a clone. It refuses unless:
  - nodes.yml gives <address> to a node whose VM is powered off, so nothing else can answer there;
  - the VM answers there with that node's already-pinned host key (StrictHostKeyChecking, HostKeyAlias);
  - an interface of the answering host holds the clone's own NIC2 MAC, read over that connection.

  It keyscans nothing and quotes no fingerprint. The re-keying that follows reads the new key over the verified
  session and matches it with a keyscan at the new address, as for kubuntu. 4 tests.

## 2026-11-18 — A reviewer verdict per node (HQ batch-8 ruling 6: the RedHat branches on rhel9)
- **Which classes:** 16 done classes have OS-specific branches (RedHat/os family/os name). They are caching_nameserver,
  filesystem_base, filesystem_sec, hello_world_flask_common, nginx_base, nginx_frontend, nginx_frontend_domain,
  nginx_static_domain, node_base, packages_base, postfix_smtp_node, rsyslog_base, ssh_secure, ssl_base, sysmon_base
  and user_sudoer. Their Phase 1 verdicts ran on the Ubuntu node only.
- **Built:** `review_class.py check|verdict <class> --node <kind>`, and the reviewer's spawn form
  `<class> --node <kind>`. The spawn-message rule gains that form.
  - It refuses a node that is not active, and a class the plan pins to another node.
  - It exports P8_NODE, which nodes.select already honours after the plan column, so the harness (revert-first),
    the per-node params and the node identities all follow it.
  - The draft records the node. A verdict must use a draft made with the same `--node`, and a plain verdict never
    takes a per-node draft.
  - The verdict goes to `reviews/<class>/nodes/<kind>/<UTC>.json` and records the node. gen_migration_order and
    status read `reviews/<class>/*.json` only, so a per-node verdict never stands in for the class's Phase 1
    verdict. It writes no metrics event, because it is not a Phase 1 attempt.
- **What follows from a result:**
  - A RedHat-branch FAIL is reported as a finding on that node (an escalation), not a re-migration, unless the
    reviewer finds the migrated code at fault.
  - A class that needs RedHat-specific params gets params/rhel9/<class>.json.
- **Tests:** 5.

## 2026-11-18 — rhel9 pass, first triage: two harness/fixture fixes
- **The triage:** the 16 done classes with OS-specific branches, each run through the revert-first harness on
  p8lab-rhel9 by the advisor, before any per-node review. 8 GREEN, 8 RED.
- **Harness: a Debian-only required_external is not declared on a RedHat target.**
  - nginx_base's plan `required_external apt` exists for its Ubuntu-only `Exec['apt_update']`. The harness declared
    it on rhel9, where puppetlabs-apt fails the compile ("only works on Debian"). That took down nginx_base and the
    three classes whose required_base is nginx_base.
  - test_class.sh now skips externals listed in DEBIAN_ONLY_EXTERNALS (apt) when the target OS family is RedHat:
    the node's family, or the compile-only facts variant. 2 tests.
- **Lab Hiera:** postfix_smtp_node looks up `<hostname>::postfix_smtp_node::relayuser/relaypass`. master_fixtures.sh
  adds the p8lab-rhel9 pair, obviously fake like puppet8node's. Applied: CHANGED, then OK.
- **Separately, for HQ** (escalations/redhat_branches.md, at the end of the pass):
  - packages_base/node_base `Exec[dnf-makecache]` runs on every agent run by design. It is the RedHat counterpart of
    the expected `Exec[apt_update]` and needs a plan entry.
  - sysmon_base: on a fresh RHEL 9 node, packages_base's nagios-plugins-all creates /usr/lib64/nagios/ as a
    directory, and filesystem_lib64's link to /usr/lib/nagios then fails.
  - hello_world_flask_common: python3-gunicorn and python3-flask come from EPEL, which the class never declares.

## 2026-11-18 — HQ rulings on round 9 (accepted: 89 done, 77 verified, 12 with stand-in)
- **A1 nginx_frontend_mail:** approved, `stream_access_log => 'off'` in nginx_base's default configs, a
  module-compatibility change (class_rulings.txt). Evidence required: for each done class that includes nginx_base, the
  rendered nginx.conf is byte-identical before and after; re-review only nginx_base and any class whose rendering changed.
  Built for it: `test_class.sh --compile-only --file-digest <path>` (38c8d75). Result (escalations/nginx_base.md, "Ruling
  A1 evidence"): identical for all eight, on Debian and RedHat facts; only nginx_frontend_mail's changes (stream block).
- **A2 RedHat:** no class changes. Production composes these classes under node_base. The plan's required_base becomes
  node-kind-aware: sysmon_base without filesystem_lib64 on RedHat; hello_world_flask_common with extra_packages_el on
  RedHat. If a class's own code forced the dependency regardless of OS, stop and show HQ the line. Checked: neither does
  (sysmon_base's /usr/lib64/nagios/plugins files require only Class[packages_base]; hello_world_flask_common declares
  its two packages and nothing that names EPEL).
- **A3 accepted:** the desktop-session checks, per-node reviewer verdicts (spawn form `<class> --node <kind>`),
  forward-free first contact, and the three stand-ins (p8test_vpn_ca, p8test_desktop_home, p8test_domain_dns).
- **B. New standing policy (Salatiel).** Improving templates, files and scripts so a class achieves its purpose on the
  target OS releases is allowed and expected. Each such change:
  - is driven by a behaviour check that fails before and passes after;
  - is minimal;
  - is recorded in the local-changes list (`rules/local_changes.md`, new) with its evidence;
  - is reviewer-verified.

  No per-item ruling is needed. Escalate when a fix changes a class interface, removes functionality, or has more than
  one reasonable design. Syntax-only stays the default where no check demands a change. This re-derives the Phase 1
  "any behaviour change escalates" bar (CLAUDE.md "Phase scoping") for purpose fixes only. Re-triage the Phase 5
  backlog and every known finding into "stops the class achieving its purpose" (now) or "normalisation" (Phase 5).
- **C. Phase 1 exit: behaviour approved for every active class.**
  1. Every class has a check set that tests its purpose, passing and reviewer-reproduced. The reviewer also judges
     purpose coverage; the existing sets are re-judged.
  2. Stand-ins and `uncovered` notes are lifted where the lab can lift them. The master-role node is built now (no
     longer deferred to December), and Hashman is verified end to end:
     - the page loads through nginx;
     - a fixture user changes a password in a headless browser run from a lab node;
     - the user record is written;
     - another node accepts the new password after its agent run.
  3. A behaviour approval report, one row per class: purpose, what the checks prove, what they do not, node kinds,
     stand-ins. Phase 1 is finished when Salatiel approves it.
- **D. Order:**
  1. nginx_frontend_mail and the RedHat fixes;
  2. the master-role node and Hashman;
  3. the backfill and purpose fixes, in batches of 10 under the start rule;
  4. the approval report;
  5. the test-suite design note (F);
  6. the rename (E).

  Phase 1's target release is Ubuntu 24.04. A 26.04 pass (server and desktop kinds) comes near the end, on HQ's word;
  only the read-only OpenVox support check is done now.
- **E. Phase 2 rename:** target `infra_populi`, option A (at the cutover).
  - Scope (Salatiel, non-negotiable): every live reference in every variant (underscore, hyphen, capitalised, prose)
    becomes the matching infra_populi variant. That covers the namespace, paths including /opt/puppet-infrastructure,
    file and directory names, unit and instance names, rendered text, the engine and the docs. This supersedes the
    draft's out-of-scope note on /opt/puppet-infrastructure.
  - Left as written: references to the old repository as a source (baseline refs), and append-only history.
  - Production moves to a new master, with nodes recreated or re-pointed. The plan adds an inventory of node-visible
    names and, for each, what a re-pointed node is left with; that becomes a cutover runbook section.
  - Consumer conversion scripts (puppet-nodes, meaningful_puppet, Hashman's database, Hiera keys) are prepared and tested
    on synthetic fixtures, applied at cutover, with a check that fails on any leftover old name.
  - Tag `phase1-complete` first. The script and rename_check cover the whole tree and every variant. Full
    re-verification on every node kind with every check set. The baseline's version number is kept; the first
    infra_populi version is Salatiel's call.
  - Production reads are Salatiel's, before the cutover.
- **F. Behaviour test suite** (a design note, then stop for HQ review). Requirements:
  - a conventional top-level test location in the module, not under .codex_state;
  - per-class checks, fixtures and the runner, with a short "test one class" guide;
  - the runner works without the advisor or Codex, against any disposable test node;
  - checks state the purpose they test;
  - no lab-specific names or secrets;
  - JUnit output;
  - the engine consumes the same suite.

## 2026-11-18 — The master-role node p8lab-puppetserver is up (HQ ruling C2)
- **The VM:**
  - cloned from ubuntu24-puppet8-Node at P8NODE_BASELINE_GREEN_v4 (`lab_vm.sh clone`), with 4096 MB for the JVM;
  - first contact forward-free with `first_contact.py --static 192.168.56.20`, puppet8node powered off: the node's
    pinned key and the clone's own NIC2 MAC both checked;
  - re-identified in that one verified session: new SSH host keys (printed over it, pinned under the alias, then
    matched by a keyscan at the new address), hostname, machine-id, certname, enp0s8 192.168.56.26, agent ssl state
    removed;
  - backups ~/.ssh/known_hosts.pre-p8lab-puppetserver and ~/.ssh/config.pre-p8lab-puppetserver.
- **Two roles:**
  - **An agent of puppet8master,** so the harness applies to it. Cert p8lab-puppetserver: the request's public-key
    hash was compared on both machines before signing. The agent service is disabled, as on every lab node.
  - **Its own Puppet server:** openvox-server 8.11.0, the lab master's version. Its `[server]` section has its own
    ssldir (`/etc/puppetlabs/puppet/ssl-server`) and its own CA (`/etc/puppetlabs/puppetserver/ca`, "Puppet CA:
    p8lab-puppetserver"). So the agent identity in the default ssldir, CA puppet8master, is untouched; both verified.
    Heap 768m; enabled, and back up by itself after a revert (status running).
- **Its production environment** holds only puppetlabs-stdlib 9.7.0, copied from puppet8master's: the user define's
  only module dependency (fqdn_rand_string). The module under test arrives per run (next entry).
  `autosign.conf` names one client, p8test-hashman-client, the identity a peer uses to fetch the users the master-role
  server defines.
- **Baseline:** P8LAB_PUPPETSERVER_BASELINE_v1 (8962f4ba). nodes.yml marks the kind active.
  `revert_node.sh --node puppetserver` restores it.
- **Tests:** no real kind is planned any more, so the tests of the planned-node rules use a synthetic planned kind
  (conftest `with_planned_kind`/`planned_inventory`) instead of the real inventory.

## 2026-11-18 — Hashman end to end: the harness deploys to a master-role node; the runner's peer agent run (HQ ruling C2)
- **Harness (test_class.sh `deploy_repo_to_node_server`):** when the target node has the `puppet-server` capability,
  the harness also installs the module under test in that node's own code tree, after the revert and right after the
  master's copy: the same tree, staged and moved into place as root, as for the master. A production master serves
  the module the same way. The node's environment otherwise holds only stdlib (its baseline). 2 tests (a puppet-server
  node gets the copy; an ordinary node never does).
- **Runner (phase3.py `peer_agent`):** a set whose class node is a Puppet server may declare
  `peer_agent: {after, certname, why}`.
  - Right after the named mutating check (action, then effect), the runner makes one agent run on the peer against the
    class's node, as `certname`.
  - `certname` must be a p8test* identity, and the master-role baseline's autosign.conf names exactly one,
    p8test-hashman-client.
  - The run uses its own confdir /etc/p8test-agent/<certname> (own ssldir, vardir, rundir, logdir), so the peer's
    identity toward the lab master is untouched.
  - The peer resolves the server through one hosts line naming the class node's host-only address, the only other
    host a peer may name.
  - The exit code, the changed resources and the output tail go to the result under `peer_agent`; the checks after
    it judge the result.
  - It is a runner step like the session's agent runs. Probes keep the Puppet ban.
  - Validation refuses: a node without puppet-server, a set without a peer, a non-p8test identity, and an anchor that
    is not a mutating check.
  - 3 tests.
- **For HQ acceptance:** a new capability of the behaviour runner, like the peer and session modes. It lets C2's last
  step ("another node accepts the new password after its agent run") be a check.

## 2026-11-18 — Hashman on the master-role node: a local MTA, ubuntu2 v2 with a browser, fresh handover files (C2)
- **The plan:** hashman_base and hashman_web are tested on node puppetserver.
  - hashman_web is GREEN there: revert-first, 98 events, run 2 only the expected Notify.
  - The master gained the node file manifests/nodes/p8lab-puppetserver.pp (the lab nodes' skeleton).
- **hashman_base needs a local MTA. Its code requires it; hashman_base declares none.**
  - libhashman/mailutils.py sends every notification through `smtplib.SMTP('127.0.0.1')`, including the team
    notice after useradd, even with SILENT.
  - Without an MTA, useradd wrote the user and then died with ConnectionRefusedError, leaving its lock directory
    /tmp/pp_auth.lock behind. Every later command refused ("could not acquire a lock"), and so would the web page.
  - The required_base of hashman_base gains postfix_smtp_node, the module's class for sending mail from a node (4
    direct production declarations). With it, useradd, unlock and printinfo all succeed. The master_fixtures hiera
    section adds the obviously fake relay keys for p8lab-puppetserver (13 values).
  - **For Salatiel:** whether production's master is one of postfix_smtp_node's direct declarations is a production
    read.
  - The stale lock after a mail failure is a robustness defect of the baseline. It does not stop the purpose while an
    MTA runs, so it goes to the Phase 5 triage.
- **ubuntu2 baseline v2 (P8LAB_UBUNTU2_BASELINE_v2):** v1 plus test tooling only, installed once instead of
  downloaded on every run. nodes.yml points at v2; v1 stays.
  - pamtester and python3-venv;
  - /opt/p8test-browser, a venv with playwright 1.64.1 (2026-10-22) and Chromium headless shell 156.0.8078.4 with its
    system dependencies.
- **Runner:** peer.files are read again before each mutating peer check, so a file a node action wrote just before
  reaches the peer. Hashman's admin step on the node produces the initial password the peer's browser needs. 1 test.
- **For the 26.04 pass:** hashman imports Python's `crypt` (DeprecationWarning on 24.04's 3.12; the module is gone in
  3.13). On 26.04 it stops the class's purpose.

## 2026-11-18 — Purpose coverage: check sets state the class's purpose; the reviewer judges it (HQ ruling C1)
- **The set:**
  - A top-level `purpose:` is required: one or two sentences on what the class is FOR, from its own header and code.
  - It is ≥ 40 characters and validated.
  - With each check's `what`, it is how "checks state the purpose they test" (also requirement F).
- **The verdict:** `phase3.py verdict ... --purpose covered|gap --purpose-evidence TEXT` is required.
  - `gap` fails the review (checks.purpose = fail), and the evidence is persisted.
  - The reviewer's instructions (.claude/agents/reviewer.md, `--phase3` step 2b) define it:
    - `covered` when every part of the purpose the lab can exercise is tested, and every part it cannot is listed
      under `uncovered` with the node kind that would lift it;
    - `gap` when a part the lab CAN exercise is untested, or the stated purpose misreads the class.
  - The same applies to deferrals.
- **The state:** a new value `unjudged`, for a set without a stated purpose, or one whose review predates the purpose
  judgement. Its earlier PASS stays as history but is not behaviour approval (C3).
- **Where things stand:** status shows 41 none, 3 stale (the pilot sets, which gained their purpose here), 46
  unjudged, of 90 done. The backfill re-judges them all in batches of 10 under the start rule (D3).
- **Tests:** 3 new; the pinned verdict shape gains `purpose`.

## 2026-11-18 — Runner: `node_agent`, an agent run on the class's node after a drift-making check (backfill)
- **Why:** many classes exist to correct drift: purge firewall rules they do not manage, restore a file's content or
  mode. A behaviour check can show that only if the class runs again after the drift. Probes keep the Puppet ban.
- **What:** `node_agent: {after: <mutating check id>, why}`. Right after the named mutating check (its action makes the
  drift), the runner makes one agent run on the class's node, as the harness and the session do. The exit code and
  changed resources go under `node_agent`; the checks after it judge the correction. 2 tests.
- **For HQ acceptance** with the other runner capabilities of this round (peer_agent, refreshed peer files).

## 2026-11-18 — HQ rulings on batch 10 (accepted: 90 done; Hashman verified end to end; 16/16 RedHat branches)
1. **Start rule for the backfill** (replaces the limit of three):
   - A check-set FAIL that is corrected and re-reviewed PASS does not stop the run.
   - A behaviour finding or a Phase 1 FAIL does stop it.
   - A set that cannot reach PASS after two correction rounds is escalated, and the run continues.
   - Each batch report gives the first-draft FAIL count. Batch 10's: 5 of 10 sets failed their first review
     (firewall_secure, rsyslog_base, dns_client, filesystem_apt and filesystem_yum).
2. **Writing check sets:** first list the class's purpose as observable outcomes, taken from the baseline's code and
   comments. Every outcome maps to at least one probe, in a table inside the set; an outcome with no probe is
   declared `uncovered` with its reason. The reviewer judges against that table.
   - Built: phase3.py `outcomes:`, where each row is `{outcome, from, checks: [ids]}` or `{..., uncovered: {why,
     lifted_by}}`.
   - The validator refuses a missing or ill-formed table. A set without one is `unjudged` ("no outcomes table yet").
   - Each run records every outcome with its checks and whether they all passed, for the approval report.
   - reviewer.md step 2b judges against the table. 3 tests.
   - The ten batch-10 sets and the three pilots predate the table; they gain it, and a re-review, in the backfill.
3. **Numbers:** any time or number in a set, a record or a report is measured or absent, never estimated. Authoring
   minutes come from `date` at the start and at validation (or from file times, said so), never from memory.
4. **Policy B also covers purpose fixes in manifests,** under the same conditions.
   - Built: tracker marker `; local change: <short>`, set by `record_green.sh --local-change` and refused without the
     class's row in rules/local_changes.md.
   - The reviewer's check output prints the row (LOCAL CHANGE, POLICY B), and DIFF A may contain exactly that change.
   - Tests: tracker grammar, the row reader, the marker writer.
5. **rsyslog_base (#14) approved:** the service subscribes to the three TLS files, and the check shows that a changed
   file restarts rsyslog once. The same applies to rsyslog_client and rsyslog_server if they share the pattern.
6. **hashman_web (#8):** the backend binds to 127.0.0.1, with no firewall change. If the baseline's nginx proxies to
   anything other than the local machine, stop and report instead. Checks: port 8080 refused from the peer, the page
   works through nginx, and the end-to-end run still passes. Recorded as a local change.
7. **Accepted:** all the capabilities listed in the batch 10 report.
8. **Postfix on the master:** answered from the fleet data, as a count of node statements that declare both
   hashman_web and postfix_smtp_node. If zero, the documentation list says that Hashman needs a mail service
   nothing declares.
9. **Logo files:** a placeholder logo is a test asset, not a stand-in, and company logos stay out of the repo. The
   documentation list notes that a site supplies its own.
   - Built: rules/test_asset_fixtures.txt. A node fixture listed there needs no mock-apply marker (records.py), and
     the reviewer judges it as a test asset.
10. **Lift** the mount_shares_desktop and user_lock stand-ins as queued. The remaining stand-ins go into the approval
    report for Salatiel's explicit acceptance.
11. **Ubuntu 26.04:** the cutover targets the newest OpenVox 8 that supports it. The lab upgrades only right before
    the 26.04 pass, as one recorded toolchain change with a canary. Hashman's `crypt` fix belongs to that pass.
    Nothing now.
12. **Order unchanged:** backfill in batches of 10 by production use, then the approval report, then the test-suite
    design note, then the rename.

## 2026-11-18 — HQ batch-10 ruling 8 answered: postfix_smtp_node on the Hashman master
- **Count:** 1 production node statement declares hashman_web, and the same statement declares postfix_smtp_node
  (both: 1).
- **Method:** fleet_class_usage.md's: one node statement per file, every group except deleted/ and tests/, and a class
  counts if declared directly, through a meaningful_puppet class or through a puppet_infrastructure composite; passwd/
  is never read. Names and counts only.
- **Cross-check:** the per-class counts (hashman_web 1, postfix_smtp_node 3) match the committed fleet table. The
  script counted 38 production statements, against the 37 implied by that table's method note (47 parsed, minus 9
  deleted and 1 test). The two class counts do not depend on that difference.
- **Result:** production's Hashman master composes the MTA that Hashman's mail needs, which is the lab composition
  (hashman_base's required_base postfix_smtp_node). No documentation-list entry is needed.

## 2026-11-18 — Backfill order: a conditional declaration counts only the statements that turn it on
- **Error:** I ordered backfill batch 2 by fleet_class_usage.md's `prod` column. Its closure is unconditional, and its
  own `conditional` column marks the rows that overstate. firewall_secure_extra (row 58) and puppet_boot_run (row 58)
  are declared by node_base only inside `if ($firewall_secure_extra)` and `if ($run_puppet_on_boot)`, both false by
  default.
- **Measured** (one node statement per file, every group except deleted/, tests/ and passwd/; names and counts only):
  - 0 of 38 statements set `firewall_secure_extra => true`;
  - 1 of 38 sets `run_puppet_on_boot => true`;
  - no fleet file outside passwd/ names firewall_secure_extra or its parameters.
- **Rule from now on:** for a class whose row has a `conditional` note, the backfill's production-use count is the
  number of statements that turn the condition on, read from the fleet by names and counts only. Classes with 0 go to
  the end of the backfill order.
- Evidence: escalations/firewall_secure_extra.behaviour.md; batch report escalations/batch-2026-11-18-11.md.

## 2026-11-18 — HQ rulings on batch 11 (firewall_secure_extra)
1. **Blacklist: fix it, option A.** A blacklist that lets a listed address in does not achieve the class's purpose.
   - Number the drop ahead of every accept, including the established rule.
   - The baseline describes a blacklist of addresses (line 25: "list of strings containing source IPs to be dropped
     unconditionally"), so the drop covers all protocols, not the module's TCP default.
   - Recorded as a local change, with before and after evidence: a blacklisted peer is refused, and a non-listed peer
     is unaffected.
   - Implementation: puppetlabs-firewall 8.3.0 orders a chain's managed rules by a plain string sort of their titles
     (provider `insert_order`, `rules.sort`). A title beginning `00 ` sorts before every `000 …` title and every
     other numbered title, so the rule becomes `00 grounding naughty boys: <ip>` with `proto => 'all'`.
2. **RST limit: no fix.** The protective effect holds through other rules (501). It is listed in the approval report
   as an unreachable rule, and added to the Phase 5 backlog (rules/phase5_backlog.md #7).
3. **Check set:** a third round runs together with fix 1, and it is the last. If it fails review again, escalate with
   the reviewer's reasons verbatim and move on.
4. **Authoring rule for firewall classes:** take each rule's effective attributes from the compiled catalog, including
   module defaults such as the protocol, before writing an expectation (CLAUDE.md "Phase 3 checks"; skill step 5b).
5. **Restart batch 2 in the re-derived order.** firewall_secure_extra goes at the end of this batch, not the end of
   the backfill. The batch is the 10 classes without a check set, by production use under the corrected count:
   firewall_ipv6_drop (done), node_base, sysmon_base, ssl_base, ssl_nginx_domain, nginx_default_removal,
   nginx_frontend_domain, nginx_frontend, docker_container, firewall_secure_extra. puppet_boot_run (1 statement) moves
   to a later batch.

## 2026-11-18 — HQ rulings on batch 12
1. **Rule 518 (firewall_secure_extra, TCP fragments):** the same handling as the RST limit (Phase 5 backlog #8,
   approval report). **Standing rule:** a rule proven unreachable, whose protection is shown to hold elsewhere or is
   not needed, is recorded (approval report, Phase 5 backlog) without a ruling. If the protection does not hold, it
   is a finding.
2. **firewall_secure_extra's set: one more round, the last for this class.**
   - First find which rule took the eighth held connection, from the rule counters before and after.
   - If the cause is the test, fix the test.
   - Only if the counters show a legitimate interaction may the expectation become "7 or 8 held, the 9th and 10th
     dropped".
   - Whatever the result, the class then goes to the approval report as it stands.
3. **sysmon_base's set:** run round 3, since the failed-run CRITICAL path is the core of the class's purpose.
   Correction rounds are capped at **three for classes used in production** and **two for the rest**.
4. **Markers:** the tracker marker lists local-change numbers generated from rules/local_changes.md. record_green
   regenerates it when the list grows, and a marker never shrinks without an explicit flag (`--shrink-local-changes`).
   Tested.
5. **Run rule, amended so the backfill does not wait on HQ:**
   - an escalated check set does not hold the run;
   - nor does a finding with one clear fix under policy B;
   - a finding with more than one reasonable design is escalated for that class, and the run continues with the next
     class;
   - only a Phase 1 FAIL or a discovered false PASS stops everything.
6. **Probe helpers:** half of the first drafts failed on probe mechanics. A small tested helper library (count, port,
   HTTP, service state, file digest, connection hold) is used wherever a helper fits. It will become part of the
   public test suite: `.codex_state/tools/probe_helpers.sh`, prepended by phase3.py to every node and peer script, with
   mutating helpers refused outside a check's action.
7. **Continue with batch 3 and onward,** by production use under the corrected count, mixing classes with no set and
   classes whose set is unjudged.

## 2026-11-19 — Backfill batch 4: the peer's address for node scripts, the lab's IPv6 and named, holds on the uplink
1. **Node scripts get `P8_PEER_ADDR`** (phase3.py, commit e85d826, tested).
   - postfix_smtp_node's relay check had to pin the relayhost's name to the peer from a node action, and the validator
     forbids lab addresses written into node probes.
   - When a set declares a peer, the runner now prepends `P8_PEER_ADDR=<the peer's host-only address>` to node
     scripts, so a node action names the peer by reference. Without a peer the variable is absent, and the validator's
     rule is unchanged.
2. **The lab NAT's IPv6, and named.**
   - VirtualBox NAT hands the VMs an IPv6 default route by router advertisement that reaches no internet.
   - Removing that route (the fixture since caching_nameserver's set) is not enough for BIND 9.18.39. Each IPv6
     attempt then fails at once ("network unreachable") but still counts against max-recursion-queries (50), and a
     name with a long delegation chain gets SERVFAIL. Measured on network_vpn's applied node: 49 of the 50 queries
     were IPv6.
   - Disabling IPv6 on the host did not stop the attempts; named with `-4` resolved every name.
   - **The lab fixture for a set that needs recursion:** remove the route and run named with `-4`, set in
     /etc/default/named (no class manages that file), with the flag shown in named's command line.
   - caching_nameserver's passing set still carries the route-only fixture. It is to be updated, since it can fail
     falsely, though never pass falsely.
   - Whether an IPv4-only production host meets the same limit is a question for HQ, not a lab fact.
3. **Lab holds on the uplink.**
   - The revert's apt-update limit (180 s) stays as it is.
   - A revert that fails on the mirrors puts lab runs on hold, with escalations/lab-uplink-2026-11-19.md. This
     happened twice on 2026-11-19: a slow uplink, then Canonical's archive refusing TCP while other hosts worked.
   - Switching the lab to another mirror changes the test environment, so it waits for Salatiel's go.
   - The lab lock's clock-skew guard caught a stopped master clock (5270 s behind). Its own remedy, restarting
     systemd-timesyncd, fixed it without restarting the master.
4. **A composite checks a component's finding on a value the composite itself passes.** network_vpn passes its own
   default cipher to openvpn_server, so network_vpn's set carries the cipher check too and its state shows the
   finding. What the composite only inherits (compression) stays with the component's set.

## 2026-11-19 — HQ rulings on batch 14
1. **openvpn_server and network_vpn, cipher: option A approved.** The class's cipher is added to the server's accepted
   list (data-ciphers), so existing clients keep connecting, and clients that negotiate a stronger cipher keep doing so.
   It is a local change, with the before-and-after check: a client offering only that cipher connects.
2. **Compression: option F approved, no change.** The one-way behaviour goes into the approval report and the
   documentation list: clients should drop compression at the cutover.
3. **ssh_secure:** restore the idle disconnect with sshd's own idle-timeout settings on OpenSSH versions that have
   them (9.2 and later, so Ubuntu 24.04), set from the class's existing timeout value.
   - Where the OpenSSH version lacks them (RHEL 9), it is recorded as not enforced there, with no shell workaround.
   - If the analysis finds a reason this does not work, hold the class and show HQ instead.
4. **network_dhcp and network_static:** they stay escalated until Salatiel answers how the production VPN servers'
   network is configured. No change yet.
5. **caching_nameserver on hosts without IPv6:** keep the IPv4-only fixture for the lab and make no class change now.
   It is recorded as a condition in the approval report, and becomes a finding only if Salatiel confirms a production
   host lacks IPv6.
6. **Lab IPv6:** no baseline change. It is handled per class with fixtures.
7. **Mirror fallback:** allowed only when the primary archive fails, for that run only, recorded in the run record,
   and never written into a baseline.
8. **Go:** batch 5 starts with user_base.

## 2026-11-19 — Backfill batch 5 and the batch-14 rulings carried out
1. **Local changes #7 and #8 are done** (Phase 1 and Phase 3 PASS each).
   - **#7:** openvpn_server adds the class's cipher to data-ciphers, after OpenVPN 2.6's default list.
   - **#8:** ssh_secure sets sshd's own idle timeouts from client_alive_interval, guarded by saz-ssh's
     ssh_server_version_release fact (9.2 and later).
   - **#8's first value was wrong.** `ChannelTimeout session=` matches no channel type on OpenSSH 9.6; the types are
     session:command, session:shell and session:subsystem:..., per the node's sshd_config(5). The correct value is
     `session:*=`. Phase 3 caught it, not Phase 1: the first Phase 1 review judged the diff against the row, and the row
     carried the same wrong value.
   - **ssh_secure's lab fixture moved from 10 to 30 s.** A working 10 s idle timeout also closed the lab's own silent
     SSH sessions to the node.
2. **The mirror fallback is built as ruled** (revert_node.sh):
   - a tmpfs copy of the sources, bind-mounted over the file, for that run only;
   - nothing is written to disk or to a baseline;
   - `apt_mirror` is recorded in REVERT_METRICS and in the phase3 run records.
   Every run since shows `primary`.
3. **rules/approval_conditions.md** is the single source for what HQ rules "record in the approval report". Its items:
   compression (openvpn_server), BIND on IPv4-only hosts, and RHEL 9's unenforced idle disconnect (ssh_secure).
4. **Fixtures moved closer to the class's defaults and purpose.** They are params and never committed:
   - **user_base:** ignorekey false, with a test RSA public key (no private half kept anywhere);
   - **user_base and user:** the SHA-512 hash of the test password `p8test-user-not-a-secret`, so a password login
     can be shown;
   - **sync:** two host names, both pinned to the peer.
5. **Proposal for HQ, not built: a validator rule against unverified uncovered reasons.**
   - **The record:** three reasons I gave for leaving an outcome uncovered were untrue:
     - sync's "one remote host" was a fixture choice;
     - user's "checked in user_base's set" was untrue for the variants;
     - backup_rsnapshot_pre's "needs a terminal" was wrong: `read` takes stdin.
   - **The rule:** the validator would require such rows to name a parameter variant or a lab limit, whenever
     `lifted_by` is the set's own node kind.

## 2026-11-19 — HQ rulings on batch 15
1. **Batch 15 is accepted** (39 approved). **Not a false PASS.** The definition, for the record: a false PASS is an error
   that got past every gate that applied to it and was recorded as approved. An error stopped by a later gate in the
   same cycle is the gates working. The ssh_secure value was caught by its behaviour check before approval.
2. **A class carrying a new local change gets its Phase 1 PASS only once the change's after-check has passed,** and the
   reviewer confirms that result exists.
3. **Validator rule approved, applied capability-based** (Salatiel's answer, 2026-11-19):
   - every `uncovered` row carries evidence for its reason: a command result, or a capability missing from the node
     inventory;
   - `lifted_by` names either a node kind that is not active, or a missing capability;
   - a row whose lifting node kind is already active is rejected, and becomes a work item to test on that node.

   **Scope:**
   - the rule is enforced now for new and changed sets;
   - the 36 approved sets with such rows (70 rows: 28 parameter variants, 16 RedHat branches on rhel9, 26 others) are
     swept in a scheduled pass, not invalidated at once.
4. **Continue with batch 6 and onward** under the run rule.
5. **network_dhcp and network_static.**
   - **Production** (read by Salatiel): a VPN server runs Ubuntu 22.04 with netplan from the cloud image and ifupdown
     installed, with a populated interfaces file. So production's design is ifupdown alongside netplan.
   - **Keep that design:** the classes declare ifupdown explicitly, if it is installable on Ubuntu 24.04; if it is not,
     stop and report.
   - **To find out:** why production has ifupdown and the lab does not. Record the answer.
   - **Checks:**
     - the fixture interface comes up through ifupdown;
     - it survives a restart of the networking service;
     - the node's primary interface keeps working.
   - **Later:** native netplan support goes on the Phase 5 backlog, and ifupdown's availability is checked in the 26.04
     pass.
6. **caching_nameserver.** The same production server has no global IPv6 address, so the IPv4-only condition is now a
   finding.
   - **Fix:** named runs IPv4-only when the host has no global IPv6 address, and is unchanged otherwise.
   - **Checks:** on the IPv4-only node, the names that failed now resolve. The IPv6 side cannot be tested in the lab:
     record that as uncovered, with the evidence.
   - **Afterwards:** remove the approval condition once this passes.

## 2026-11-19 — The lab VM crash on a laptop resume, and what it changed
1. **The crash** (escalations/lab-vm-crash-2026-11-19.md):
   - the laptop suspended at 20:35:48Z;
   - on resume, at 20:38:08Z, both lab VMs went to Guru Meditation with VERR_VMX_INVALID_VMXON_PTR;
   - kvm_intel is loaded beside VirtualBox on the laptop;
   - no lab run was active: the runs' own inhibitors (test_class.sh, phase3.py) covered only the runs;
   - Salatiel powered both VMs off; Salatiel is checking the KVM side.
2. **A sleep guard** (HQ batch-15 follow-up 1): lab_sleep_guard.sh blocks sleep (logind, `--what=sleep --mode=block`)
   for as long as any lab VM runs, and releases it when the last one stops.
   - revert_node.sh and `lab_vm.sh start` call `ensure` (idempotent).
   - The guard sleeps with the system's `sleep`, so a stub on PATH cannot make it spin. This happened once in the test
     suite before the fix: leaked test guards ran with a stub `sleep`, and the load average reached 37.
   - The stub lab opts out of guards by default.
3. **Two defects of the lab lock** that the recovery exposed, both fixed and tested:
   - **The clock check:** the lock refused the very revert that starts a powered-off master, because it checked the
     master's clock first. Now `take` skips a master that is not running, and revert_node.sh checks the clock of a
     master it started (−1.07 s measured on the resume).
   - **The mutex:** the master-state read added for that ran under the lock's mutex and started a VBoxSVC that inherited
     the mutex. The revert's release then waited 9 minutes, until I removed the stale mutex file. Every command under
     the mutex now closes its descriptor (`8>&-`). The test checks the descriptor itself and fails without the fix.
4. **The master after the restart:**
   - puppetserver active, 8140 listening, `/status/v1/simple` HTTP 200;
   - clock NTP-synchronized;
   - the CA lists 8 certificates, including puppet8node and p8lab-ubuntu2;
   - `puppet module list`: 28 modules, none invalid, and only the two expected Windows-only warnings (powershell,
     reboot via docker; entry of line 528).
5. **Facter and IPv6** (for caching_nameserver, HQ batch-15 ruling 6): on the lab node, Facter reports the VirtualBox
   NAT's unique-local address fd17:625c:f037:2:a00:27ff:fe76:5ec6 with `scope6: global`, and `networking.ip6` is that
   address. The kernel calls it scope global too.
   - So "no global IPv6" is decided from the address (2000::/3), never from Facter's scope.
   - The node has no 2000::/3 address, as Salatiel found on the production VPN server.
6. **Uncovered rows, follow-up to ruling 3:**
   - status.py and the approval report show the count of open uncovered rows per class.
   - **Sweep order, after the backfill:**
     1. the RedHat rows, on rhel9;
     2. the parameter variants that production sets (names and counts from the fleet data);
     3. the remaining variants, listed for Salatiel's acceptance, not tested one by one.

## 2026-11-20 — Local change #9 done; the review form for a class with a new local change
1. **Local change #9** (caching_nameserver, HQ batch-15 ruling 6) is done.
   - On a host without a 2000::/3 address, a stdlib file_line makes named IPv4-only.
   - On the IPv4-only lab node, www.debian.org and www.kernel.org now resolve at the first cold attempt.
   - Phase 1 PASS 20261120T000035Z, with the after-check confirmed by the reviewer. Phase 3 PASS 20261120T000624Z.
   - Approval condition #2 is removed; its number is not reused.
   - The plan row gained required_external stdlib (file_line, as linux_policies_user).
2. **The review form.** Ruling 2's order (record_green, the Phase 3 after-run, the row's after evidence, then the
   reviewer) puts commits after the migrate commit, and the reviewer's `--fresh` refuses that ("only for the review right
   after a migration"). For a class with a new local change, the Phase 1 review uses the plain form `<class>`, which
   re-verifies the recorded class. Recorded in CLAUDE.md.

## 2026-11-20 — ifupdown alongside netplan (HQ batch-15 ruling 5): measured facts and the plan
1. **ifupdown is installable on Ubuntu 24.04:** 0.8.41ubuntu1 from noble/universe (apt-cache policy on the 24.04
   master), depending only on libc6, adduser and iproute2. So the ruled design stands; no stop.
2. **Why production has ifupdown and the lab does not** (the answer HQ asked to record).
   - network_dhcp's own header: it "was originally created because the OpenVPN server class needs to manage interface
     lo".
   - In production, the same 3 node statements declare network_dhcp and network_vpn (fleet_class_usage.md: direct=3
     each), and network_vpn brings in openvpn_server.
   - openvpn_server installs ifupdown itself (`package { ['ifupdown', 'bridge-utils']: }`, baseline :35) and enables
     the networking service (:38-41). That is the ifupdown and the populated interfaces file Salatiel found.
   - The lab ran network_dhcp alone, so nothing installed ifupdown.
   - network_static has 0 production statements.
3. **On the 24.04 node** (prototype, 2026-11-20):
   - installing ifupdown enables networking.service by itself, so network_dhcp needs only the package;
   - `ifup` of a DHCP stanza uses dhcpcd (dhcpcd-base; isc-dhcp-client is absent), and p8test0 got 10.251.0.146/24
     from the fixture's server;
   - dhcpcd added the fixture's default route at metric 1005, behind the NAT route's 100, and the node kept its
     internet.
4. **Recording.**
   - **network_dhcp:** declares ifupdown (local change #10) through stdlib ensure_packages.
   - **openvpn_server:** its plain package declaration becomes the same ensure_packages (class_rulings.txt), so the two
     classes compile together in either order.
   - **network_static:** gets the same declaration and a set of its own.
5. **Reported, not part of ruling 5.** network_static's default route is hard-coded to `interface => 'eth0'` (baseline
   :13), whatever $iface is. Ubuntu 24.04 names interfaces predictably, with no eth0.
6. **Plan:** native netplan support goes on the Phase 5 backlog, and ifupdown's availability is checked in the 26.04
   pass (HQ ruling 5).

## 2026-11-20 — HQ after batch 15: network_static fixed, no hand-entered authoring time, lab power commands
1. **network_static (HQ item 1, keep and fix).** The baseline's parameters show the gateway belongs to the interface the
   class configures: one `$iface` with its address and gateway, no other interface; upstream f807e7b split it from the
   first OpenVPN file, whose WAN interface defaulted to `eth0`. Local change #12: `interface => $iface`. Before:
   route check `0` (20261120T011857Z); after: `1` (20261120T084255Z). Phase 1 PASS 20261120T084744Z, Phase 3 PASS
   20261120T085040Z. The route takes the node's default route on the lab node, so the node is reverted after every run.
2. **Authoring time (HQ item 2).** Computed by the tool or not recorded: phase3.py refuses an `authoring` block, and
   the block is removed from all 79 sets. Results and reviews now carry a content sha (the set without that block), and
   older records are matched through the git version their full-file sha names, so removing the block left every
   reviewed set reviewed (state unchanged). Found on the way: an approved set's new-form uncovered rows (evidence,
   `capability:`) were judged by the earlier rule and read as invalid; they are now judged by the new rule.
3. **Lab power (HQ item 3).** `lab_power.sh down|up`, the second sanctioned master shutdown beside snapshot_master.sh
   (CLAUDE.md updated). Down: TERM to the lab lock's holder and a wait (refuses, touching nothing, if it does not stop),
   the lock, every other running lab VM powered off (nodes are reverted before use), the master through ACPI with a
   timeout and never forced, the sleep guard released. Up: the lock, the master started, SSH + puppetserver + 8140 +
   clock checked, the node reverted. 9 tests on the stub lab.

## 2026-11-20 — HQ accepts travel readiness, with three additions
1. **Lab power at run boundaries.** When a run stops to wait for Salatiel or HQ, `lab_power.sh down`; `lab_power.sh up`
   when work resumes. The lab is never left running unattended (CLAUDE.md, migrate-next END OF RUN and PREFLIGHT).
2. **Battery guard.** The sleep guard, which runs exactly while lab VMs run, reads /sys/class/power_supply each poll
   (30 s): a battery whose kernel status is `Discharging` below 25% starts `lab_power.sh down` once, detached. Down
   aborts the run holding the lab (TERM), powers the nodes off and the master through ACPI, and releases the guard.
   `Not charging` and `Full` are on mains (the laptop reports `Not charging` at 99% on its adapter). Tests: down at 20%
   discharging; no down at 25% discharging, 60% discharging, or 10% not charging / full. The live guard was restarted
   on the new code.
3. **Nothing is deleted.** The six VMs the lab does not use stay (three are clone sources); old snapshots and backup
   files stay until Salatiel decides.
Then batch 6. Order after the backfill is unchanged: stand-in lifts, the sweep of open uncovered rows, the approval
report, the test-suite design note, the rename.

## 2026-11-20 — backfill batch 6: lessons that change how sets are written
1. **Declared writes are measured, not recalled.** After an author run, the paths the node changed during each
   exercise are listed with `find -newermt` and compared with `mutates` before the review (letsencrypt_base needed two
   rounds for undeclared writes of `certbot plugins`).
2. **Literal data is matched as a fixed string.** A count fed with substituted data (keys, hashes, tokens) uses
   `grep -F`; a regex over base64 matched nothing and let a key-absence check pass on a 0 it could not avoid
   (hashman_base, caught before any review; no other set had the pattern).
3. **A behaviour baseline is measured before a check relies on it.** user_kde_lock_screen's first draft assumed
   Plasma's default locks an idle session after five minutes; measured, a fresh session was still unlocked 450 s after
   login.
4. **Local change #13** (puppet_boot_run, policy B): `lsof` given several files exits 0 only when all are open.
5. **Plan node follows production's declaring node** where the behaviour needs it (letsencrypt_base to puppetserver).

## 2026-11-20 — HQ after batch 16, item 3: lab access through a wrapper
A command run by hand on a lab machine goes through `lab_exec.sh <host> '<command>'`: it takes the lab lock for as long
as the command runs (so it refuses while another run holds the lab, and no run starts under it), runs only on lab hosts,
passes stdin through, and inside an engine run (P8_LAB_LOCKED=1) runs without taking the lock. Cause: batch 16, a
command run on the node during a reviewer's run was cut by that run's revert. Enforcement: a project PreToolUse hook
(`hooks/lab_ssh_guard.py`) refuses a Bash command that reaches a lab host with ssh/scp/sftp/rsync outside the wrapper;
the engine's tools, which take the lock themselves, are unaffected. 21 tests; the live hook refused a direct ssh.

## 2026-11-20 — HQ after batch 16, items 1 and 2: the backup directory and loud failures
1. **Local change #14:** the backup define receives the target, so it declares the directory once for every caller
   (`ensure_resource`, owned by the cron user, 0755); filesystem_base keeps the parent. The fixture of the define's own
   set moved under the parent, as every real caller's target is. Standing composite `backup_wrappers` (filesystem_base,
   puppet_backup, sysmon_backup) compiles.
2. **Local change #15:** after tar, a non-zero status writes an ERROR line to stderr and syslog and exits with tar's
   status before retention, so old archives are kept. The checking method matters: a read-only directory cannot show
   that retention was skipped (rm could not delete either way; puppet_backup's review caught it, and backup's earlier
   PASS on the same check was corrected in the same cycle). The check now fills a one-page tmpfs over the directory,
   holding an archive old enough for retention to delete, so tar fails with the directory writable.
3. **sysmon_backup's set** no longer creates the backup directory (it masked the defect).
4. **Cutover item 7 (item 2):** check on the production master (and the monitoring server) whether archives were ever
   written.
5. **A commit deadlock** (Salatiel chose the fix): a FAIL review of a re-migrated checkpoint class blocked every commit
   (test_repo_sweep_result_is_8_verified) while the reviewer refused the uncommitted fix. The test now accepts a class
   out of the verified set only while its latest review is a recorded FAIL of its current migration; moving the FAIL
   review aside was refused as undermining oversight and was not done.

## 2026-11-21 — backfill batch 8: an uncovered row's "capability" is tried first
1. **Try before claiming.** Reviewers rejected three of my uncovered rows in batch 8 because the lab could do what the
   row said it could not: a VPN connection without a desktop session (`nmcli ... passwd-file`), read errors under a
   monitored tree (a loop-mounted image under a device-mapper error target), and onward mail relay (a peer sink with an
   address-literal recipient). From now on, before writing `lifted_by: "capability: ..."`, the advisor tries the
   capability on the node (or the peer) and writes the attempt's result as the row's evidence.
2. **Restore-and-restart behaviour** (ssl_base and similar): each notifying resource gets its own drift and its own
   agent run (`node_agent.after` as a list), so a restart is attributed to one resource.
3. **Peers powered off after a run** (HQ 2026-11-17 ruling 5) leave a domain-member node waiting on its DC: a by-hand
   command on such a node after a run needs the peer started first (measured in the batch 18 report).

## 2026-11-21 — HQ after batch 18 (batch 8 accepted)
1. **The three escalated check sets** (openvpn_domain, postfix_smtp_base, linux_policies_user) get one more round
   each, because the missing outcomes are central and lab-testable: bare-name login against the DC; relay to another
   domain through the second node; the agent run's own policy lines. After that round the set stands as it is, and
   any remaining gap is listed as an open row.
2. **openvpn_domain's Kerberos realm is a finding with one clear fix** (policy B, a local change): the realm is
   upper-cased when built; the check shows kinit working with the lowercase-tld fixture.
3. **A domain-joined node hanging on SSH while its DC is down:** no fix now; a known limitation in the approval report
   and Phase 5 backlog #11. Batch 18's two unreachable rules are recorded alongside it (#12, #13) under the batch-12
   standing rule.
4. **Continue with batch 9**, then straight on in the agreed order: stand-in lifts → sweep of open uncovered rows →
   approval report → test-suite design note. Stop for HQ review at the approval report.

## 2026-11-21 — batch 19: a Phase 1 review that fails on a missing peer; masked chain failures
1. **A Phase 1 review of a class whose harness needs a peer** (openvpn_domain needs the dc) runs only with the peer up.
   Phase 3 runs power the peer off at their end (HQ 2026-11-17 ruling 5), and the Phase 1 harness does not start it. On
   20261121T105110Z the join could not find the DC, and the review failed with faithfulness ok. The FAIL is recorded as
   it stands; the peer is reverted and started, and the review runs again. This is not a Phase 1 FAIL that stops the
   run when no migrated code failed and the reviewer's own evidence names the missing precondition. To be built: the
   Phase 1 harness starts a class's peer itself.
2. **Command chains that filter a commit's output run with `set -o pipefail`.** A trailing `grep -vE` hid a failed
   edit, and a run executed an unchanged set against a changed fixture (sysmon_integrity_node 20261121T122111Z,
   committed as an operator error).

## 2026-11-22 — HQ after batch 20 (after the laptop's power-off; the lab travels)
0. State check first: every lab VM was in a clean poweroff (the battery guard took the lab down on 2026-11-21 at 19:43
   UTC, because the advisor had left the master, node and kubuntu up after a run); HEAD = origin/main = a1cc094; no
   uncommitted change in this clone (an old stash of 2026-11-18 only). The run rule "lab down when stopping" applies
   at every stop, without exception.
1. The backfill is accepted: 90 classes with a reviewed set.
2. sysmon_mysqldump_health: fix now: restore into a scratch database with its own unique name, drop only that one,
   UNKNOWN when that cannot be done; a live database of the dump's name keeps every row. The advisor's escalation had
   recommended a different option (A: drop only what the check created, restoring under the dump's name), so per
   item 2-4's condition the class stops and HQ is shown the difference (dumps made with --databases carry their own
   CREATE DATABASE/USE lines, which a scratch name must rewrite or filter).
3. sysmon_puppet_cert_status: the certregen call replaced by a direct read of the certificates' expiry dates, the
   thresholds and output kept; checked with fixture certificates (local change #19; the escalation's option C, which
   HQ's wording matches; the advisor had recommended B, listing through puppetserver ca, a difference of how the
   certificates are found, not of substance).
4. openvpn_set_vpn_passwd_file: the password through NetworkManager's own interface so it works wherever profiles are
   stored; set twice, the VPN connecting after each (the escalation's option A: the script already set the password
   with nmcli; its profile-file existence test is what is replaced).
5. The approval report, generated from the recorded state (approval_report.py), first version now and regenerated as
   the work changes it.
6. Stand-in lifts with small lab additions: user_lock, the desktop login, a lab ACME endpoint, an extra network card on
   a gateway node, a harness mode that tolerates a running agent. The Zentyal and monitoring-server stand-ins stay and
   go to Salatiel for explicit acceptance in the report.
7. Then the sweep of open uncovered rows, the final approval report (stop for Salatiel), the test-suite design note,
   and the rename.
8. Stop at a clean point and run `lab down` when Salatiel says he is closing the laptop.
9. **Run stopped 2026-11-22 ~22:05 UTC** on a standing Phase 1 FAIL: sysmon_puppet_cert_status's review failed twice
   on the mechanical comments_preserved check after local change #19 (escalations/sysmon_puppet_cert_status.phase1.md).

## 2026-11-22 — HQ rulings after the run stopped
1. **sysmon_mysqldump_health:** the scratch-name design is withdrawn; the advisor's design, with conditions. Before any
   restore, list the databases the dump would create or use. If any of them already exists, do not restore: validate
   the file only, and say in the output that the restore test was skipped because the database exists. When it does
   restore, it drops only databases it created in that run. Checks: a live database with the dump's name keeps every
   row; a dump whose database is absent gets the full restore test and leaves nothing behind.
2. **sysmon_puppet_cert_status: option B.** A comment describing replaced behaviour is not kept verbatim. The mechanical
   comments_preserved check accepts a changed or removed upstream comment line only when the class's local-change row
   lists that exact line and its replacement; anything not listed still fails. The reviewer confirms each listed line is
   justified by the change. A tool change with tests, then one more review of this class.
3. **Lab down at pauses is enforced mechanically,** not by memory: a hook that runs when the advisor's turn ends brings
   the lab down unless a run holds the lock. Tested.
4. **Then continue:** item 4 (openvpn_set_vpn_passwd_file), the stand-in lifts, the sweep, the final approval report
   (stop for Salatiel), the test-suite design note, the rename.

## 2026-11-23 — HQ rulings after the stop: carried out
1. **Ruling 3, lab down at pauses (lab_idle_down.sh, 5066ec7).** A Stop hook (`.claude/settings.json`) runs
   `lab_idle_down.sh arm` when the advisor's turn ends; a UserPromptSubmit hook runs `disarm`. Armed, a detached watcher
   runs `lab_power.sh down` once the lab has been idle for 600 s: no lab lock holder and no lab tool process
   (phase3.py run, test_class.sh, revert_node.sh, record_green.sh, review_class.py, codex_migrate_class, lab_exec.sh,
   lab_power.sh, snapshot_master.sh, lab_vm.sh). A lock holder or lab process resets the idle clock; with no lab VM
   running it does nothing. The watcher does not act at the instant a turn ends, because turns end while background
   reviewer or harness runs still use the lab between two lock-holding steps. Tests on the fake lab (8). The hook fired
   in this session (~/.cache/infra_populi/idle_down.log). Consequence for the advisor: a turn that ends while waiting on
   a long laptop-only step (a full-suite commit) may let the lab go down; a GREEN stamp then needs a new harness run.
2. **The fake lab writes its world atomically** (conftest.py, both writers): a stub read a half-written world file
   under load, the sleep-guard flake noted in batch 20. Two test races in the new idle-down tests were mine and are
   fixed (135d01c, and the 'armed' assertion with a 1 s idle time).
3. **Ruling 2 done:** review_class.py `comments_preserved` accepts a listed comment change (559979d, 3 tests; reviewer.md
   exception). Row #19 lists `# This runs the command and collects the output` -> (removed) and the dictionaries
   comment -> its replacement; the moved copy of the first line was removed from the file, as it described the certregen
   call. Re-recorded (c8c6ed4), after-run ALL_PASS (ad49928), Phase 1 PASS (30e8bc4), Phase 3 PASS (fb5ce96);
   escalations/sysmon_puppet_cert_status.phase1.md closed.
4. **Ruling 1 done as local change #20** (287a517): the dump's databases (header, CREATE DATABASE, USE) are listed before
   any restore; an existing one means file validation only (a complete mysqldump ends with "-- Dump completed") and an
   OK line saying the restore test was skipped; a restore drops only the databases this run created (CREATED, reset
   after each drop). Before: the live database was dropped by the old error path (20261122T233809Z). After: ALL_PASS
   (20261122T234851Z). Phase 1 PASS (01e4f81). The set's Phase 3 review FAILed on purpose (the create-failure path after
   #20 has no row); the set had used its two correction rounds, so it is escalated with a one-check fix
   (escalations/sysmon_mysqldump_health.behaviour.md) and the run continued.
5. **Item 4 (openvpn_set_vpn_passwd_file), local change #21:** VPN1 connects to a real OpenVPN server on the ubuntu2 peer
   that accepts one password at a time, switched between the two runs. Before (20261123T000353Z): run 1 connects; run 2
   leaves the old password and the connection fails (up rc 4). After (20261123T002025Z): run 2 sets the new password and
   VPN1 connects with it. Phase 1 PASS (the first review failed on records only: a '|' inside row #21's change cell
   shifted the row parser's cells; the row was reworded) and Phase 3 PASS; the behaviour escalation is fixed.
6. **Commits with a path argument** (`git commit -- <path>`) run the pre-commit hook with GIT_INDEX_FILE set to a
   temporary index, which the tests' own git calls inherit; such commits are not used. Noted for the test-suite design
   note, with a row-shape check for local_changes.md.

## 2026-11-23 — item 6 started; the run stops on user_lock's Phase 1 FAIL
1. **user_lock's stand-in lifted** (7175bca): on the master-role node, hashman itself creates the user (node fixture
   hashman_user_via_hashman, listed as a test asset); the set matches hashman's own entries and authenticates with
   hashman's initial password; ALL_PASS (14522e1).
2. **Operator error, recorded:** to drop the tracker's mock-apply marker I re-ran record_green without a content change,
   which made a `P8: migrate` commit touching only the tracker (3731d97). The reviewer's provenance check fails on it
   (review 20261123T011346Z). Marker-only changes belong to `record_green.sh --fix`; record_green does not refuse the
   other path today.
3. **Run stopped ~01:15 UTC** on that standing Phase 1 FAIL (escalations/user_lock.phase1.md, options A/B). Not started:
   the other stand-in lifts (a draft node fixture for mount_shares_desktop's real first GNOME login is in the advisor's
   scratch, not committed), the sweep, the final report.

## 2026-11-23 — HQ rulings on the user_lock stop
1. **user_lock: option A, kept narrow.** record_green refuses a migrate commit that changes no class file and points to
   `--fix`. The provenance check ignores such an empty migrate commit only when an earlier migrate commit for the class
   did change its files, and the verdict lists the ignored commit. Tests for both, then one more review.
2. **sysmon_mysqldump_health's set:** a third correction round is approved for the one missing check (the
   create-failure path).
3. **Scratch is not storage:** /tmp does not survive a reboot, and the laptop is shut down for travel. The test-suite
   notes and the desktop-login draft are committed as drafts (`.codex_state/drafts/`); anything worth keeping lives in
   the repo from now on.
4. **Continue:** the remaining stand-in lifts, the sweep, the final approval report (stop for Salatiel), the test-suite
   design note, the rename. When Salatiel says he is closing the laptop: stop at a clean point, commit, push, lab down.

## 2026-11-23 — HQ rulings on the user_lock stop carried out; item 6 stand-in lifts; the run stops before the sweep
1. **Ruling 1** (a3df1b6): record_green refuses a migrate commit that changes no class file and points to --fix;
   provenance ignores such a commit only after an earlier migrate commit that changed the class's files, and lists it
   (`ignored_migrate_commits`). user_lock Phase 1 PASS (20261123T014847Z; the review before it failed on fixtures=error
   only, the master-role node being powered off: `lab_power.sh up` starts the master and the default node only).
2. **Ruling 2:** sysmon_mysqldump_health's third round (the create-failure check), Phase 3 PASS; escalation closed.
3. **Ruling 3:** drafts live in `.codex_state/drafts/` (the test-suite notes; the desktop-login fixture, since used).
4. **Item 6 stand-in lifts:**
   - user_lock: on the master-role node hashman itself creates the user (test-asset fixture hashman_user_via_hashman).
     Phase 1 PASS; its set's Phase 3 review failed on purpose (hashman expires a new user, so the Samba hash carries
     '!' before the lock): escalated past the correction cap with the one-line fixture fix (escalations/user_lock.checkset.md);
   - mount_shares_desktop: a real first GNOME login (test-asset fixture p8test_desktop_login) creates ~/Desktop; both
     reviews PASS;
   - node_base_desktop, node_base_domain_desktop: the harness tolerates a running agent daemon (6e007df: runs wait
     for the agent lock; a between-runs gate fails a daemon run that logged a resource event or an error, read from
     puppet.service's journal, since the master names stored reports by the minute and the harness's own runs log
     from the ssh session's scope); the agent-daemon outcome is now a check; both reviews PASS for both classes;
   - letsencrypt_certificate (a lab ACME endpoint) and openvpn_server/network_vpn (an extra NIC on a gateway node):
     escalated, each needing a design choice, the second a new VM (escalations/*.standin.md).
   - Marker-only re-records now go through `record_green.sh --fix`.
5. **The run stops before the sweep** (~04:45 UTC): its approach is a design choice affecting 34 sets
   (escalations/sweep.md: record the real gaps, or build two runner capabilities first). The lab is down.

## 2026-11-23 — HQ rulings on the sweep and the escalated lifts
1. **Sweep: option B, done once** (the 34 sets re-run and re-reviewed a single time).
   a. Build both runner capabilities first, with tests: more than one params fixture per set, and running a set's
      checks on a second node kind.
   b. RedHat rows become checks on rhel9.
   c. Parameter variants: read the fleet data for which variants production uses, recording only the variant and a
      count, never a value. Variants production uses become checks. The others become rows marked as an accepted gap,
      which the validator allows only for a variant no production node uses, and which the approval report lists for
      Salatiel's acceptance.
   d. One-off rows: a check where the lab can test it; otherwise a row naming what is missing, with evidence.
2. **user_lock's check set:** a third round is approved for the fixture fix (unexpire after unlock).
3. **letsencrypt_certificate:** no mock DNS API; it stays a stand-in for Salatiel's acceptance. A real lift needs a
   sandbox DNS zone and API token against Let's Encrypt staging. Documentation list, cutover row 8: prove issuance on
   staging before the new master takes over renewals.
4. **openvpn_server and network_vpn:** no new gateway VM now; they stay stand-ins for Salatiel's acceptance.
   Documentation list, cutover row 9: the first VPN gateway is migrated as a recreated test gateway before any live one.
5. **Then** the final approval report (stop for Salatiel), the test-suite design note, and the rename.

## 2026-11-24 — HQ rulings for the resume
Verbatim (received as a paste on 2026-11-24):
0. Before anything else: run lab up and measure the node's and the master's clock rate against the laptop again. If
   the drift is gone, release node_base's review. If it is still there, stop and report the measurements; do not run
   time-based checks on a drifting clock. Either way, list the sweep runs made on the drifting boot whose expectations
   depend on a duration, and re-run those.
1. rsyslog_client: remove the rejected setting, as you recommend. Checks: rsyslog starts with no config error on
   Ubuntu 24.04 and RHEL 9.5, and auth.log lines are still forwarded. Local change; add "restore the setting when the
   oldest supported rsyslog accepts it" to the Phase 5 backlog and the 26.04 pass.
2. rsyslog TLS files (cutover row 10): fix the default now; do not leave it to the cutover. Without an override, the
   class uses the agent's real SSL directory on current agents; the override parameter stays. Check on a node with no
   override that the TLS files are copied and a log line reaches the peer over TLS. Keep the cutover row as a reminder
   for Salatiel to read whether production sets the override.
3. Backlog #14: accepted as recorded.
4. Correction rounds: confirmed. The sweep counts its rounds from 1, with the same caps as before (three for classes
   production uses, two for the rest).
5. Then as you listed: sysmon_base's re-review, the 18 remaining reviews, the DESIGN_DECISIONS entry, the filesystem_apt
   local change, and the final approval report, where you stop for Salatiel.

Ruling 0 carried out the same day: the drift remains (node 1.0245, master 1.0249 over 300 s), and the laptop had not
been cold-booted (up since 2026-11-22 21:17:07, the boot of the 2026-11-23 measurements). The run stopped there, the lab
down; measurements and the list of duration-dependent sweep runs in escalations/lab-clock.md. Rulings 1-5 wait.


## 2026-11-24 — After the cold boot: the clocks still drift (0.465% slow); HQ rulings 1 and 2 carried out
HQ after the laptop's cold boot (verbatim): "If all keep time: proceed with rulings 1–5, and re-run the
duration-dependent checks on your list, by author and reviewer. If the drift is still there: proceed only with rulings
1 and 2 and the reviews that involve no durations, hold everything on your list, and report the measurements so HQ can
look at the VirtualBox side."
- **Clock, corrected:** the uptime method (±0.6%) first showed every VM keeping time (d9480ba). node_base's
  ntp-keeps-the-time then failed again. An SNTP measurement of CLOCK_MONOTONIC_RAW over 900 s found that the node,
  master, rhel9 and ubuntu2 run 4645-4659 ppm slow (bounds about ±220 ppm), beyond the 500 ppm that ntpd and timesyncd
  correct; gnome runs at 0 ppm. Of the VM settings compared, only gnome's differ: paravirt provider hyperv and EFI.
  The second branch therefore applies: the duration-dependent reviews are held, and escalations/lab-clock.md is
  reopened for HQ. Rule kept from this: a clock "keeps time" only at the resolution of its measurement, and a check
  that needs ntpd's 500 ppm needs a method that resolves it.
- **Re-runs made before the correction** (author, committed): gnome_lock_screen, firewall_secure, docker_container and
  sync ALL_PASS; firewall_secure_extra only its ruled RST finding. They ran on the drifting clock; HQ decides whether
  they stand. The rhel variants of node_base, ssh_secure and sysmon_base were ENVIRONMENT_FAILED.
- **Tool:** revert_node's dnf metadata timeout is 600 s (09afd07; was 300). A restore discards dnf's cache, and the
  current uplink needed 4 min 02 s, and 342 s in a revert, for BaseOS's 173 MB.
- **Ruling 2 (local change #23):** rsyslog_base's default ssldir is the AIO agent's /etc/puppetlabs/puppet/ssl when
  the aio_agent_version fact is present, and /var/lib/puppet/ssl otherwise. The override still wins. The lab Hiera
  binding is removed (48b06e9; master_fixtures reported CHANGED hiera, so per the script a new master snapshot is
  HQ's). Checks: base run with no override, rhel and override variants ALL_PASS. Reviews PASS (Phase 1 after a records
  round: review_class reads a row's check ids before the first colon, split at "and" and commas, so a parenthesis
  with a comma breaks it). Cutover row 10 stays.
- **Ruling 1 (local change #22):** deleteStateOnFileMove removed. Ubuntu 24.04 starts rsyslog with no configuration
  error, and an auth.log line reaches the TLS peer through imfile (the same run is ruling 2's end-to-end check with no
  override). Phase 5 backlog #15. Correction to the escalation's premise: on rhel9 the class installs
  rsyslog-gnutls, which upgrades rsyslog to 8.2604.0-4.el9_9.1, and that version accepts the parameter; only Ubuntu
  24.04's 8.2312 rejects it. Reviews PASS.
- **Reviews with no durations:** ssl_base PASS. ssl_nginx_domain's review was stopped by the sleep guard: the laptop
  was on battery at 24%, and the guard ran `lab_power.sh down` and aborted the run, leaving no verdict. The run
  resumes on mains power with ssl_nginx_domain, then nginx_base, backup_rsnapshot, user_base, user, openvpn_server,
  network_vpn, postfix_smtp_node, hashman_web, nginx_frontend and nginx_frontend_domain.

## 2026-11-24 — HQ rulings (resume on mains power), and the hyperv result
Verbatim:
1. First, fix the test isolation (tests never read the laptop's real battery or act on the real lab) and commit the
   DESIGN_DECISIONS entry.
2. Clock drift: follow your lead with an experiment on ubuntu2, which lab_vm.sh may modify. With it powered off, set its
   paravirtualization provider to hyperv, as gnome has; boot and measure its rate against NTP over 900 s. If the drift
   remains, try provider none and measure again. Also compare the `virtual` and `is_virtual` facts between gnome and
   the node, since no class may see a different platform after the change. Report the numbers.
   - If a provider fixes it: apply it to rhel9 and ubuntu2 yourself and take new baselines. Write out the exact
     commands for the master and the node for Salatiel, plus the new node baseline and master snapshot that follow,
     and stop for him.
   - If neither fixes it: stop and report.
3. Runs made on a drifting clock do not count as evidence, whatever their result, except gnome_lock_screen's, which ran
   on the one VM that keeps time. Re-run the rest of your duration list after the fix.
4. The reviews with no durations may continue (ssl_nginx_domain onward) whenever the experiment is not using the lab.
5. rhel9 on this uplink: before a block of rhel9 runs, refresh its baseline once so the reverts inside that block
   download almost nothing, and do the block within the metadata's 24 hours.
6. Master snapshot: take it with snapshot_master.sh after the clock change is settled, so one snapshot covers both
   changes.
7. Noted: only Ubuntu 24.04 rejects the rsyslog setting. The removal stands.

Carried out the same day:
- **Ruling 1:** feb9cd0 (the autouse isolation stubs the power supply and moves the battery log, guard pid and idle
  state into each test's tmp; full suite 750 passed) and c1a777c.
- **Ruling 2:** hyperv fixes the drift. ubuntu2 -11 ppm and rhel9 +7 ppm, against 4645 and 4656 ppm slow under kvm;
  gnome -3 ppm and the kvm node -4654 ppm in the same window. Facts unchanged (`virtual` virtualbox, `is_virtual`
  true). New baselines P8LAB_UBUNTU2_BASELINE_v3 and P8LAB_RHEL9_BASELINE_v3 (2ec8724), verified by real reverts.
  Salatiel's steps for the master and the node, with node baseline v5 and master snapshot v10 to follow, are in
  escalations/lab-clock.md (3c4f3e3). The run stops for him there; the lab is down (his step 1).
- **Ruling 3:** the runs made on the drifting clock no longer count as evidence: the 2026-11-24 author re-runs of
  firewall_secure, firewall_secure_extra, docker_container and sync, and every earlier sweep run of the duration list.
  gnome_lock_screen's 2026-11-24 run (on gnome) counts.
- **Ruling 4:** not used in this stretch, since the experiment held the lab the whole time. ssl_nginx_domain is next.
- **Not ruled, noted:** p8lab-kubuntu, p8lab-dc and p8lab-puppetserver still use kvm and were not measured.

## 2026-11-25 — The lab's paravirt provider is hyperv, enforced (HQ 2026-11-24 "experiment accepted")
Verbatim:
"HQ: experiment accepted; hyperv is the lab's paravirtualization provider from now on.
1. Salatiel has run steps 2 and 3 (node restored to v4, set to hyperv, P8NODE_BASELINE_GREEN_v5 taken without booting;
   master set to hyperv while powered off). Proceed with your steps 4 and 5.
2. Switch p8lab-kubuntu, p8lab-dc and p8lab-puppetserver the same way, with new baselines, and measure each once.
3. Make it stick: lab_vm.sh sets the provider on every new clone, the inventory records it, and a revert fails if a VM
   is not on it. Tests. Record the cause and the fix in DESIGN_DECISIONS.
4. Then, in this order: the reviews with no durations; the duration list re-run by author and reviewer; the rhel9 block
   within its baseline's 24 hours; the filesystem_apt local change; the final approval report, where you stop for
   Salatiel."

- **Cause:** under VirtualBox's `default` paravirt provider (effective kvm on this Linux host) every lab guest's clock
  ran at a rate ntpd and timesyncd could not follow: 2.45% fast before the laptop's cold boot, 4645-4659 ppm slow after
  it (SNTP over 900 s: master, node, rhel9, ubuntu2; escalations/lab-clock.md). The provider was the one
  difference: gnome, created with hyperv, kept time in every window (-3 and -0 ppm). node_base's
  `ntp-keeps-the-time` failed on it, and every timed run on those clocks (sweep durations, timeouts) measured a wrong
  rate.
- **Fix:** every lab VM runs on paravirt provider hyperv. Measured over 900 s: ubuntu2 -11 ppm, rhel9 +7 ppm (2ec8724);
  on 2026-11-25 (on AC, 03:53-04:09Z) the master -4, the node -5, kubuntu -8, dc -5 and puppetserver -1 ppm, each
  within its bound of about +-200 to 220 ppm. The facts classes read are unchanged (`virtual` virtualbox,
  `is_virtual` true).
- **Baselines:** the provider is a VM setting a snapshot carries, so a restore of an older snapshot brings kvm back.
  New baselines carry it: P8NODE_BASELINE_GREEN_v5 (Salatiel, 4735218), P8LAB_UBUNTU2_BASELINE_v3,
  P8LAB_RHEL9_BASELINE_v3, P8LAB_KUBUNTU_BASELINE_v2, P8LAB_DC_BASELINE_v2, P8LAB_PUPPETSERVER_BASELINE_v2; the master
  was set while powered off (Salatiel) and P8MASTER_BASELINE_GREEN_v10 follows (ruling 6 of the resume).
- **Enforcement (8d5ca2f):** nodes.yml `paravirt_provider: hyperv` is the single source (nodes.py validates it is a
  real provider other than `default`, prints it with `provider`, exports NODE_PARAVIRT). lab_vm.sh sets it on every
  clone and refuses another on modify. revert_node.sh reads the restored VM's effective provider and fails before boot
  if it differs. lab_power.sh up refuses a master that is not on it (its settings are Salatiel's). Tests for each.
- **Step 5's finer test:** node_base's `ntp-keeps-the-time` passes (results/node_base/20261125T041119Z-author). That
  run's rhel variant did not apply (a subscription-manager guard exceeded Puppet's exec timeout; 10.6 s by hand) and is
  re-run in the rhel9 block.
- **rhel9 metadata, measured:** after a restore dnf treats every repository as expired and checks each one upstream.
  The 2026-11-25 reverts downloaded 138 MB in 155 s, 9 h after the v3 refresh: AppStream had new metadata (published
  2026-11-24 21:08 WET), while BaseOS and openvox8 were reused. A refresh therefore saves the download only until Red
  Hat publishes AppStream again; the rhel9 block refreshes its baseline just before it starts (HQ ruling 5).
- **Measurement note:** two five-VM runs lost their results because they were written to /dev/shm. The VMs run
  systemd-logind's default RemoveIPC=yes, which deletes a user's /dev/shm files when the user's last process exits:
  here the measurement itself, at the moment it wrote them (/dev/shm's mtime changed at 03:39:07-23Z on all five, the
  runs' end; no VM rebooted). The 2026-11-24 20:33Z run was also cut by the sleep guard (lab down at 01:42Z, battery
  24%). Results now go to /var/tmp.

## 2026-11-26 — HQ 2026-11-24 item 4 carried out; the final approval report; stopped for Salatiel
- **4a, reviews with no durations:** the 11 sets pass: ssl_nginx_domain, nginx_base, backup_rsnapshot, user_base,
  user, openvpn_server (its ruled compression finding reproduced), network_vpn, postfix_smtp_node, hashman_web,
  nginx_frontend, nginx_frontend_domain. Eight needed corrections of the swept set, none past round 2. Every correction
  was a purpose gap the reviewer found: an outcome claimed but tested as rule text, a row left uncovered for a reason
  the lab disproves, or a parameter production sets with no check. The lab Hiera fixture gives p8lab-rhel9 non-default
  postfix_smtp_node per-node values (3a02162).
- **4b, the duration list on hyperv clocks:** node_base, ssh_secure, firewall_secure, firewall_secure_extra (its ruled
  RST finding reproduced), docker_container (correction 3, the last), sync and sysmon_base re-run by author and
  reviewer, all PASS; gnome_lock_screen's 2026-11-24 run counted and its review PASS. Variant runs have no peer, so
  the firewall sets' strict and anti-DDoS variants are tested from a network namespace on the node behind a veth pair
  (RFC 5737 addresses).
- **4c, the rhel9 block:** no block was left. It held the three rhel variants that failed on the environment (node_base,
  ssh_secure, sysmon_base), and all three re-ran in 4b: node_base and ssh_secure inside v3's 24 h window,
  sysmon_base's author and reviewer runs after it (from about 21:05Z, past 19:27Z; its revert downloaded 327668172
  bytes in 334.857 s). A refresh just before them would have been the ruling's order; no baseline was refreshed.
- **4d, filesystem_apt:** local change #24 (a custom apt_surface_list joined with spaces), Phase 1 and Phase 3 PASS.
  The first Phase 1 review failed on records only: review_class.py read a local change's after-check from the base
  run, so a check that runs in a variant could not be found; fixed with tests (66e621d). A new item, escalated (OPEN,
  environment): the dist-upgrade check's action cannot finish within phase3's 600 s cap on this uplink (986 MB
  pending on the node baseline); options in escalations/filesystem_apt.behaviour.md.
- **Measured on the way:** dnf after a rhel9 restore treats every repository as expired and re-downloads what Red Hat
  has published since the refresh (138 MB at 9 h, 327 MB at 26 h).
- **Reviewers' minor notes, not gaps (for the report's reader):** backup_rsnapshot's daily-backup-executes mutates text
  omits that rsnapshot creates its snapshot_root; user_base's locked variant does not assert group p8testuser still
  exists when the primary group is users; nginx_frontend's server_monitoring_create default (no monitoring server) is
  untested, production keeps it; firewall_secure's ssh_port is untested at a non-default value, no production
  statement sets it.
- **Housekeeping:** escalations/sweep.md marked closed (ruled 2026-11-23, carried out).
- **4e:** approval_report.md regenerated: 90 done (89 reviewer-verified, 1 owner-validated), behaviour 86 pass,
  3 findings (filesystem_apt's timeout, open for HQ; firewall_secure_extra's RST limit and openvpn_server's compression,
  both ruled), 1 deferred (letsencrypt_certificate, a stand-in); 84 open rows in 61 classes; 24 local changes in 19
  classes; 7 stand-ins. The run stops here for Salatiel; the lab is down.

## 2026-11-26 — Test-suite design note written (ruling F); stopped for HQ review
Salatiel, at the approval-report stop: write the test-suite design note now, Phase 1 not yet approved; the rename
stays untouched. The note is `.codex_state/test_suite_design.md` (a proposal, nothing built): the suite moves to
`spec/behaviour/` with its own runner (any disposable node over ssh, a provider hook for fresh nodes, agent or local
apply, the gate moved in), probes read runner variables instead of lab names (which also shrinks the rename), JUnit
kept, and the engine keeps its lab provider, records and baseline checks around the public runner after a sameness
proof. Five open questions for HQ (location, committing fake-only fixtures, local apply, names, derived_from in
public). The drafted observations moved into its appendix. The run stops for HQ review; the lab is down.

## 2026-11-26 — HQ review of design note F: approved, with rulings
Verbatim:
"HQ review of design note F: approved, with these rulings.
1. Location: spec/behaviour/. spec/acceptance/ is where the Puppet community's standard acceptance tools look, and this
   suite is not one of them.
2. Fixtures: fake-only params fixtures may be committed inside the suite. This is the one exception to "never commit
   params", enforced by the fake-values check in the pre-commit hook. Real or lab-specific values stay outside git.
3. puppet apply: allowed as the public default only for sets shown to give the same result as the agent path. Measure
   every set. A set that needs a Puppet server (file mounts, server facts, anything apply cannot do) declares it and is
   skipped in apply mode with a clear message. The server path stays the engine's gate of record.
4. Names: runner variables get neutral names with no P8_ prefix. The suite is built under the current module name and
   renamed with everything else by the rename script.
5. derived_from: becomes optional provenance that the public validator ignores. The engine keeps validating it against
   the pinned baseline while the migration lasts. The public validator requires the purpose and outcomes table.
6. Moving the sets must be provably neutral: for every set whose probes change (addresses, hostnames and paths becoming
   variables), the probes rendered with the lab's values must be byte-identical to the old ones. Build that check; sets
   that pass it are not stale.
7. The engine's switch to the public runner needs a sample that covers every probe helper, every node kind, a
   second-node set, a mutating probe, the desktop session and the browser flow.
8. The guide is written for an outside contributor: nothing in spec/behaviour/ refers to .codex_state, the advisor or
   Codex.
9. filesystem_apt timeout: option C now. Option A (a fresh node baseline) is done just before the rename's full
   re-verification, so that pass runs on an up-to-date machine.
10. Order: build the suite now (items 1–8), then stop for HQ with the neutrality and sample results. The rename follows,
    and its full re-verification runs on the public runner. Phase 1 approval is separate and stays with Salatiel."

## 2026-11-26 — Behaviour suite, steps 1-4: the sets moved to spec/behaviour/checks, neutrally (HQ review of design note F)
- **Built so far:** spec/behaviour/lib (placeholders {{NAME}}, {{NAME|re}}, {{NAME+N}}, {{NAME:arg}}; probe rules and
  verdicts; the public validator: purpose and outcomes required, derived_from ignored as provenance, ruling 5),
  spec/behaviour/kinds.yml (each node kind by OS, capabilities and the tooling it provides), suite_check.py in the
  pre-commit hook (no lab value, no engine reference, fake-only params fixtures; rulings 2 and 8), and the engine's
  converter behaviour_move.py (57e3f2e, 60b6ab6, 8c48593).
- **The move (ruling 6):** all 90 sets now live in spec/behaviour/checks as templates. Their machines and site paths are
  placeholders by role in what runs (NODE_NAME, NODE_ADDR, PEER_ADDR, SERVER_NAME, CONTROLLER_ADDR, LOCALDIR, ...)
  and by kind in prose ({{NODE:rhel9}}); the runner variable P8_PEER_ADDR is PEER_ADDR (ruling 4). Each set gained an
  `apply:` block: the catalog the harness builds for it from the plan, per OS family, with its node kind, node fixture
  and expected run-2 events, so a runner without the plan can build it. The neutrality check renders each template with
  the lab's values (each run's own node and peer) and names PEER_ADDR back: all 90 equal their old files, every string
  byte for byte, with no lab value left. `behaviour_move.py verify` re-proves it against the old files as git holds
  them, and a test runs it. moved.json ties each new file to its old identity, so phase3.reviewed_as_is keeps every
  review valid: behaviour state unchanged (86 pass, 3 finding, 1 deferred), approval_report.md regenerates identical.
- **The engine reads the public sets:** phase3.load_set renders the template with the lab's values (behaviour_move.
  lab_view) and leaves the `apply` block to the harness; it runs exactly the old probes. Results and reviews stay in
  .codex_state/checks/{results,reviews}; each set's comments (its authoring history) moved to
  .codex_state/checks/notes/<class>.md. CLAUDE.md, the migrate-next skill and the reviewer agent name the new path.
- **Ruling 8, as read:** the sets no longer name .codex_state, the advisor, Codex, or an engine file. The prose cites the
  engine's records and tools (phase3.py 56 times, the fleet usage count, nodes.yml, escalation files, ...) as
  {{SITE:<record>}} placeholders, which render back exactly for the engine and which a runner never needs. The generic
  word "plan" and references to HQ rulings stay in the prose. Reported to HQ at the stop.
- **Caught on the way:** a lab name or address written escaped (`\Apuppet8node`, `192\.168\.56\.20` inside a probe's
  grep pattern) first escaped the converter; the leftover check and suite_check.py found both, and the converter now
  handles escaped forms in every executed string.

## 2026-11-27 — Behaviour suite, steps 5-8: fixtures, the public runner, the engine's switch sample, local apply measured (HQ review of design note F)
- **Fixtures (rulings 2, 6):** the lab's params directory stays the harness's source of record; the suite's copies in
  spec/behaviour/fixtures are derived from it (fixtures_move.py) and proven neutral like the sets: each template,
  rendered with the lab's values of every run that uses it, equals the local file. A lab value becomes a role
  placeholder only where the role names the same machine in every such run. Files that are not plainly fake stay
  operator-supplied (`--params`). Node fixtures move with their Puppet code neutral; their comments (the engine's
  history) stay with the engine's copy.
- **The public runner (rulings 3, 7, 8):** spec/behaviour/run. Fresh nodes from a provider command, or given once and
  marked; agent, local (`puppet apply`) or command apply modes; JSON and JUnit. Its gate is gate v2's plus two rules:
  a run that logged an `Error:` line fails (Puppet exits 0 when an exec's check times out: escalation
  harness-gate-run2-errors.md), and changed resources are read from Puppet's last-run report, so a change no log line
  shows still counts (seen: run 2 exiting 2 with no change line under local apply).
- **The manifest is the harness's:** manifest_compare.py builds both, offline, for every run; 146 of 146 equal. It found
  three converter faults first (a base define's title, the plan's per-OS-family bases, params lookup precedence), and the
  measurement found a fourth (the expected run-2 events of the whole catalog, as the harness allows them).
- **The engine's switch (ruling 7):** behaviour_lab.py gives the public runner the lab: a fresh node is a reverted one
  under the lab lock; the apply hook runs the gate-v2 harness only after checking it renders exactly the runner's
  manifest, so the engine's gate of record is unchanged. Sample: 7 sets, 9 runs, identical to the engine check for check.
- **Local apply (ruling 3):** measured on every set (behaviour_sample.py measure). A set local apply cannot run declares
  `apply.requires: [server]` with `requires_why` (the validator requires the reason). Its engine view is unchanged, and a
  moved set's identity is also its engine view (phase3.view_sha, recorded in moved.json), so such a declaration keeps the
  set's reviews. Result: 89 sets measured, 65 identical to the engine check for check; 23 declare a server, each one
  differing under local apply for the reason it gives (16 take files from puppet:///extra_files, 7 depend on the agent:
  its cached catalog, its state files, its daemon, $server_facts, or another machine using the node as its server);
  filesystem_yum is unmeasured (its full dnf update exceeds the check's 600 s on the slow uplink). A set is declared
  only on a measured difference with its cause read from the run, never on a guess.
- **Lab uplink:** from about 09:30 the laptop's uplink fell to 9.5 kB/s (later 100-180 kB/s). Reverts refresh apt and
  dnf, so at the low point every run failed in its revert; at 100-180 kB/s they work. A degraded uplink is an
  environment failure: the run is repeated, never judged.
- **Master outage (2026-11-26/27):** the sleep guard powered the master off cleanly at 19:47 (battery at the power
  cut); a later boot was cut when the laptop's battery died, which left an ext4 error the initramfs fsck would not
  repair. Salatiel ran the manual fsck; no restore. The damaged directory was /tmp/snap-private-tmp; five orphans in
  /lost+found; packages, CA and modules verified. The laptop's /tmp went with the reboot: anything a run needs after a
  reboot belongs in the repo or the state directory, not in /tmp.

## 2026-11-27 — Correction to the entry above (behaviour suite, steps 5-8)
- The split of the 23 sets that declare a server was miscounted: 15 take files from puppet:///extra_files (not 16) and
  8 depend on the agent or the server otherwise (not 7: dns_client, firewall_addon_hosting, hashman_base,
  node_base_desktop, node_base_domain_desktop, packages_base, rsyslog_base, sysmon_base). Counted from the sets'
  requires_why; the totals (89 measured, 65 identical, 23 declared, 1 unmeasured) stand.

## 2026-11-27 — HQ review of the behaviour suite: accepted, with rulings (the rename may start)
Verbatim:
"HQ review of the behaviour suite: accepted. Both proofs hold (90 of 90 sets neutral; the sample identical on the new
runner). The rename may start. Rulings:
1. Logged errors (your escalation): option A. A run that logs an error line fails, in gate v2 as in the public runner.
   Gate v2 also counts changes from Puppet's last-run report. The two gates must never differ; after the switch below
   they are one code path.
2. Engine switch: the engine now runs behaviour checks through the public runner, with the lab as its provider.
3. Wording (your item 2): accepted for now. Add to the documentation list: before the module is promoted, one pass over
   spec/behaviour replaces internal terms such as "HQ ruling" with neutral ones.
4. Lab power: the lab runs on mains only. `lab up` refuses on battery, and when mains is lost the guard brings the lab
   down after a two-minute grace, whatever the charge. Tests. (Salatiel may veto this line.)
5. Scratch: the turn-end hook lists scratch files newer than the last commit; commit them to drafts or discard them
   before you stop.
6. Slow uplink: build a small package cache as its own never-reverted lab VM (not on the master, whose disk is too
   small), and point the Ubuntu nodes' apt at it with a direct fallback. Verify on three package-heavy classes that
   results are unchanged. If any class behaves differently because of the proxy, drop it and report.
7. Fresh node baseline (option A), taken once, including the cache setting if item 6 holds. Hand Salatiel any command
   your settings do not allow.
8. Rename, per the approved plan and its amendments: tag `pre-rename` first (Phase 1 approval is still Salatiel's, so
   not phase1-complete); every variant, including paths and unit and instance names; rename_check over the whole tree;
   the inventory of node-visible names for the cutover; consumer conversion scripts tested on synthetic fixtures only.
9. Re-verification after the rename, on the public runner, every class on its node kinds: Phase 1 harness and the
   behaviour set. The reviewer confirms for every class that its diff is rename-only and its runs are green, and
   independently re-runs every class whose node-visible names changed plus a random 15% of the rest.
10. Failures are escalated per class and the pass continues. Stop for HQ when the pass is complete."
- Item 3's documentation-list entry: before the module is promoted, one pass over spec/behaviour replaces internal
  terms ("HQ ruling", "the plan", batch references) with neutral ones.
- Salatiel passed the rulings on without vetoing item 4.
