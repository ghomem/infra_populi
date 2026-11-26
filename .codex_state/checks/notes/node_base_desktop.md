# node_base_desktop: authoring notes (the comments of .codex_state/checks/node_base_desktop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::node_base_desktop (class; node gnome; until 2026-11-23 MOCK-APPLY for
# Service['puppet'] with node fixture puppet_agent_standin, as node_base_domain_desktop). Synced to release-0.9.10 on 2026-11-17 (hazard 8).
# Fixture (params, never committed): log_target puppet8master.example.com / 192.168.56.10, manage_gnome_screenlock true;
# defaults: password_authentication false, ssh_allow_root_login false, screenlock 5 min / grace 0, screenlock_users [].
# Scope: what this profile itself chooses; its component classes carry their own check sets.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), the log forwarding the profile chooses,
# and the uncovered rows in the current form.
# Authoring error in run 20261121T031451Z: the rendered forward line has two spaces after *.*, which the first probe
# did not allow; it now matches any whitespace. The configuration was as expected.
# Correction round 1, 2026-11-21 (review 20261121T032544Z, purpose): sentinels for the components the profile applies
# and chooses (firewall_secure, filesystem_base_desktop, filesystem_apt in desktop mode), as node_base's set has.
# 2026-11-23 (HQ after batch 20, item 6, the stand-in lift; not a correction round): the harness tolerates a running
# agent daemon (6e007df), so the agent-daemon outcome is now tested: the real daemon, restarted, makes a catalog run
# of its own that changes nothing but Exec[apt_update].
```
