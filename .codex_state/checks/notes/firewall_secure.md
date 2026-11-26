# firewall_secure: authoring notes (the comments of .codex_state/checks/firewall_secure.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_secure (class; node ubuntu; required_base per plan). Fixture
# (params, never committed): acl [the laptop's host-only address (the harness's SSH source), the peer's second
# address (its host-only address + 100, which the peer adds to its own NIC)]; ssh_port 22, strict false, strict_purge
# true and ignore_patterns [] at their defaults; the lab Hiera's firewall::whitelist ['127.0.0.1'].
# From its primary address the peer (ubuntu2) is a host on no list, as any other machine on the network; from its
# second address it is a whitelisted host. Node probes name no other host; peer probes name only the class node's
# host-only address and compute their own second address.
# 2026-11-18 authoring correction (review 20261118T103002Z, purpose gap): the whitelist was tested only as rule text
# and the per-host limits (8 simultaneous, 15 new per minute) were not told apart from the overall limit; three
# behaviour checks now show each (whitelisted-host-is-not-limited, held-connections-stop-at-eight,
# new-connections-stop-at-fifteen-a-minute).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): strict mode, and strict_purge false with ignore_patterns (production
# uses both) are checks in the variant runs `strict` and `keep`; the rule-002 row names what is missing.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2), with three behaviour checks the table
# showed missing (loopback, the flush script and the rebuild after it) and the held-connection check moved to the
# probe helpers with the SSH rules' counters recorded around it (as in firewall_secure_extra's set).
# Correction round 1 of the swept set (2026-11-25, review 20261125T150903Z, purpose): strict mode was checked as rule
# text only. The strict variant's acl now also lists 192.0.2.3, and a check connects to the node's SSH from a network
# namespace behind a veth pair, from that listed address and from an unlisted one (192.0.2.2; RFC 5737 addresses).
  # 2026-11-18 authoring correction (run 2, 20261118T104207Z): the expectation still listed two addresses after the
  # fixture's acl gained the peer's second address; it now lists all three. The behaviour is unchanged.
```
