# firewall_ipv6_drop: authoring notes (the comments of .codex_state/checks/firewall_ipv6_drop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_ipv6_drop (class; node ubuntu; no parameters, fixture defaults).
# An add-on to firewall_secure in production (node_base); applied alone here, it adds the two ip6tables DROP rules.
# On the clean node, sshd listens on [::]:22 and the host-only NIC has an IPv6 link-local address, so another machine on
# that link reaches the node over IPv6. The node writes its link-local address to a file the runner hands to the peer
# (ubuntu2); node probes name no other host; peer probes name only the class node's IPv4 host-only address and that
# handed-over link-local address.
  # 2026-11-18 authoring correction (run 1, 20261118T164432Z): the class's INPUT drop also drops neighbour discovery
  # (rule 600 counted 7 packets, FORWARD 0), so the peer never resolved the node's MAC and sent nothing. The node now
  # also hands over its MAC, and the peer adds a static neighbour entry for the node's link-local address.
```
