# Lab network canary — step 8 item 1 FAIL, stopped for HQ (2026-11-10 17:16Z)

**Status: STOPPED.** Per the plan's step 8 rule (HQ E), a canary FAIL stops the plan and is escalated with evidence.
There is no automatic rollback and no re-run. Not started: items 2 (rsyslog_client) and 3 (the three Phase 3 pilots).
The lab stays as it is: lab.env `hostonly`, aliases on 192.168.56.x, `-wifi` fallbacks present.

## What failed
Reviewer verdict `.codex_state/reviews/firewall_secure/20261110T171621Z.json` (committed as `P8: record review
firewall_secure`) is FAIL on exactly one check:
- `git`: `--fresh: migrate commit is under 92 later commits` (latest: b4-A7, b4-A6, b4-A4, …).

`review_class.py` defines `--fresh` as "the migrate commit must be at HEAD or under at most 3 record/regenerate
commits". It is the post-migration mode the loop uses right after record_green.
- firewall_secure's migrate commit is e342bdac (batch 2). Re-verifying it with `--fresh` fails `git` by
  construction, on any network.
- **The cause is my plan's wording.** Step 8 prescribed `reviewer firewall_secure --fresh` (and `rsyslog_client
  --fresh`). HQ approved that text, but I wrote it.

## What the run proves about the network (all other checks ok)
- Harness log `.codex_state/logs/reviews/firewall_secure.20261110T171459Z.harness.log`:
  - `Applying the host-only overlay (enp0s8 192.168.56.20, master 192.168.56.10)`;
  - `SUCCESS … (network hostonly)`: the revert's path assert (SSH_CONNECTION 192.168.56.1 → .20) and getent assert
    (.10) passed;
  - `NODE_FRESH: yes`;
  - `RUN1_EVENTS: 27 catalog` (rc 2, reverted first);
  - `GREEN: run 2 exited 0 with no change events`.
- So firewall_secure's default-drop applied with the ACL `acl = 192.168.56.1` (step 7). The harness's own SSH over
  host-only survived it. The agent reached the master on 8140 over host-only for both runs.
- `idempotent` ok (20 concrete resources covered); `scope`, `provenance`, `records`, `header_modules`,
  `comments_preserved`, `syntax`, `fixtures` and `faithful` all ok. The reviewer judged DIFF A faithful: jump
  renames and Integer typings, the same values.

## Options for HQ
1. **(Recommended)** Amend step 8 to the re-verification mode, without `--fresh`: `reviewer firewall_secure` and
   `reviewer rsyslog_client`. Re-run item 1 that way, then continue with items 2–3. Only the `git` check differs;
   every other check runs identically.
2. Accept this verdict as the network evidence for item 1 (every network-relevant check ok) and continue with item 2
   in the non-fresh mode.
3. Treat it as a canary failure and roll back steps 7 → 1. Not recommended: nothing points at the network.
