# sysmon_puppet_cert_status — Phase 1 review FAIL twice on comment preservation (OPEN, for HQ: the run is stopped)

The class carries local change #19 (HQ after batch 20, item 3): `files/sysmon/check_puppet_cert_health.py` reads the
certificates' expiry with openssl instead of `puppet certregen`. The Phase 3 after-check passes on the current code
(results/sysmon_puppet_cert_status/20261122T215658Z-author: OK, Warning, Critical, expired from fixture certificates).

## The two Phase 1 reviews
| review | verdict | failed checks | cause |
|---|---|---|---|
| 20261122T214907Z | FAIL | comments_preserved, faithful | the rewrite dropped the upstream comment "# This runs the command and collects the output" and reworded "#This will be the list where we will store the dictionaries ...", neither recorded in row #19 |
| 20261122T220040Z | FAIL | comments_preserved (faithful ok) | after the fix (the first comment restored verbatim but moved from 8- to 4-space indentation; the rewording recorded in row #19), the mechanical check still lists both lines |

The mechanical check (review_class.py, `comments_preserved`) fails on any baseline comment line absent from the final
file at its exact text and indentation. A moved comment counts as removed, and a reworded comment always counts, even
when a local-change row records it. The reviewer's faithfulness judgement on the second review was ok: the change is
exactly row #19.

## Why the run stopped
The loop allows one fix and one re-review after a Phase 1 FAIL (migrate-next skill, step 5), and that is spent. A
standing Phase 1 FAIL is the run rule's stop condition. Nothing else was changed after the second review.

## The fix I would make (one clear change)
Keep both upstream comment lines verbatim at their original indentation, and add the clarification as a new line:
- `        # This runs the command and collects the output` (8 spaces, inside the `try:` block, which still runs a
  command, openssl);
- `    #This will be the list where we will store the dictionaries containing the information about each machine's
  health` (4 spaces), followed by a new line noting that the list now holds (name, expiry) pairs under local change
  #19.

Then: harness GREEN, record_green (re-migration), the after-run on the current code, the row's evidence, and one more
Phase 1 review.

## For HQ
- **A:** allow that fix and one more Phase 1 review.
- **B:** a ruling on the check itself: a comment line that a local-change row records as reworded need not appear
  verbatim. That is a tool change, with tests.
