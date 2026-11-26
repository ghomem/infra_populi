# extra_packages_el: authoring notes (the comments of .codex_state/checks/extra_packages_el.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::extra_packages_el (class; routed to the rhel9 node: RHEL 9.5, registered,
# BaseOS + AppStream enabled at the baseline, CodeReady Builder available but off, no content overrides).
# Fixture: none. The revert clears content overrides after every restore (an enabled repository survives a snapshot
# restore on the subscription server), so the clean node starts with CRB off.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1d): the RHEL 8 row names what is missing, with its evidence.
# Purpose and outcomes table added 2026-11-19 (backfill batch 4, HQ batch-10 rulings 2 and C1), with installs from each
# repository as behaviour (the set read repository state only).
```
