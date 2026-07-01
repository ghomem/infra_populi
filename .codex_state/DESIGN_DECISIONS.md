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
