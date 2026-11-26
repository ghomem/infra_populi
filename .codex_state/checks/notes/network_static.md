# network_static: authoring notes (the comments of .codex_state/checks/network_static.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::network_static (class; node ubuntu; 0 production statements). Fixture
# (params, never committed): iface p8test0 (the fixture interface name), ipaddress 192.0.2.10, gateway 192.0.2.1 (a
# documentation address since 2026-11-20; it was on the home LAN's prefix). Written 2026-11-20 (HQ batch-15 ruling 5,
# local change #11): ifupdown is declared as for network_dhcp. The checks give p8test0 a LAN: a network namespace
# p8testgw joined to the node by a veth pair (p8test0 on the node, p8testgwif 192.0.2.1/24 in the namespace). Measured on
# the node 2026-11-20 (the class applied, ifupdown installed by hand): the stanza has no netmask and ifupdown gives
# p8test0 192.0.2.10/24; /etc/network/routes reads `default 0.0.0.0 192.0.2.1 eth0`, and ifupdown-extra's
# 20static-routes installs no default route for p8test0, because the class names eth0 (baseline :13), which Ubuntu 24.04
# does not have. The route check expects the baseline's purpose and fails: a finding, escalated.
# 2026-11-20, local change #12 (HQ: keep and fix): the route uses $iface. The class's default route through p8test0
# now takes the node's default route (by design: the class configures the node's primary interface), so the last
# check reads that the NAT route stays behind it and the host-only route stays; the node is reverted after every run.
```
