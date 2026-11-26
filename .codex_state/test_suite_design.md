# Behaviour test suite — design note (HQ ruling F, for HQ review)

Status: PROPOSAL, written 2026-11-26 after the final approval report (88feaae). Nothing here is built yet. The note
stops for HQ review; the open questions at the end need rulings before the first step.

## The requirements (HQ ruling F, 2026-11-18, verbatim)
- a conventional top-level test location in the module, not under .codex_state;
- per-class checks, fixtures and the runner, with a short "test one class" guide;
- the runner works without the advisor or Codex, against any disposable test node;
- checks state the purpose they test;
- no lab-specific names or secrets;
- JUnit output;
- the engine consumes the same suite.

## What exists today (measured 2026-11-26)
- **Check sets:** 90 files in `.codex_state/checks/` (89 with checks, 1 deferred). 758 checks, 372 of them mutating
  (an action plus a read-only effect), 64 with a mismatch control. 57 variants in 28 sets; 25 sets use a peer node,
  27 an agent run on the node mid-set, 2 an agent run on the peer, 4 a desktop session. 89 sets carry `purpose` and an
  `outcomes` table (each outcome mapped to checks, or `uncovered` with evidence, or an accepted gap).
- **Runner:** `.codex_state/tools/phase3.py`, 1538 lines. It validates a set against the pinned upstream baseline
  (`derived_from`), reverts the node, runs the CLEAN phase (negative controls must fail, invariants must pass), applies
  the class through the harness, runs the APPLIED phase (read-only checks first, mutating ones after), runs each
  variant on a fresh node, and writes JSON and JUnit to `.codex_state/checks/results/<class>/`. It also holds the
  engine's records: review verdicts, behaviour state, spot checks, the sweep.
- **Apply:** `test_class.sh` (996 lines, under `~/.local/bin`, outside the repo) deploys the module to the lab master
  and runs the agent twice on the node; GREEN means run 2 has no change events beyond the plan's
  `expected_run2_events`. `revert_node.sh` (434 lines) restores VirtualBox snapshots named in `.codex_state/lab/nodes.yml`.
- **Probe helpers:** `.codex_state/tools/probe_helpers.sh`, 95 lines, 10 functions, prepended to every node and peer
  script (HQ batch-12 ruling 6 already marked it for the public suite).
- **Fixtures:** params in `~/.config/infra_populi/params/` (65 files, 31 variant directories; local, never committed by
  standing rule); the master's Hiera, PKI, extra_files mount and clock settings from `master_fixtures.sh` (206 lines;
  values validated as obviously fake by a test); node fixtures `.codex_state/tools/tests/fixtures/node/*.pp`;
  `rules/test_asset_fixtures.txt` lists which node fixtures are test assets and which are stand-ins.
- **Lab-specific text inside the sets:** host-only addresses `192.168.56.*` in 17 sets (52 lines); the lab's host names
  `puppet8node`/`puppet8master` in 10 sets (14 lines); `p8lab-*` names in 8 sets (16 lines); runner variables `P8_*`
  in 5 sets (21 lines). The site path `/opt/puppet-infrastructure` appears in 38 sets (284 lines); the Phase 2 rename
  changes it.

## The design

### 1. Location
`spec/behaviour/` at the module root. `spec/` is where a Puppet module's tests live (PDK and rspec-puppet use
`spec/classes`, Litmus uses `spec/acceptance`), and PDK's default build ignore list leaves it out of a release
(this repository has no `.pdkignore` yet). The checks are YAML and
shell, not RSpec, so the directory is named for what it holds rather than `acceptance`, which would suggest Litmus
(open question 1).

```
spec/behaviour/
  README.md              how to test one class (below), the set format, the runner's options
  run                    the runner's entry point (python3 with PyYAML; no other dependency)
  lib/                   validate, probes, apply, variants, results (JSON and JUnit)
  probe_helpers.sh       moved from .codex_state/tools
  checks/<class>.yml     one set per class, moved from .codex_state/checks
  fixtures/params/<class>.yaml            the class's parameters for its base run
  fixtures/params/variants/<name>/<class>.yaml
  fixtures/hiera/        the Hiera data the apply uses (fake values only)
  fixtures/node/<name>.pp node fixtures, each marked test asset or stand-in
  fixtures/files/        files served as puppet:///extra_files (generated ones, like the throwaway PKI, are made at
                         run time and never committed)
```
Results go to `--out` (default `spec/behaviour/results/`, ignored by git).

