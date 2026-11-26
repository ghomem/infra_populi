# dns_client: authoring notes (the comments of .codex_state/checks/dns_client.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::dns_client (class; node ubuntu). Fixture (params, never committed; changed
# 2026-11-18 for these checks): nameservers [10.0.2.3, 1.1.1.1], the VirtualBox NAT resolver every lab VM reaches,
# then a public one. The clean node has a static /etc/resolv.conf naming 1.1.1.1 and 8.8.8.8, so the fixture's list,
# order and exclusion of 8.8.8.8 make the class's effect visible.
# 2026-11-18 purpose correction (review 20261118T114959Z): the single-server fixture could not show order or "only
# those", and the empty-list guard was not listed; the fixture now has two servers and the guard is listed below. saz-resolv_conf 8.0.1 renders the file. Probes read the node's own resolver and query through it.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1: variants): the empty-list variant, which node_base passes by
# default to every server, is now a check in the variant run `empty` (params/variants/empty).
# Authoring correction 2026-11-23 (run 20261123T083652Z): the expectation named systemd-resolved's stub, but the
# reverted node's resolv.conf holds static servers; the check now shows the file was not written by the run.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2); the set-level uncovered entry moved into it.
```
