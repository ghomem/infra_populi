# node_base_domain_desktop: authoring notes (the comments of .codex_state/checks/node_base_domain_desktop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::node_base_domain_desktop (class; until 2026-11-23 MOCK-APPLY for
# Service['puppet']: node fixture puppet_agent_standin replaced puppet.service's ExecStart with a sleep).
# Fixture: defaults (the class's own parameters only reach filesystem_base_desktop and filesystem_apt).
# Scope: what this profile itself chooses. Its component classes (packages_base, ssh_secure, firewall_secure,
# firewall_ipv6_drop, filesystem_base_desktop, filesystem_apt) carry their own check sets; here only the parameters
# the profile passes them and the resources it declares itself.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), the IPv6 drop and the APT desktop mode
# the profile chooses, and the uncovered row in the current form.
# Correction round 2, 2026-11-23 (review 20261123T034707Z, purpose): the stand-in was lifted (HQ after batch 20, item 6:
# the harness tolerates a running agent daemon, 6e007df), so the agent-daemon outcome is now tested: the real daemon,
# restarted, makes a catalog run of its own that changes nothing but Exec[apt_update].
  # Correction round 1, 2026-11-21 (review 20261121T040410Z, purpose): the check read only the compatibility link; it now
  # reads the desktop surface list the default selects (the substance of desktop mode), as node_base_desktop's set does.
```