### 2. The runner, without the advisor or Codex
```
spec/behaviour/run validate <class>
spec/behaviour/run <class> --node <ssh-destination> [--peer <ssh-destination>]
                   [--variant <name> | --all-variants --provider <command>]
                   [--apply local | --apply agent --server <host>] [--out <dir>]
```
- **A disposable node** is any machine reachable over ssh with passwordless sudo, freshly installed. The runner
  cannot make a node fresh, so it marks every node it uses (`/var/lib/behaviour-suite/used`) and refuses a marked
  node: a second run, or a variant, needs another fresh node. `--provider <command>` lets a caller supply them: the
  runner calls `<command> fresh <kind>` and gets an ssh destination back. The lab's VirtualBox revert becomes one such
  provider, in the engine.
- **Two ways to apply.** `--apply agent --server <host>` is today's path: the module is deployed to a Puppet server and
  the node's agent runs twice. `--apply local` copies the module, its Puppetfile modules and `fixtures/hiera` to the
  node and runs `puppet apply` twice, so a single disposable VM is enough. Local apply has never been run on these sets;
  serving `puppet:///extra_files` from a local fileserver mount is a design point to prove, not a measured fact (open
  question 3).
- **The gate moves into the runner.** Run 1 applies; run 2 must report no change events except the set's own
  `expected_run2_events` (moved from migration_plan.md into each set). Today this gate lives in test_class.sh.
- **The mid-set steps keep their meaning:** `node_agent` reapplies (agent run or `puppet apply` again); `peer_agent`
  needs a server, so sets that use it (2 today: hashman_web, hashman_base) declare `requires: [server]` and the runner
  refuses them under `--apply local`; `session` (4 sets: linux_policies_user, user_desktop, user_desktop_sudoer, user_kde_lock_screen) needs a desktop node and says so the same way.
- **Unchanged from today:** the CLEAN phase (negative controls fail, invariants pass, else the set is INVALID), read-only
  checks before mutating ones, mismatch controls that must fail after apply, and exit codes 0 all pass, 1 findings,
  2 invalid set, 3 apply or environment failure.

### 3. Checks state their purpose
Kept as now and required by the public validator: `purpose`, an `outcomes` table whose rows map to checks or are
`uncovered` with `why`, `lifted_by` and `evidence`, or are an accepted gap with the parameters named. A check keeps
`what` (the observable outcome in a sentence). `derived_from` stays as the reference to the code each check comes from;
the public validator checks that each reference resolves in the module's own tree at the tag being tested, and the
engine keeps its stricter check against the pinned upstream baseline (open question 5).

### 4. No lab-specific names or secrets
- **Names:** the runner exports `NODE_ADDR`, `PEER_ADDR`, `NODE_NAME`, `SERVER_NAME` and the site paths from the Hiera
  fixture (`BINDIR`, `LOCALDIR`) to every probe. The 52 + 14 + 16 + 21 lab-specific lines above become those variables.
  The validator refuses a literal private address or a lab host name in a probe, as it already refuses a probe that
  reaches another host.
- **The rename:** once probes read `BINDIR`/`LOCALDIR` from the fixture, the Phase 2 rename changes one Hiera fixture
  instead of 284 lines in 38 sets. So this parametrisation should come before the rename.
- **Values:** every committed fixture value must pass one rule, the one master_fixtures.sh's test already applies: it
  contains `p8test`, uses a reserved name (`.invalid`, `example.com` and its kind) or an RFC 5737 address, is a lookup,
  or is a plain number. Test passwords are fake and say so (`...-not-a-secret`). Nothing read from production, and no
  real credential, is ever a fixture. Committing params fixtures goes against the standing rule "never commit params",
  so it needs a ruling (open question 2).

### 5. JUnit
Kept: one `<testsuite>` per phase (clean, applied) per run (base, each variant), one `<testcase>` per check, a mismatch
control as its own testcase, the probe's output in `<system-out>`. The JSON record stays beside it.

### 6. The engine consumes the same suite
`phase3.py` keeps the engine's part and calls the public runner for the rest:
- **Public (spec/behaviour):** the set format and its validator, probes and helpers, apply and gate, variants, the
  clean and applied phases, JSON and JUnit.
- **Engine (.codex_state):** the VirtualBox provider (revert_node.sh, nodes.yml), the lab lock and sleep guard, the
  stricter `derived_from` check against the upstream pin, the records (results under `.codex_state/checks/results`,
  reviews, verdicts), `state`, `spot`, metrics and the approval report.
