# The sweep of open uncovered rows — approach (CLOSED 2026-11-23: HQ ruling 1, option B; carried out, the swept sets reviewed 2026-11-25)

HQ after batch 20, item 7: the sweep of open uncovered rows, then the final approval report (stop for Salatiel).
`phase3.py sweep` lists 67 rows in 34 approved sets written before HQ batch-15 ruling 3. Each lacks `evidence`, and
every one names an ACTIVE node kind as `lifted_by` (ubuntu 43, rhel9 15, ubuntu2 3, gnome 2, kubuntu 2,
puppetserver 2), which the strict rule refuses: "one lifted by an active node kind is a work item to test there".

Any edit makes a set stale (phase3.py state compares the file with its review), so every touched set needs a new run
and a Phase 3 review: 34 runs and 34 reviews, whichever approach is taken.

## The rows, by their real reason (counted 2026-11-23 by the words of each row's `why`)
- **Parameter or fixture variants (27 rows; `why` names a variant):** "one set holds one params fixture". The node kind is the plan's
  own; what is missing is a second fixture per set. The runner runs one params fixture per set (phase3.py, harness).
- **The RedHat branch (13 rows; `why` names the RedHat branch or RHEL):** the set runs on its plan node (Ubuntu); the branch needs the same checks on
  rhel9, which is active. The runner runs a set on its plan node only (`phase3.py run <class>` has no node option).
- **Single cases (the other 27 rows):** a cron time (23:00, 03:17), a GNOME session (the runner starts Plasma only), a
  mail relay to deliver to, the private half of a fixture key (the repository keeps none), a compile-time refusal,
  deprecated sshd options with no behaviour, an ecryptfs home, an internal network behind a node, xt_geoip, and rows
  already covered by another class's set.

## Options
- **A (recommended): record the real gap.** Rewrite each row with `lifted_by: capability: <what is missing>` and its
  `evidence` (the runner's code line or a command result): "more than one params fixture per set", "a set run on a
  second node kind", "a timer trigger in the runner", "a GNOME session in the runner", and so on; a row whose reason
  is "covered by <class>'s set" names that set and its check ids. Rows that a node really can test now with the
  existing runner become checks. The 34 sets then run and are reviewed. Lab time is measured as it goes.
- **B: build the two runner capabilities first** (a second params fixture per set; a set run on another node kind),
  then turn the variant and RedHat rows into checks. More coverage; a tool change of its own and more runs.
- **C: A now, B as Phase 5 backlog items** named in the approval report.

The final approval report follows the sweep; the test-suite design note and the rename come after Salatiel's stop.

## Closed
HQ ruled option B on 2026-11-23 (DESIGN_DECISIONS "HQ rulings on the sweep and the escalated lifts", ruling 1): the
sets were swept once (variants for the parameters production uses, accepted gaps for the others, RedHat rows on
rhel9). The swept sets were reviewed on 2026-11-25 (the reviews with no durations and the duration list, HQ
2026-11-24 item 4); the approval report regenerated that day lists 84 open rows in 61 classes, down from 118 in 72.
