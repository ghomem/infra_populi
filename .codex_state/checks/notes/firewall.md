# firewall: authoring notes (the comments of .codex_state/checks/firewall.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall (class; node ubuntu; required_base filesystem_base; required_external
# firewall, the module's base class that saves the rules for the boot). No parameters (fixture: defaults). The class's
# own comment recommends firewall_secure instead; this is the plain base firewall: drop by default, ICMP and SSH from
# any host, unmanaged rules purged, the emergency flush script. Adapted from firewall_secure's reviewed set (the same
# peer probes, purge, flush and rebuild); firewall has no whitelist or rate limits. Node probes name no other host; peer
# probes name only the class node's host-only address.
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1).
# Correction round 1, 2026-11-21 (review 20261121T144541Z, purpose): rule 003 exercised, an outbound connection from the
# node to the peer's SSH port (P8_PEER_ADDR) gets its replies, counted by the rule.
```
