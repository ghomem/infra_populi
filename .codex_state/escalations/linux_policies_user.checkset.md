# linux_policies_user — check set past its correction cap (2026-11-21)

Status: OPEN, for HQ. Run rule (HQ batch-12 ruling 3): a class not used in production gets two correction rounds; the
third review still found a purpose gap, so the set is escalated rather than corrected again. It does not hold the run.
No behaviour finding: every review reproduced ALL_PASS, and the class behaves as its baseline says.

## The reviews
| review | verdict | gap |
|---|---|---|
| 20261121T013717Z | FAIL (purpose) | no-session side unchecked; the fixture's policies were no-ops (`true`) |
| 20261121T014847Z | FAIL (purpose) | the login's own policy run was not tied to the autostart (round 1 fixed the first review) |
| 20261121T015754Z | FAIL (purpose) | the agent run's own policy run is not tied to the agent run (round 2 fixed the second review) |

## What remains, and the fix I would make
`policies-run-on-an-agent-run-while-logged-in` counts the "loged in, executing policies" line and the
`p8test policy 1 as p8testuser` line over the whole journal. The login's autostart run alone produces both, so the
check would pass even if the agent-run script stopped after the runner's Executing line. The fix mirrors round 2's:
- count both lines `--since` the first `linuxint-policies-puppet-agent` line (t1);
- the node journal shows policy lines after each agent-run Executing line (1795226201.445, 1795226213.388 in the
  reviewer's run).

This is one clear change. I am holding it only because of the cap.

## For HQ
- **A:** allow a third round with this fix.
- **B:** accept the set as it stands, with the gap recorded. The behaviour itself passed every run.
