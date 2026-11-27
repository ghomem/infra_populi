# Gate v2 passes a run 2 that logged a resource error (found 2026-11-26, behaviour suite step 7)

## What happened
The public runner's sample ran `extra_packages_el` on rhel9 through the gate-v2 harness while the lab's NAT uplink was
degraded (the laptop had changed networks that morning; Red Hat's CDN answered slowly or not at all). The harness
printed GREEN:

```
Error: /Stage[main]/Puppet_infrastructure::Extra_packages_el/Exec[enable-codeready-builder-repo]/unless: Check "subscription-manager repos --list-enabled | grep -q 'codeready-builder-for-rhel-9-x86_64-rpms'" exceeded timeout
Notice: Applied catalog in 300.21 seconds
...
GREEN: run 2 exited 0 with no change events (gate v2).
```

Record: `.codex_state/checks/public/harness/extra_packages_el/20261126T102814Z.json` (apply tail). The behaviour checks
then failed (each `subscription-manager`/`dnf` probe timed out at 120 s): outcome FINDINGS, caused by the environment,
not the class.

## Why the gate let it through
The `Check ... exceeded timeout` message is Puppet's exec type handling a timed-out `unless`/`onlyif` command: it logs an
error, takes the check as false (for `unless`: the exec is in sync, so it does not run), and the resource does not
fail. The run exits 0 with no change event. Gate v2 (test_class.sh) checks run 2's exit code and its change events
only; its own message says "GREEN requires exit 0 (no changes, no failures)", and this run had an error it does not see.

## Is anything recorded on it?
No false PASS found:
- this GREEN was not recorded (no record_green.sh run); extra_packages_el's Phase 1 record comes from an earlier,
  healthy run, and its behaviour set passed afterwards (checks/results/extra_packages_el, reviewer PASS);
- a scan of every stored apply tail (phase3 results, base and variants; public-runner records) and every Phase 1
  review found no other GREEN with an `Error:` line. The tails are the last 1500 characters, so this is evidence,
  not proof, for the older runs; the behaviour sets (86 pass) would show a class whose work a hidden error undid.

## Options
A. Gate v2 also refuses any `Error:` line in run 1 or run 2 (one grep in test_class.sh; a test with a fixture whose
   exec's `unless` sleeps past its timeout). Only tightens: a GREEN can become RED, never the reverse. Recommended.
B. Refuse `Error:` lines in run 2 only (run 1 may legitimately log errors the class corrects? None is known).
C. Leave the gate; document that the behaviour sets catch what it misses.

The public runner (spec/behaviour) already does A for its own agent and local modes (gate(): an `Error:` line in either
run fails it; test_runner.py). Its command mode keeps the harness's verdict, so the sample compares like with like.

## Resolved (HQ review of the behaviour suite, 2026-11-27, ruling 1: option A)
Gate v2 refuses an `Error:` line in either run and counts run 2's changes from Puppet's last-run report on every run,
not only when run 2 exits 2 with no console line. The harness no longer has a gate of its own: it calls the behaviour
suite's (`spec/behaviour/lib/behaviour/gate.py`, `python3 -m behaviour.gate`), which the public runner uses too, so
the two cannot differ. Tests: test_harness_gate.py (an error in run 1 or in run 2 with exit 0 is red), test_gate.py.
