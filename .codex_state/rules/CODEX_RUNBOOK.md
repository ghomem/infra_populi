# CODEX_RUNBOOK.md - Phase 1: Syntax Migration

<!-- TRACKED single source since 2026-10-27 (step 3.5; was ~/.config/infra_populi/CODEX_RUNBOOK.md). The wrapper
injects this file, then .codex_state/rules/hazards.md, into every Codex prompt. -->

## 0. What this document is

This is an AUTHORITY document, not a procedure. It says what you decide, what stops you, and how you record a stop. You own the migration loop for one class per invocation. Work the problem: research, retry, fix. Escalate only at the walls named in section 3.

Phase 1 scope: Puppet 5 -> Puppet 8 / Vox Pupuli syntax migration, behaviour preserved exactly. GREEN means "compiles and applies idempotently" - it does NOT mean behaviour is preserved. That is your responsibility, not something the harness proves.

## 1. Your authority - act without asking

- Params JSON under ~/.config/infra_populi/params/ - determine values yourself: probe the node, read templates to learn what a parameter feeds, pick values that exist in the environment. Never commit these.
- Never target a real account. Where a class acts on a user identity - creating, modifying, locking, or granting privileges to it - the value must be the synthetic fixture p8testuser, never a real login on the node (salatiel, root, or any existing account). This applies to params JSON as much as to the define title: the migration plan assigns p8testuser deliberately, and a params override defeats it. The reason is safety, not tidiness: user_lock locks the account, user_sudoer grants sudo, user_samba changes Samba identity - any of these aimed at the harness's own SSH user would lock you out of the node mid-run. If a class needs the account to exist first and nothing creates it, that is an undeclared prerequisite - stop and record it, do not substitute a real user to make the run proceed.
- Forge modules - install via Puppetfile + r10k on the master, pinned to an exact version inside the consumer's declared range; after r10k run `puppet module list` (any `invalid` = failure) and, for a module with custom types, `puppet generate types --environment production` + puppetserver restart. Then export the Puppetfile into the repo: `python3 .codex_state/tools/export_puppetfile.py` (record_green.sh refuses while the repo copy differs from the master). Name the module and its version in the class header; record_green.sh adds it to necessary_modules.txt.
- Research - Forge, docs, web. Module compatibility and Puppet 8 semantics are yours to establish.
- Environment recovery - run .codex_state/tools/revert_node.sh whenever the node needs a clean baseline. You may START a stopped or aborted master or node VM and verify it. You must NEVER restore a snapshot of the MASTER, power it off, or reset it - that would discard the Puppetfile, installed Forge modules, and node manifests that are deliberately kept there. Node snapshot restores are fine and expected; the node is disposable, the master is not.
- Iterate - read the error, form a hypothesis, fix, rerun. Repeat while each attempt teaches you something.
- Record a block - write the blocked.txt entry yourself when you hit a section 3 wall.
- Cleaning up after a failed dependency. If you install a Forge module and it turns out to be incompatible with Puppet 8, you must leave the environment as you found it: remove the mod line from the master's Puppetfile, re-run r10k so the module directory matches, and delete the installed module directory if r10k leaves it behind. Do NOT record it in necessary_modules.txt - that file lists modules the migration NEEDS AND USES, and a module that will not load is a blocker, not a dependency. Record it in blocked.txt with evidence instead. An orphaned module left installed is debris that misleads the next session about what the environment requires.

## 2. The loop

1. The wrapper has reverted the node. To start clean again: test_class.sh --revert-first <class>.
2. Run the harness: test_class.sh <class>. It classifies from migration_plan.md (class vs define, title, required_base) and dies loudly on missing params.
3. Fix what fails. Smallest change that preserves behaviour.
4. Loop to GREEN (gate v2): run 2 exits 0 with no change events and the class's resources are in the catalog. The harness stamps the code that went GREEN.
5. Add the 2-line header to the manifest: purpose (or '<baseline> manifest validated unchanged') and every module dependency with its installed version.
6. Record: .codex_state/tools/record_green.sh <class>. It is the ONLY recorder: it checks the GREEN stamp, the header, the worktree and the standing composites, writes the tracker marker, commits 'P8: migrate puppet_infrastructure::<class>', regenerates the order file, commits and pushes. Never hand-write migrated_classes.txt or migration_order.md, never commit class files yourself.

## 3. What stops you - PHASE-SCOPED, expect this section to be replaced

These triggers are correct BECAUSE Phase 1 is syntax-only. Later phases will have different ones - Phase 3's work IS behavioural, so "any behaviour change" would halt everything there. The durable principle: escalate decisions whose consequences extend beyond the current class.

THE INFORMATIONAL STOP. Stop when an attempt produces NO NEW INFORMATION - the same failure repeats, or your next step would be a guess rather than a hypothesis derived from the error. This is not a retry count; padding attempts is forbidden.

CATEGORY 1 - DEPENDENCY INCOMPATIBILITY. A Forge module or custom type will not load on Puppet 8. Do NOT reimplement the class's behaviour to avoid it. Resolution is module-level (find a compatible module, or fix the incompatibility) and belongs to a deliberate investigation, not this loop.

CATEGORY 3 - HARNESS CAPABILITY GAP. The harness cannot classify or contextualise the class, or the required context is unknown. Includes: needs a base whose identity is not established, or needs a capability that does not exist.

CATEGORY 5 - ENVIRONMENT MISMATCH. The class targets an OS the test node is not. Distinguishing question: does it EXECUTE OS-specific commands, and is that execution GUARDED? A class that only DEPLOYS OS-specific files is fine - Puppet never runs them. Note: an unless/onlyif whose command does not exist on the target OS exits non-zero, which Puppet reads as "condition unmet" - so it RUNS the command anyway. A guard that cannot run is worse than none.

BEHAVIOUR CHANGE. Any fix that alters what the class does rather than how it is written. Includes dropping a resource, changing a default, or replacing a mechanism.

BEYOND-TARGET EDITS. Anything requiring changes to a class other than the target - except required_base classification, which the harness handles.

HAND-REPAIRING NODE STATE. If GREEN would need manual fixes to the node outside Puppet, stop.

## 4. Recording a block

Append to .codex_state/blocked.txt, then STOP AND REPORT. The entry must carry EVIDENCE, not just a classification:

- The actual error text
- The traced chain (what needs what, and where you established it)
- The specific module, resource, or path involved
- The category and why that category
- What would unblock it

A conclusion without working shown cannot be verified.

Environment failures are NOT class blocks. If the harness fails before it reaches classification or catalog compilation - master unreachable, a VM aborted, SSH failing, rsync unable to connect - that is an infrastructure problem, not a property of the class. Recover it yourself where you are permitted to (start a stopped VM, revert the node) and continue. Do NOT write it to blocked.txt: that file records classes with real obstacles, and infrastructure incidents pollute it. Only report and stop if recovery is outside your authority or fails.

## 5. Hazards

The checklist follows this runbook in the prompt (.codex_state/rules/hazards.md, single source).
