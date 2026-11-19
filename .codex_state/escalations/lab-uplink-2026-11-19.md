# Lab uplink too slow for node reverts (2026-11-19, from 06:25Z)

Status: REOPENED 2026-11-19 12:14Z, for Salatiel: Canonical's archive mirrors are unreachable from this network (see
"Reopened" below); lab runs are on hold again. History: first held from 06:25Z (slow uplink), resolved 11:17Z
(Salatiel: "internet should be normal").

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

## Resolved (2026-11-19)
- `revert_node.sh` succeeded at 11:17:19Z to 11:17:51Z with no VPN interface on the laptop. From REVERT_METRICS:
  total 30.9 s, apt update 9.8 s.
- The peer's revert in the next run took 58.5 s, of which apt update was 38.6 s (REVERT_METRICS, run
  20261119T113217Z), well inside the limit.
- The resume steps ran:
  - openvpn_server's review re-ran (20261119T112433Z, FAIL on purpose → correction round 1 → review 20261119T114553Z
    PASS with two findings, escalations/openvpn_server.behaviour.md);
  - network_vpn and batch 4 continue.

## Reopened (2026-11-19 12:04Z to 12:14Z)
- **Run network_vpn 20261119T120430Z-author: ENVIRONMENT_FAILED.**
  - Node revert succeeded, but its apt update took 112.4 s (9.8 s at 11:17Z).
  - The peer's revert failed: "apt-get update failed on node 'p8lab-ubuntu2' (mirror unreachable?)".
- **Measured from the laptop at 12:08Z to 12:14Z** (no VPN interface):
  - every address of archive.ubuntu.com and security.ubuntu.com (9 each) fails: TCP connect to port 80 never
    completes within 8 s;
  - port 443 behaves the same;
  - the same addresses answer ping (91.189.92.23, about 65 ms).
- **Other hosts are fine:**
  - deb.debian.org: 967 kB/s;
  - www.google.com: 0.24 s;
  - launchpad.net (Canonical): 0.1 s to connect, HTTP 200;
  - 1.1.1.1: 4.8 to 21.3 ms ping.
- **So** this is not the uplink's speed: the connection works, but Canonical's archive hosts do not take TCP
  connections from this network right now (a filter on the path, or an outage on their side). Both are outside the
  lab.
- **Options:**
  - wait and retry;
  - point the lab VMs at another Ubuntu mirror. That changes the baseline snapshots' sources, which is Salatiel's call
    (the snapshots are baselines).
- **Resume:**
  1. Re-run `.codex_state/tools/revert_node.sh`; an apt update of about 10 s means it is back.
  2. Re-run `phase3.py run network_vpn` (the corrected set, commit 6bce592).
