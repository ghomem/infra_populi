# firewall_addon_caching_nameserver: authoring notes (the comments of .codex_state/checks/firewall_addon_caching_nameserver.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_addon_caching_nameserver (class; node ubuntu; no required base).
# Fixture (params, never committed): lan_iface p8test0 (the fixture interface name; never the node's real NIC), port
# at its default 53. The class adds one rule, 1301: accept UDP to the port arriving on the LAN interface (chain INPUT
# by the firewall type's default). The checks give p8test0 a client: a network namespace p8testns joined to the node by
# a veth pair (p8test0 10.250.0.1/30 on the node, p8testpeer 10.250.0.2/30 in the namespace), UDP responders on
# 10.250.0.1:53 and :5353, and a stand-in for the base firewall's default drop (the class is complementary, like
# firewall_addon_web) appended after the class's rule: UDP to 53 and 5353 arriving on p8test0 is dropped. Everything
# stays on the node.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1c): the port variant is an accepted gap (production does not set it).
```
