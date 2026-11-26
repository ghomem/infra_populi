# network_dhcp: authoring notes (the comments of .codex_state/checks/network_dhcp.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::network_dhcp (class; node ubuntu; no required base). Fixture (params, never
# committed): iface p8test0 (the fixture interface name; never the node's real NIC). The class installs ifupdown-extra
# and declares network_config p8test0 (puppet-network: a stanza in /etc/network/interfaces, `auto p8test0` / `iface
# p8test0 inet dhcp`). The checks give p8test0 a LAN with a DHCP server: a network namespace p8testdhcp joined to the
# node by a veth pair (p8test0 on the node, p8testsrv 10.251.0.1/24 in the namespace) and dnsmasq serving
# 10.251.0.100-150 there. Then the step a boot runs for /etc/network/interfaces (the networking service, or ifup -a)
# is run, whichever the node has. Everything stays on the node.
# 2026-11-20, HQ batch-15 ruling 5 (local change #10): production runs ifupdown beside netplan (openvpn_server installs
# it on the same servers); the class now declares ifupdown itself (ensure_packages). New checks: ifupdown and the
# networking service, the address through a restart of networking, and the primary interface still carrying the
# node's internet. Measured on the node 2026-11-20: ifup uses dhcpcd (dhcpcd-base), and the fixture's DHCP route
# comes at metric 1005, behind the NAT route's 100.
```
