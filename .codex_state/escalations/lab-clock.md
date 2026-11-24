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