- **Proof of sameness:** before the engine switches, a sample of sets (one per kind of step: a peer, a variant, a
  node agent run, a peer agent run, a session, a mutating exercise) runs through both runners on fresh nodes, and every
  check's outcome must match. The old runner is removed only after that.

### 7. "Test one class" (the README's core)
1. Make a fresh Ubuntu 24.04 VM you can throw away; give the runner ssh access with passwordless sudo.
2. `spec/behaviour/run validate <class>`.
3. `spec/behaviour/run <class> --node <ssh-destination> --apply local`.
4. Read `results/<class>/<time>.xml` (or the JSON). A FINDING is a check that failed after apply; INVALID means the
   set itself is wrong (a negative control passed on the clean node).
5. Variants and peers: each variant needs another fresh node (`--variant <name> --node ...`, or `--all-variants
   --provider ...`); a set with a peer needs `--peer` (a second fresh Ubuntu 24.04).

### 8. Order of work (each step its own commit, with tests and the full suite; no check changes meaning)
1. Move probe_helpers.sh and the set format's validator into `spec/behaviour`, with their tests.
2. Replace the lab-specific text in the sets with the runner's variables, and add the validator rule (the set
   contents change; their reviews are re-judged only where a probe's meaning changed, which should be none).
3. Move the gate and `expected_run2_events` into the runner and the sets.
4. Build `--apply local` and prove it on a sample against `--apply agent`.
5. Move the checks and the fake-only fixtures (after the ruling on open question 2).
6. Switch the engine to the public runner after the sameness proof; remove the old code.
7. The README.

## Open questions for HQ
1. **Location:** `spec/behaviour/` (recommended) or `spec/acceptance/`?
2. **Fixtures in the repository:** may fake-only params fixtures be committed under `spec/behaviour/fixtures`, checked
   by the fake-values validator, as an exception to "never commit params"? Without it the public runner needs the
   caller to supply every class's params.
3. **Local apply:** is `puppet apply` on the node an acceptable public default, given it has not been measured against
   the agent path yet, or should the public runner require a Puppet server like the engine?
4. **Names:** the runner's variables are proposed without the `P8_` prefix (it names the migration, not the suite).
   Should the suite take its final names (`infra_populi`) now or at the rename?
5. **`derived_from` in public:** check references against the module's own tagged release (proposed), or keep them as
   documentation only outside the engine?

## Appendix: engine test-suite observations (moved from drafts/test_suite_notes.md, collected 2026-11-22 to 26)
- **Fixed:** test_lab_idle_down's teardown restarted the fake master under a running `lab_power.sh down` (135d01c);
  the fake lab's world file was written in place and read half-written (atomic writes, 5066ec7); an 'armed' assertion
  with a 1 s idle time raced a slow status call (fixed in the test); tests read the laptop's real battery and wrote the
  real guard state (feb9cd0); review_class.py read a local change's after-check from the base run only (66e621d).
- **Proposals, not built:**
  - the pre-commit hook keeps its full output in a log file when the suite fails (it prints the last 25 lines, and
    that output was lost twice);
  - the hook (or conftest) clears `GIT_INDEX_FILE`/`GIT_DIR` before pytest: `git commit -- <path>` runs the hook with
    a temporary index that the tests' own git calls inherit (test_codex_wrapper::test_hung_codex_is_killed failed);
  - a pre-commit check that every local_changes.md row has exactly 6 cells (a `|` in a code span shifted row #21's
    cells and failed a review);
  - the hook records the staged list at its start and refuses if the index changed by its end (files staged during a
    running hook went into 42e7252);
  - record_green.sh refuses a re-record with no class change (it made a `P8: migrate` commit the reviewer's provenance
    check refused, user_lock, review 20261123T011346Z);
  - review_class.py's fixtures check starts or names the class's node when it is powered off (fixtures=error, user_lock
    review 20261123T014324Z);
  - test_class.sh's between-runs gate filters the daemon's lines through `expected_run2_events` as run 2's are (a false
    RED is possible; not seen yet);
  - the clean-phase failure of the-agent-daemon-runs-the-catalog is a probe timeout, not its output (review
    20261123T041051Z): a valid but weak negative control.
- **Lab limits met in the 2026-11-24/25 runs:** phase3's 600 s action cap against a growing apt backlog on the node
  baseline (escalations/filesystem_apt.behaviour.md); dnf metadata re-downloaded after every rhel9 restore (138 MB at
  9 h, 327 MB at 26 h); `/run` mounted noexec on Ubuntu (an askpass helper had to move); results written to `/dev/shm`
  are deleted by systemd-logind's RemoveIPC when the writer exits.
