# firewall_ipv6_drop_policy: authoring notes (the comments of .codex_state/checks/firewall_ipv6_drop_policy.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_ipv6_drop_policy (class; node ubuntu; no parameters, fixture
# defaults). An add-on to firewall_secure: the IPv6 INPUT and FORWARD chains get the policy DROP and their unmanaged rules
# are purged (no accept rule at all, unlike firewall_ipv6_drop_policy_desktop's loopback rule). On the clean node sshd
# listens on [::]:22 and the host-only NIC has an IPv6 link-local address, so another machine on that link reaches the
# node over IPv6. Adapted from firewall_ipv6_drop's reviewed set (the node hands its link-local address and MAC to the
# peer ubuntu2; node probes name no other host; peer probes name only the class node's IPv4 host-only address and that
# handed-over link-local address).
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1).
# Correction round 1, 2026-11-21 (review 20261121T150624Z, purpose): the purge shown on FORWARD as well as INPUT.
  # Carried over from firewall_ipv6_drop's set (its 2026-11-18 correction there): an IPv6 INPUT drop also drops neighbour
  # discovery, so the node hands over its MAC and the peer adds a static neighbour entry for the node's link-local
  # address. Here the INPUT policy does the dropping (this class has no rule).
```
