# Test-suite design note — observations (draft)

Collected 2026-11-22/23 while committing; each is measured, with its evidence.

- intermittent: the pre-commit full suite failed once at ~207 tests (1 error, -x) on 2026-11-22 while committing lab_idle_down (output not kept); passed alone and on retry (717). Idle-down teardown under load is the suspect.
- intermittent: the pre-commit fast subset rejected a commit once more on 2026-11-23 ~00:20Z (output lost to tail -1); passed on rerun. Proposal for the design note: the hook keeps its last failing output in a log file.
- the fast-subset flakes of 2026-11-22/23 were test_lab_idle_down's 'armed' assertion with a 1 s idle time (a slow status call lands after the watcher took the fake lab down); fixed in the parked test file.
- `git commit -- <path>` runs the hook with GIT_INDEX_FILE set to a temporary index; tests that run git in their own repos inherit it and fail ("unable to read <sha>"): test_codex_wrapper::test_hung_codex_is_killed. Proposal: conftest clears GIT_INDEX_FILE/GIT_DIR for subprocesses, or the hook unsets them before pytest.
- local_changes.md rows are split on '|' with no check: a '|' inside a code span shifted row #21's cells and the reviewer's records check failed (review 20261123T002612Z). Proposal: a pre-commit check that every row has exactly 6 cells.
- batch 20: test_lab_sleep_guard failed intermittently with a JSONDecodeError reading the fake world file. Cause: the
  fake lab's stubs and FakeLab.save wrote world.json in place; a reader could see a half-written file. Fixed: both write
  atomically (5066ec7).
- the first intermittent error above (2026-11-22, ~207 tests in) was test_lab_idle_down's teardown: FakeLab.run saves
  its in-memory world before every call, which turned the master back on under a running lab_power.sh down (found by
  repetition with kept test directories; fixed 135d01c).
- the pre-commit hook prints only the last 25 lines on failure, and the advisor's own filters dropped them twice: keep
  the full output of a failed run in a log file (proposal above).
- record_green.sh accepted a re-record with no class change, making a `P8: migrate` commit that the reviewer's
  provenance check refuses (user_lock, review 20261123T011346Z; HQ 2026-11-23 ruling 1).
- review_class.py's fixtures check reads the class's node over ssh before the harness starts it; with the node powered
  off (lab_power.sh up starts only the master and the default node) it reports fixtures=error (user_lock review
  20261123T014324Z). Proposal: start/revert the class's node first, or name the cause ("the class's node is not running").
- test_class.sh's between-runs gate (6e007df) treats any resource event in a daemon run as a failure; for a class whose
  plan lists expected_run2_events (Exec[apt_update]), a daemon run in the window would fail the harness although run 2
  may report that event: a false RED, never a false GREEN. Not yet seen (the daemon skips while the harness holds the
  agent lock). Proposal: filter the daemon's lines through the plan's expected_run2_events as run 2's are.
- the-agent-daemon-runs-the-catalog fails on the clean node by a probe timeout (no restart file), not by its output
  (review 20261123T041051Z): a valid but weak negative control.
- operator error 2026-11-23: files staged while a background commit's pre-commit hook was running went into that commit
  (42e7252, a tool commit, also carries filesystem_apt's and filesystem_base_desktop's sweep results and
  escalations/filesystem_apt.behaviour.md); git writes the commit from the index after the hook. Proposal: the hook
  records the staged list at its start and refuses if the index changed by its end.
