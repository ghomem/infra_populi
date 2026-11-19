# Lab uplink too slow for node reverts (2026-11-19, from 06:25Z)

Status: OPEN, for Salatiel (the laptop's uplink is outside the lab). Lab runs are on hold. Nothing was recorded on the
failed runs.

## Evidence (measured 2026-11-19)
- **Reverts fail:**
  - Every node revert since 06:25Z stops at the apt refresh: `ERROR: apt-get update failed on node 'puppet8node'
    (mirror unreachable?)`.
  - Failed attempts: two in the openvpn_server Phase 3 review (results/openvpn_server/20261119T062528Z-reviewer,
    20261119T062911Z-reviewer, ENVIRONMENT_FAILED; no verdict persisted), two by the advisor. The last one took 196 s
    against the 180 s apt limit (revert_node.sh, DESIGN_DECISIONS 2026-10-26).
- **Bandwidth:** one file (ao.archive.ubuntu.com noble main Packages.gz) for 60 s:
  - laptop: 1,255,592 bytes (20,926 B/s);
  - node through VirtualBox NAT: 306,600 bytes (5,109 B/s).
- **Dead mirror address:** security.ubuntu.com resolves to 185.125.190.83 and 91.189.92.24.
  - 185.125.190.83 times out on port 80 from the laptop and from the node.
  - 91.189.92.24 answers 200.
  - apt falls back, but each fallback first waits out the connect timeout.
- **apt timing:**
  - A manual refresh on partly fresh lists finished in 93 s (2,988 kB at 33.8 kB/s).
  - A full refresh, as after a restore, with `-o Acquire::http::Timeout=10` still hit the 180 s limit.
- **No VPN:** no tunnel-type interface was up on the laptop.

## Why no tool change
- The revert's apt refresh guards a ruled property: current package lists and real internet before any harness run.
- At about 5 kB/s a full refresh takes many minutes. Raising the limit would make every revert that slow, and it would
  hide a degraded uplink rather than fix anything.
- A shorter connect timeout did not bring the refresh under the limit (measured above).

## To resume
1. Restore a normal uplink.
2. Re-run `.codex_state/tools/revert_node.sh`. A refresh of about 12 s, as measured 2026-10-26, means it is back.
3. Then:
   - re-dispatch the reviewer for openvpn_server --phase3 (its set is committed, author run 20261119T061919Z
     ALL_PASS);
   - run network_vpn's extended set (drafted and validated, not yet in the repo);
   - continue backfill batch 4 → the batch report.
