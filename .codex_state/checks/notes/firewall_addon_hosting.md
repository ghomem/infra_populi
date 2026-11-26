# firewall_addon_hosting: authoring notes (the comments of .codex_state/checks/firewall_addon_hosting.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_addon_hosting (class; required_external firewall; re-migrated
# 2026-11-16 with the ruled upstream-defect fix: OUTPUT accept for the master on 8140, destination
# $server_facts['servername'] resolved on the agent). Fixture: none (no parameters).
# The ruled rule is not baseline text, so its checks cite the baseline lines it complements (the OUTPUT drop policy
# that would otherwise cut the agent) and the ruled change is named in each `what`.
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1), and the traffic as behaviour: DNS and NTP
# still answer (invariants: they answer on the clean node too), a new TCP connection to the internet is dropped, and
# an agent run made through the firewall (node_agent) succeeds. Probes may not name the master; the agent run does.
# Correction round 1, 2026-11-21 (review 20261121T000538Z, purpose): purge => true exercised (an unmanaged OUTPUT rule
# inserted before the agent run is gone after it); the purpose says IPv4 (the class leaves ip6tables alone).
```
