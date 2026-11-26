# firewall_addon_openvpn_server: authoring notes (the comments of .codex_state/checks/firewall_addon_openvpn_server.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_addon_openvpn_server (class; params fixture).
# Fixture: lan_bridge_iface p8test1 (production default br0), wan_iface p8test0 — interfaces that do not exist on the
# node, so the rules are installed but carry no traffic. client_isolation (default true) is not used by the code.
# Required external (plan): class firewall (puppetlabs-firewall 8.3.0). The probes read the installed iptables rules
# and the forwarding sysctl (direct state reads). Real VPN-bridge forwarding needs the bridge and a second host and is
# not tested here.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1d): the client_isolation row names what is missing, with its evidence.
# Purpose and outcomes table added 2026-11-19 (backfill batch 4, HQ batch-10 rulings 2 and C1), with forwarding through
# the node as behaviour: two network namespaces stand for the LAN behind the bridge (p8testlan, through veth p8test1,
# 10.252.1.0/24) and the WAN (p8testwan, through veth p8test0, 10.252.0.0/24), and a stand-in for the base firewall's
# FORWARD default drop is appended after the class's rules. Everything stays on the node.
# Correction round 1 (2026-11-19, review 20261119T050053Z FAIL on purpose): the hairpin outcome (rule 204) was marked
# uncovered for a reason of this set's own fixture (one client on a veth), not a lab limit. p8test1 is now a Linux
# bridge holding two subnets (10.252.1.0/24 and 10.252.2.0/24) with a client namespace in each; a connection between
# them is routed by the node in and back out of p8test1, which only rule 204 accepts ahead of the stand-in drop. The
# client namespaces ignore ICMP redirects so the flow stays routed through the node. br_netfilter is not loaded on
# the clean node (lsmod), so bridged frames do not traverse iptables.
```
