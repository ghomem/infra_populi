# user_lock — Phase 1 review FAIL on provenance after the stand-in lift (OPEN, for HQ: the run is stopped)

## What happened
HQ after batch 20, item 6 lifts user_lock's stand-in. Done (7175bca): the class runs on the master-role node
(puppetserver) and hashman itself creates p8testuser (node fixture hashman_user_via_hashman, a test asset in
rules/test_asset_fixtures.txt: `pp_auth.py useradd ... SILENT`, then `unlock`), instead of seeded hashes. Harness GREEN
there; the set ALL_PASS (results/user_lock/20261123T010755Z-author, 14522e1).

Because the fixture is no longer a stand-in, the tracker's `mock-apply` marker had to go. I ran
`record_green.sh user_lock --defect "exec guarded by its post-condition"`, which made a `P8: migrate
puppet_infrastructure::user_lock` commit (3731d97) that changes only migrated_classes.txt. The class content is
unchanged since a795d98.

## The review
Review 20261123T011346Z: FAIL, provenance only ("the migrate commit changed no class file"); faithful ok (DIFF A is the
header and the ruled upstream-defect guard), fixture scope ok, records ok. The check takes the newest migrate commit
as the content change; record_green allowed one that changes no class file. My error was the choice of path; the two
tools disagree on whether such a commit is valid.

## Why the run stopped
The FAIL cannot be fixed inside the records path: history is not rewritten, and `record_green.sh --fix` plus a re-review
would still find 3731d97 as the newest migrate commit. A standing Phase 1 FAIL is the run rule's stop condition.

## Options
- **A (recommended): a tool change with tests.** record_green refuses a migrate commit that changes no class file and
  points to `--fix` (marker-only changes); provenance takes the newest migrate commit that changed a class file, and
  reports a later class-file-free migrate commit as a records commit. Then one more review of user_lock.
- **B:** provenance unchanged; user_lock stays FAIL on provenance with a note in the approval report (its behaviour is
  verified on the master-role node).
