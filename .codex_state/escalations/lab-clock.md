# Lab: VM clocks drift under the kvm paravirt provider (0.465% slow after the cold boot; 2.45% fast before); hyperv fixes it on every lab VM (2026-11-25: all seven on hyperv, measured -11 to +7 ppm; enforced by 8d5ca2f)

Found 2026-11-23 by the sweep: node_base's `ntp-keeps-the-time` failed twice (results/node_base/20261123T132939Z-author:
a source selected, the clock not synchronised; 20261123T142843Z-author: no source). The check passed on 2026-11-18
(20261118T193806Z, 20261118T194317Z) and is unchanged since its review.

## Measured (2026-11-23, laptop on AC, VPN off)
- **The node's clock rate against the laptop's** (each side's /proc/uptime, read twice 120 s apart over lab_exec; each
  read took 1.0-1.7 s, so about ±1.2%):
  - clocksource tsc (the guest's own, calibrated at 3601.070 MHz in the boot the baseline snapshot holds): laptop
    121.47 s, node 124.44 s, ratio 1.0245;
  - after switching the running node to kvm-clock: laptop 121.35 s, node 124.57 s, ratio 1.0265.
  The guest's clocksource is not the cause: VirtualBox's virtual time itself runs fast.
- **The laptop's clock:** "System clock synchronized: yes" (timedatectl). ntpd/timesyncd slew it by at most 500 ppm, so
  the laptop is not the 2.5%.
- **ntpsec on the node with node_base applied** (ntpq every 10 s for 600 s): it reached its server at once, stepped the
  clock by -0.808363 s, selected the server from 10 s to at least 81 s, and selected nothing from 143 s on; offset
  -13125.3 ms then -14723.6 ms, jitter 6880.704 ms then 6949.192 ms. ntpd disciplines a clock's frequency by at most
  500 ppm, far below 2.5%.
- **timesyncd on the clean node** (when ntpsec is not installed) steps the clock at each 32 s poll: offset -1.145530 s,
  jitter 427.644 ms. That broke ssh_secure's idle-session probe, which timed by the wall clock: measured 28-29 s, then
  "ended after 29.3s (wall clock 28s)" on the monotonic clock. Corrected in the set (monotonic timing).
- **Host:** Linux 7.0.0-22-generic, VirtualBox 7.2.6_Ubuntur172322; the node VM has hwvirtex on, nestedpaging on and
  paravirt provider default (effective kvm).

## Effect
- node_base's `ntp-keeps-the-time` cannot pass while the node's clock runs this fast. Its Phase 3 review is held. Its
  set otherwise passes in the same runs (variants rhel and prod ALL_PASS).
- Checks that time intervals by the wall clock on a node are exposed (ssh_secure's was; corrected).
- The other nodes and the master were not measured.

## Not tried (outside the advisor's authority)
The VM settings of the node and master (raw VBoxManage is denied), and a new baseline snapshot after a cold boot.

## Options
- **A (recommended):** Salatiel looks at the host side, for example a VirtualBox or host-kernel update since 2026-11-18,
  or a cold boot of the node instead of a restore. Then node_base's set is re-run and reviewed.
- **B:** node_base's sweep closes with the ntp check recorded as untestable on this lab while the clock runs fast, and
  the approval report lists it.

## 2026-11-24: measured again on resume (HQ ruling 0 of the resume): the drift remains; stopped
- **HQ's premise:** the rulings say the laptop had been through a cold boot. It had not: `uptime -s` gives
  2026-11-22 21:17:07, the same host boot as the 2026-11-23 measurements (`uptime` at 12:04: up 1 day, 14:46).
  Host unchanged: Linux 7.0.0-22-generic, VirtualBox 7.2.6_Ubuntur172322.
- **Rates over 300 s** (`lab_power.sh up`, then each VM's /proc/uptime read twice 300 s apart over lab_exec against
  the laptop's; each read took 0.8-1.9 s):
  - node (puppet8node, freshly reverted): laptop 301.67 s, node 309.06 s, ratio 1.0245;
  - master (puppet8master, clocksource tsc): laptop 301.16 s, master 308.65 s, ratio 1.0249; its timesyncd offset
    then -724.271 ms, jitter 18.952 ms.
- **Stopped** under the ruling: no time-based check runs on a drifting clock. The lab is down.

### Sweep runs on this boot whose expectations depend on a duration (all of the sweep's runs were made on it)
To re-run, author and reviewer, once the clocks keep time:
- **ssh_secure:** an-idle-session-is-ended-after-the-interval (29-45 s), on-redhat-an-idle-session-is-not-ended
  (60 s, rhel9).
- **gnome_lock_screen** (its review PASS too): a-gnome-session-locks-after-the-idle-time (60 s idle plus 10 s
  grace, under 300 s, gnome node).
- **node_base:** ntp-keeps-the-time (review held).
- **firewall_secure:** a-burst-of-new-ssh-connections-is-cut-at-the-limit, held-connections-stop-at-eight and
  new-connections-stop-at-fifteen-a-minute (iptables limit and recent windows on the node's clock, the peer's
  pacing on its own).
- **firewall_secure_extra:** a-whitelisted-source-is-held-to-the-new-connection-rate, icmp-echo-is-rate-limited,
  an-ssh-burst-is-cut-at-the-overall-limit, held-ssh-connections-stop-at-eight,
  new-ssh-connections-stop-at-fifteen-a-minute, the-rst-limit-dropped-the-third.
- **docker_container:** the-service-starts-it-again (within 60 s).
- **sync:** the-script-mirrors-the-remote-dir (transfer timed against the bandwidth limit).
- **sysmon_base:** the-cpu-plugin-is-critical-under-load (20 s), the-latency-check-times-a-write (5 s),
  the-bandwidth-check-reports-throughput and the-bandwidth-check-is-critical-above-its-threshold (1 s samples).
  a-stale-package-list-raises-the-alarm compares a file's age with the node's own clock, so the rate does not enter
  it.
The rhel9, ubuntu2 and gnome nodes' rates were not measured; the checks above that run there are listed by kind.

## 2026-11-24: after a cold boot of the laptop (HQ): the drift is gone
- **Host:** booted 2026-11-24 12:24:51 (`uptime -s`); kernel and VirtualBox unchanged (7.0.0-22-generic, 7.2.6).
- **Rates** (`lab_power.sh up`; rhel9, ubuntu2 and gnome started with lab_vm.sh; each VM's /proc/uptime read at the
  start and end of one 300 s window against the laptop's; reads took 0.8-2.3 s, so about ±0.6%):
  node 1.0020 (again over 300 s: 1.0015), master 1.0006, rhel9 1.0001, ubuntu2 1.0003, gnome 0.9999.
- **Time sync on the VMs then:** timesyncd on the node, master and ubuntu2 at its +500 ppm frequency limit with offsets
  +142.571, +155.426 and +144.044 ms; gnome +43.339 ms; chrony on rhel9 0.0037 s slow, estimating the raw clock
  4676.815 ppm slow (skew 13.758 ppm), which chrony corrects. The uptime method cannot resolve rates within ntpd's
  500 ppm; node_base's ntp check is the finer test.
- The duration-dependent runs listed above are re-run, by author and reviewer (HQ, after the cold boot).

## 2026-11-24 (later): measured precisely, four VM clocks still drift, at -0.465%: reopened
- **What showed it:** the node_base re-run after the cold boot (results/node_base/20261124T124342Z-author) failed
  `ntp-keeps-the-time` again: ntpsec active, its server configured, a source selected (`*`) within 60 s, but
  `timedatectl` NTPSynchronized `no`. The uptime method above resolves about ±0.6% (6000 ppm), so it could not see a
  drift beyond ntpd's 500 ppm; the "keep time" above holds only at that resolution.
- **Method:** a script on each VM took 8 SNTP samples (ntp.ubuntu.com) at the start and 8 at the end of a 900 s window,
  kept the lowest-delay sample of each, and compared CLOCK_MONOTONIC_RAW (not slewed by any time daemon) with the
  server's time. Bound: half the round-trip delays over the window.
- **Rates (raw seconds per server second), 2026-11-24 14:34-14:50 UTC, all five VMs running:**
  - node (puppet8node): 0.995346 (-4654 ppm, ±232);
  - master (puppet8master): 0.995341 (-4659 ppm, ±208);
  - rhel9: 0.995344 (-4656 ppm, ±222); chrony's own estimate then: 4674.733 ppm slow;
  - ubuntu2: 0.995355 (-4645 ppm, ±219);
  - gnome: 1.000000 (-0 ppm, ±221).
- **Time sync then:** timesyncd on the node, master and ubuntu2 at its +500.000 ppm limit with offsets +137.654,
  +174.666 and +160.752 ms; gnome -24.366 ppm, +47.505 ms; chrony on rhel9 (which corrects up to 100000 ppm) 0.003 s
  fast. ntpsec and timesyncd correct at most 500 ppm, so on the four drifting VMs they cannot hold the clock.
- **VM settings (VBoxManage showvminfo, read-only):** the four drifting VMs have paravirtprovider `default`
  (effective `kvm`) and BIOS firmware; gnome, the one that keeps time, has `hyperv` and EFI. CPUs (2), cpu-profile
  host, hwvirtex, nestedpaging, largepages, vtxvpid, vtxux, hpet off, x2apic on and chipset piix3 are the same on all
  five; the guest clocksource is tsc on all five. A lead for the VirtualBox side, not a finding.
- **Before the cold boot** the same four kinds ran +2.45% fast (above); the sign and size changed with the host boot.

### Status under HQ's cold-boot instruction ("If the drift is still there ... hold everything on your list")
- Held: node_base's review and the reviewer re-runs of every set listed above; no new duration-dependent run.
- Already made after the cold boot, before this measurement (author runs, committed): gnome_lock_screen ALL_PASS (on
  gnome, which keeps time), firewall_secure ALL_PASS, firewall_secure_extra FINDINGS (only the ruled RST finding),
  docker_container ALL_PASS, sync ALL_PASS. They ran on a clock 0.465% slow; HQ decides whether they stand.
- node_base, ssh_secure and sysmon_base: their rhel variants were ENVIRONMENT_FAILED (the revert's 300 s dnf metadata
  refresh: 173 MB of BaseOS metadata, measured at 849 kB/s and 4 min 02 s by hand on the current uplink); not re-run.
- Going on: HQ rulings 1 and 2 and the reviews that involve no durations.

## 2026-11-24 (HQ, resume on mains power, ruling 2): the experiment, hyperv fixes the drift
- **ubuntu2 with paravirt provider hyperv** (lab_vm.sh modify, powered off), measured with SNTP over 900 s
  (19:02-19:17Z). gnome and the unchanged node ran in the same window:

  | VM | provider | rate | timesyncd |
  |---|---|---|---|
  | ubuntu2 | hyperv | 0.999989 (-11 ppm, ±211) | frequency +10.252 ppm, offset +24.878 ms |
  | gnome | hyperv | 0.999997 (-3 ppm, ±218) | +7.930 ppm |
  | node | kvm | 0.995346 (-4654 ppm, ±203) | +500.000 ppm (at its limit), offset +116.719 ms |

  Provider `none` was not needed.
- **rhel9 with hyperv** (19:19-19:34Z): 1.000007 (+7 ppm, ±215); chrony then estimated 6.585 ppm fast (4674.733 ppm
  slow under kvm).
- **Facts** (`facter virtual is_virtual hypervisors dmi.product.name`): the same on gnome (hyperv), on the node (kvm),
  on ubuntu2 before and after, and on rhel9 under hyperv: `virtual` virtualbox, `is_virtual` true, `hypervisors`
  virtualbox 7.2.6 (r172322), DMI product VirtualBox. Under hyperv the guest no longer offers the kvm-clock
  clocksource; tsc stays the current one on every VM.
- **Applied (2ec8724):** P8LAB_UBUNTU2_BASELINE_v3 (v2 + hyperv, offline) and P8LAB_RHEL9_BASELINE_v3 (v2 + hyperv +
  a fresh dnf cache, one boot, no agent run). Verified by a real revert of each: hyperv after the restore; rhel9's
  revert downloaded 139,911 bytes.
- **Not changed, not measured, still kvm:** p8lab-kubuntu, p8lab-dc and p8lab-puppetserver (their clocks likely drift
  the same way; lab_vm.sh can change them with new baselines if HQ wants). ubuntu-desktop is hyperv already.

## Steps for Salatiel: the master and the node (raw VBoxManage on them is his)
**Step 1 (advisor):** `.codex_state/tools/lab_power.sh down`: the nodes are powered off and the master is shut down
through ACPI.

**Step 2 [HUMAN]: the node, new baseline P8NODE_BASELINE_GREEN_v5.** The restore brings back v4's exact disk state,
undoing the boot the last revert made, so the new baseline is v4 plus the provider and nothing else.
```bash
VBoxManage showvminfo ubuntu24-puppet8-Node --machinereadable | grep -E '^(VMState|paravirtprovider)='   # poweroff, default
VBoxManage snapshot ubuntu24-puppet8-Node restore P8NODE_BASELINE_GREEN_v4
VBoxManage modifyvm ubuntu24-puppet8-Node --paravirtprovider hyperv
VBoxManage snapshot ubuntu24-puppet8-Node take P8NODE_BASELINE_GREEN_v5 --description "P8NODE_BASELINE_GREEN_v4 with paravirt provider hyperv (was default/kvm: the guest clock ran 4654 ppm slow; ubuntu2 under hyperv -11 ppm, SNTP over 900 s, 2026-11-24); taken offline, no boot after the v4 restore"
VBoxManage showvminfo ubuntu24-puppet8-Node --machinereadable | grep -E '^paravirtprovider='              # hyperv
```
Rollback: none needed. v4 is untouched, and nothing uses v5 until step 4's commit.

**Step 3 [HUMAN]: the master** (powered off by step 1; no snapshot here, step 6 takes it):
```bash
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -E '^(VMState|paravirtprovider)='  # poweroff, default
VBoxManage modifyvm Ubuntu24-puppet8-Master --paravirtprovider hyperv
VBoxManage showvminfo Ubuntu24-puppet8-Master --machinereadable | grep -E '^paravirtprovider='             # hyperv
```
Rollback [HUMAN]: `VBoxManage modifyvm Ubuntu24-puppet8-Master --paravirtprovider default` while it is powered off.

**Step 4 (advisor; tool change + tests + shellcheck, own commit):** `.codex_state/lab/nodes.yml` ubuntu
`baseline_snapshot: P8NODE_BASELINE_GREEN_v5`, plus the tests and comments that name v4 as the live baseline.
Rollback: `git revert` that commit.

**Step 5 (advisor):** `lab_power.sh up` starts the master and reverts the node to v5. Then check:
- the provider on both is hyperv;
- puppetserver is healthy;
- the master's and the node's facts are unchanged (hostname, fqdn, domain, `virtual`, `is_virtual`);
- SNTP over 900 s on both;
- node_base's `ntp-keeps-the-time`, the finer test.

A clock that still drifts stops the plan, which is then reported.

**Step 6 (advisor):** `snapshot_master.sh P8MASTER_BASELINE_GREEN_v10`. One snapshot covers both changes since v9: the
lab Hiera without the rsyslog_base binding (48b06e9) and the provider (HQ ruling 6).

**Then:**
- the duration-dependent list above is re-run by author and reviewer (HQ ruling 3: runs made on a drifting clock do
  not count, except gnome_lock_screen's, which ran on gnome);
- the rhel9 runs go in one block within 24 h of a baseline refresh (HQ ruling 5); v3's cache dates from about 19:27Z
  on 2026-11-24, so a later block refreshes first.

## 2026-11-25: the provider everywhere (HQ "experiment accepted"), measured
- **Salatiel's steps 2 and 3** done (node baseline P8NODE_BASELINE_GREEN_v5, master on hyperv). Step 4: 4735218.
- **The other three VMs** (HQ item 2): P8LAB_KUBUNTU_BASELINE_v2, P8LAB_DC_BASELINE_v2 and
  P8LAB_PUPPETSERVER_BASELINE_v2, taken offline with hyperv; their reverts restore hyperv (revert_node.sh checks it).
- **Enforcement** (HQ item 3): 8d5ca2f (nodes.yml `paravirt_provider`, lab_vm.sh, revert_node.sh, lab_power.sh, tests).
- **Step 5, SNTP over 900 s** (2026-11-25 03:53-04:09Z, on AC, all five at once):

  | VM | rate | bound |
  |---|---|---|
  | puppet8master | -4 ppm | +-215 ppm |
  | puppet8node | -5 ppm | +-206 ppm |
  | p8lab-kubuntu | -8 ppm | +-202 ppm |
  | p8lab-dc | -5 ppm | +-220 ppm |
  | p8lab-puppetserver | -1 ppm | +-217 ppm |

  All keep time. Two earlier attempts lost their results: they were written to /dev/shm, which systemd-logind's default
  RemoveIPC=yes empties when the user's last process (the measurement itself) exits. Results now go to /var/tmp.
- **Step 5, node_base `ntp-keeps-the-time`:** pass (results/node_base/20261125T041119Z-author: the base
  run ALL_PASS, `ntp-keeps-the-time` included; variant prod ALL_PASS). Its variant rhel did not apply: the guard of
  Exec[enable-codeready-builder-repo], `subscription-manager repos --list-enabled`, exceeded Puppet's exec timeout and
  the agent run timed out at 600 s. By hand on a fresh rhel9 the same command took 10.6 s (04:41Z), so the variant is
  re-run in the rhel9 block. The plan is not stopped: no clock drifts.
- **Step 6** follows: `snapshot_master.sh P8MASTER_BASELINE_GREEN_v10`.
