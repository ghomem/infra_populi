# firewall_addon_web: authoring notes (the comments of .codex_state/checks/firewall_addon_web.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_addon_web (class; node ubuntu; no parameters, no required base).
# The class adds two accept rules (200 http, 201 https; tcp, chain INPUT by the firewall type's defaults) that are
# COMPLEMENTARY to a base firewall (its comment, lines 3-7), which supplies the default drop. Its plan row has no base,
# so on the lab node the INPUT policy is ACCEPT; the set stands in for the base's default drop with one rule appended
# after the class's (a drop of ports 80, 443 and 8888 on the host-only NIC: no address named, SSH untouched). The peer
# (ubuntu2) connects as any other host on the network; peer probes name only the class node's host-only address.
  # 2026-11-19 authoring correction (run 20261119T041438Z): the sed back-references were written as \\N (escaped twice)
  # and printed literally; they are \N now (here and in the stand-in check).
  # 2026-11-19 authoring correction (run 20261119T041703Z): iptables -S prints a one-word comment without quotes, so
  # the stand-in rule was not matched; the quotes are optional now.
```
