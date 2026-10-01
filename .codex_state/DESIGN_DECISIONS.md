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
