# caching_nameserver: authoring notes (the comments of .codex_state/checks/caching_nameserver.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::caching_nameserver (class; node ubuntu; no required base). Fixture (params,
# never committed): allowed_networks ["192.168.56.0/25"], which holds the node's host-only address (.20) and the peer's
# +100 address (.124) and leaves out the peer's +150 address (.174). The template uses the list both for listen-on
# (bind listens on its local addresses that match) and for allow-query and allow-query-cache. The peer (ubuntu2) asks
# from inside and from outside the list; peer probes name only the class node's host-only address and compute their
# own addresses. Recursion goes out through the lab's NAT uplink.
# 2026-11-19, HQ batch-14 ruling 5 (keep the IPv4-only fixture for the lab): the lab IPv6 fixture also runs named
# with -4, as network_vpn's does. Removing the route alone left named spending its max-recursion-queries (50) on
# IPv6 attempts that fail at once (measured on network_vpn's node: SERVFAIL for www.debian.org, 49 of the 50
# queries IPv6; with -4 every name resolved). On an IPv4-only production host the same limit is an approval
# condition (approval_conditions.md #2), not something this lab can show.
# 2026-11-19, HQ batch-15 ruling 6 (local change #9): the production VPN server has no global IPv6 address, so
# the IPv4-only condition became a finding. The lab fixture no longer sets -4: the class does, on a host without
# a 2000::/3 address (Facter reports the NAT's unique-local fd17:... address as scope global, so the class reads
# the address itself). New checks: named runs -4 on this IPv4-only node, and the names that failed resolve cold,
# with no retries (the cache check below retries, which would hide an intermittent SERVFAIL).
  # Correction round 1 (2026-11-19, run 20261119T042407Z): recursion failed in the lab because named sent its queries
  # over the VirtualBox NAT's IPv6 (a ULA address with a default route learned by router advertisement), which reaches
  # no internet (tcpdump: 27 queries out to root servers' IPv6 addresses, 0 answers); a lab-environment fixture now
  # removes that route, stops advertisements re-adding it, restarts named, and waits until it resolves a name the
  # checks do not ask (its first wait, on the root hints' answer, ended before named could resolve: run 20261119T042847Z).
  # 2026-11-19 authoring correction (run 20261119T043144Z): the first question timed out once more on the lab's IPv6
  # (www.debian.org's servers have many IPv6 addresses); it is asked up to 10 times, 3 s apart, before the cache test.
```
