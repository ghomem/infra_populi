# firewall_ipv6_drop_policy_desktop: authoring notes (the comments of .codex_state/checks/firewall_ipv6_drop_policy_desktop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_ipv6_drop_policy_desktop (class; plan node ubuntu; no parameters,
# fixture defaults). Written 2026-11-19 (backfill batch 5), on the pattern of firewall_ipv6_drop's set: the peer
# (ubuntu2) tries the node over IPv6 on the host-only link (the node hands over its link-local address and MAC; the
# INPUT drop also drops neighbour discovery, so the peer adds a static neighbour entry) and routes IPv6 through it. This
# variant drops by chain policy (no drop rule to count: the FORWARD policy counter is read), accepts IPv6 on lo (::1
# must work on the node), and purges unmanaged IPv6 rules (a planted rule must be gone after an agent run).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1d): the desktop login under the drop policy is now a check in the
# variant run `desktop` on the kubuntu node (a fresh user's automatic Plasma login through SDDM).
```
