---
name: migrate-next
description: Run the Phase 1 migration loop autonomously for a budget of classes. Usage /migrate-next 5, /migrate-next until 5 done, /migrate-next until 8 resolved (resolved = done + blocked-with-evidence). Picks the next pending class from the order file, runs hazard checks, reverts the node, invokes Codex through the wrapper, verifies with the reviewer subagent, records, and continues. Escalates by file and keeps going.
---
Budget: parse the argument. `N` means N classes reach reviewer-PASS. `until N done` same. `until N resolved`
counts PASS + blocked-with-evidence. Stop exactly at budget, or when no PENDING non-blocked class remains.

PREFLIGHT (once): read CLAUDE.md and the three most recent DESIGN_DECISIONS.md entries. `git status`
clean and HEAD == origin/main (fix by push if only ahead; STOP if diverged). `ssh puppet8master` reachable
and 8140 listening. Regenerate the order file. Create `.codex_state/logs/` if missing.

FOR EACH CLASS:
1. PICK: next PENDING row in migration_order.md that is not in blocked.txt. Read its plan row
   (resource_type, internal_deps, required_base, required_external, self_contained) and
   `manifests/<class>.pp`. If deps are not DONE, the order file is wrong — investigate, do not skip silently.
2. HAZARDS: run the 7-item checklist from CLAUDE.md against the manifest (grep, read templates it uses,
   check external types against the master's `puppet module list` and the production module list in
   the 2026-09-30 design entry). For each hazard found decide the tier:
   - You can resolve (pin+install a module via Puppetfile+r10k on the master following the module rules;
     set required_base/required_external/resource_type in the plan; choose a fixture param value): do it,
     record it (plan edit + one-line note in the class's log), continue.
   - Salatiel-tier (new node/OS, production access, behaviour change, hand-repair of node state): write
     `.codex_state/escalations/<class>.md` (evidence, options, your recommendation), add a blocked.txt
     entry with category + evidence, `git add -f` both, commit `block(<class>): ...`, regenerate, and
     move to the next class. Counts as resolved.
3. REVERT: `.codex_state/tools/revert_node.sh`. Must end in SUCCESS; otherwise stop the run and report.
4. CODEX: `~/.local/bin/codex_migrate_class puppet_infrastructure::<class> 2>&1 | tee .codex_state/logs/<class>.$(date +%s).log`.
   Run it in the foreground with a long timeout. Do not interrupt it. Read only the LAST 60 lines to
   classify the outcome: GREEN+committed / BLOCKED (it wrote blocked.txt) / FAILED (neither).
5. VERIFY: spawn the `reviewer` subagent with the message "<class>" and nothing else. Do not paste it
   any Codex output.
   - PASS: count it.
   - FAIL: read the evidence. If it is a records/annotation/header gap, fix with ONE targeted
     `codex exec -c 'sandbox_mode="danger-full-access"' -c 'approval_policy="never"' '<precise fix>'`,
     requiring its fix commit message to start with `P8: record <class>: `, then re-run the reviewer
     once. If it is faithfulness (reimplementation) or non-idempotency: back
     the migration out with a corrective commit (never force-push), preserve the manifest as
     `candidates/<class>.partial.pp` or `.reimplemented.pp` with a header, block with evidence, escalate.
6. BLOCKED by Codex: read its blocked.txt entry. It must carry category + evidence; if not, fix the entry.
   If the category is one YOU can resolve (cat 1 with a known compatible module; cat 3 with an existing
   capability whose plan column is simply unset), resolve it and retry the class ONCE from step 3.
   Otherwise accept the block, add an escalation file if Salatiel-tier, commit, continue.
7. FAILED (no green, no block): read the log tail. Apply the stop condition — if the failure yields a
   hypothesis you can act on within your authority, act once and retry from step 3 once. Otherwise
   block with evidence and continue.
8. Regenerate the order file, commit if it changed, push. Move to the next class.

END OF RUN: revert the node to baseline. Confirm `git status` clean and pushed. Print a summary table:
class | outcome (PASS/BLOCKED cat N/ESCALATED) | commit | one-line note. List every escalation file.
If any design decision was made (a new rule, a corrected diagnosis), append a dated entry to
DESIGN_DECISIONS.md before the final push.
