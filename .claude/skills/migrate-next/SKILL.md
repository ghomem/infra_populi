---
name: migrate-next
description: Run the Phase 1 migration loop autonomously for a budget of classes. Usage /migrate-next 5, /migrate-next until 5 done, /migrate-next until 8 resolved (resolved = done + blocked-with-evidence). Picks the next pending class from the order file, runs hazard checks, reverts the node, invokes Codex through the wrapper, verifies with the reviewer subagent, records, and continues. Escalates by file and keeps going.
---
Budget: parse the argument. `N` means N classes reach reviewer-PASS. `until N done` same. `until N resolved`
counts PASS + blocked-with-evidence. Stop exactly at budget, or when no PENDING non-blocked class remains.

PREFLIGHT (once): read CLAUDE.md and the three most recent DESIGN_DECISIONS.md entries. `git status`
clean and HEAD == origin/main (fix by push if only ahead; STOP if diverged). `ssh puppet8master` reachable
and 8140 listening. Regenerate the order file. Create `.codex_state/logs/` if missing.
`.git/hooks/pre-commit` must be a symlink to `../../.codex_state/tools/pre-commit` (install it if missing).

FOR EACH CLASS:
1. PICK: next PENDING row in migration_order.md that is not in blocked.txt. Read its plan row
   (resource_type, internal_deps, required_base, required_external, self_contained) and
   `manifests/<class>.pp`. If deps are not DONE, the order file is wrong — investigate, do not skip silently.
2. HAZARDS: first run `.codex_state/tools/pregate.sh <class>` (drift, parse, lint, templates, static
   hazards 1/2/5/6/9 — it prints its tool versions); every FINDING is a hazard to tier below. Then run
   the 13-item checklist in `.codex_state/rules/hazards.md` (the single source) against the manifest (grep, read templates it uses,
   check external types against the master's `puppet module list` and the production module list in
   the 2026-09-30 design entry). For each hazard found decide the tier:
   - You can resolve (pin+install a module via Puppetfile+r10k on the master following the module rules;
     set required_base/required_external/resource_type in the plan; choose a fixture param value): do it,
     record it (plan edit + one-line note in the class's log), continue.
   - Salatiel-tier (new node/OS, production access, behaviour change, hand-repair of node state): write
     `.codex_state/escalations/<class>.md` (evidence, options, your recommendation), add a blocked.txt
     entry with category + evidence, `git add` both (plain tracking, no `-f`), commit `block(<class>): ...`, regenerate, and
     move to the next class. Counts as resolved.
2b. PATH: `python3 .codex_state/tools/classify_path.py <class>` (CLAUDE.md "Generation paths").
   - `unchanged-validated` → ADVISOR-DIRECT, skip steps 3–4: `test_class.sh --revert-first <class>` to GREEN
     (not GREEN → it is not this path: continue at step 3), write the 2-line header with the modules
     `orientation.py <class>` lists, `.codex_state/tools/record_green.sh <class>`, then step 5.
   - `baseline-sync first` / `context-gap` → resolve (hazard 8 sync commit / params or Hiera fixture or
     required_base plan fix), re-classify.
   - `syntax-work` → steps 3–4 (Codex). `ERROR` → stop the run and report.
3. REVERT: the wrapper reverts the node itself before Codex starts (step 1.2). If it prints
   `REVERT_FAILED`, stop the run and report.
4. CODEX: `~/.local/bin/codex_migrate_class puppet_infrastructure::<class> 2>&1 | tee .codex_state/logs/<class>.$(date +%s).log`.
   The wrapper puts the orientation packet (`.codex_state/tools/orientation.py <class>`) in the prompt and
   tells Codex to record through `record_green.sh` only. Run it in the foreground with a long timeout. Do not
   interrupt it. Read only the LAST 60 lines to classify the outcome: GREEN+recorded (`RECORDED ... P8: migrate`)
   / BLOCKED (it wrote blocked.txt) / FAILED (neither). GREEN but not recorded: run
   `.codex_state/tools/record_green.sh <class>` yourself — it refuses unless the GREEN stamp matches the code.
5. VERIFY: spawn the `reviewer` subagent with the message "<class> --fresh" and nothing else (reviewer
   v2: it must not learn who authored the change or which path produced it — never mention Codex, the
   advisor-direct path, or paste any output). It persists
   `.codex_state/reviews/<class>/<UTC>.json`; commit that file as `P8: record review <class>`.
   - PASS: count it.
   - FAIL: read the evidence. If it is a records/annotation/header gap, fix the header comment yourself
     and record it with `.codex_state/tools/record_green.sh <class> --fix "<what>"` (comments + tracker only;
     it refuses a code change; commit `P8: record <class>: <what>`), then re-run the reviewer once.
     (Any ad-hoc `codex exec` keeps the mandatory `timeout -k 30 900 ... </dev/null`.) If it is faithfulness (reimplementation) or non-idempotency: back
     the migration out with a corrective commit (never force-push), preserve the manifest as
     `candidates/<class>.partial.pp` or `.reimplemented.pp` with a header, block with evidence, escalate.
6. BLOCKED by Codex: read its blocked.txt entry. It must carry category + evidence; if not, fix the entry.
   If the category is one YOU can resolve (cat 1 with a known compatible module; cat 3 with an existing
   capability whose plan column is simply unset), resolve it and retry the class ONCE from step 3.
   Otherwise accept the block, add an escalation file if Salatiel-tier, commit, continue.
7. FAILED (no green, no block): read the log tail. Apply the stop condition — if the failure yields a
   hypothesis you can act on within your authority, act once and retry from step 3 once. Otherwise
   block with evidence and continue.
8. `record_green.sh` already ran the standing composite compiles (step 2.2), regenerated the order file and
   pushed. Its exit 4 means a composite no longer matches `compile/composites.txt`: a regression (investigate
   before the next class) or a fix (update composites.txt in its own commit, then re-run record_green.sh).
   After a block, regenerate the order file yourself, commit if it changed, push.
9. METRICS (step 3.4): the tools logged events while you worked (path, revert, harness, codex, record,
   review). Close the attempt: `python3 .codex_state/tools/metrics.py close <class> --outcome
   PASS|FAIL|BLOCKED|FAILED|ESCALATED [--interventions N] [--note "<why a 2nd Codex run>"]` — it appends one
   record to `.codex_state/runs/metrics.jsonl` and commits `P8: record metrics after <class>` (worktree must
   be clean otherwise). Then move to the next class.

END OF RUN: `python3 .codex_state/tools/metrics.py summary` (medians/rates per path) goes in the summary.
Revert the node to baseline. Confirm `git status` clean and pushed. Print a summary table:
class | outcome (PASS/BLOCKED cat N/ESCALATED) | commit | one-line note. List every escalation file.
If any design decision was made (a new rule, a corrected diagnosis), append a dated entry to
DESIGN_DECISIONS.md before the final push.
