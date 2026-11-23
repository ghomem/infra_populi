# Lab: the node's clock runs about 2.5% fast on this host boot (OPEN, for HQ/Salatiel: lab environment)

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
