# firewall_addon_xrdp: authoring notes (the comments of .codex_state/checks/firewall_addon_xrdp.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_addon_xrdp (class; node ubuntu; no parameters, fixture defaults).
# An add-on to a base firewall (firewall_secure's INPUT drop and the IPv6 drop): it opens xrdp's port 3389 over IPv4 and,
# over IPv6 loopback, VNC's port 5900 with its established replies, so xrdp can reach the local VNC server (its comment:
# xrdp tries VNC over IPv6 first and treats a dropped IPv6 connection as no failure). Applied alone here the node's
# policies stay ACCEPT, so the exercises first set the DROP policies the add-on is meant to sit on (declared in each
# action; IPv4 keeps an accept for established traffic and port 22 so the harness's SSH stays up, as the base firewall
# does). Rule texts read from the applied node (HQ batch-11 ruling 4). Node probes name no other host; the peer's probe
# names only the class node's host-only address.
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1). Prototyped on the node.
```
