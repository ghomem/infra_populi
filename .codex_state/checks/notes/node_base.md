# node_base: authoring notes (the comments of .codex_state/checks/node_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::node_base (class; node ubuntu; fixture params: ssh_acl [the laptop's
# host-only address], everything else at its default; lab Hiera: ntp::servers [pt.pool.ntp.org],
# filesystem::restricted_group_ubuntu sudo). node_base composes the base classes; each component's own behaviour is
# checked in its own set (packages_base, sysmon_base, ssh_secure, firewall_secure, firewall_ipv6_drop, filesystem_base,
# filesystem_lib64, filesystem_apt, filesystem_sec, dns_client). These checks cover what node_base itself decides:
# which components it applies on this OS, the parameters it passes them, and the NTP service it adds. Values were read
# on the node after one harness apply (2026-11-18, before writing them).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the RedHat branch and the parameters production sets are checks in
# the variant runs `rhel` and `prod`; custom NTP, nameservers and the extra firewall are an accepted gap.
# 2026-11-23, ntp-keeps-the-time in the sweep: it failed in runs 20261123T132939Z (a source selected, the clock not
# synchronised) and 20261123T142843Z (with a 105 s wait tried as an authoring correction: no source). Measured by hand the
# same day (node_base applied on a reverted node, ntpq every 10 s for 600 s): ntpsec reached its server at once, stepped
# the clock by -0.808363 s, selected the server from 10 s to at least 81 s, and selected nothing from 143 s on; ntpq gave
# offset -13125.3 ms then -14723.6 ms with jitter 6880.704 ms then 6949.192 ms, and the node's wall clock read about
# 5.5 s ahead of the laptop's synchronised clock. The node's own clock was unstable that day, not the class's NTP
# configuration (it passed on 2026-11-18, runs 20261118T193806Z and 20261118T194317Z). The wait was a wrong diagnosis
# and is withdrawn; the check is unchanged from its review.
# Correction round 1 of the swept set (2026-11-25, review 20261125T113935Z, purpose): the prod check read the same
# whether node_base forwards firewall_strict_purge false and the ignore patterns or not; the prod variant now plants two
# unmanaged rules, one matching p8test-keep, and the next agent run keeps that one and purges the other (as
# firewall_secure's keep variant). Every forwarded parameter production does not set is in the accepted-gap row.
# 2026-11-25 (review 20261125T125545Z of ssh_secure): the accepted-gap row no longer says each component's own set
# covers these parameters; ssh_secure's set, for one, leaves the SSH ones in its own accepted gap.
```
