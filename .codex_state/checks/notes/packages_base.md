# packages_base: authoring notes (the comments of .codex_state/checks/packages_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::packages_base (class; node ubuntu; required_external none of its own: it
# declares class apt itself). Fixture: defaults (unattended_upgrades false). On Ubuntu the class declares
# `class { 'apt': update => { frequency => 'always' } }`, installs the Debian package list, removes supervisor and
# cloud-init and keeps unattended-upgrades off. The clean node has cloud-init, unattended-upgrades, vim and wget, and
# lacks aptitude, acl, monitoring-plugins-standard, ecryptfs-utils and iptables-persistent (node inventory
# P8NODE_BASELINE_GREEN_v4). Probes read the node's own packages, tools and Puppet's last run report.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): unattended_upgrades true (a production node sets it) and the RedHat
# branch on rhel9 are checks in the variant runs `unattended` and `rhel`.
# Correction round 1, 2026-11-23 (review 20261123T120924Z, purpose): the RedHat run also checks vim (vim-enhanced) and
# dnf makecache on every run; unattended_upgrades true on RedHat (dnf-automatic) is the variant run `rhel-unattended`.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2); the set-level uncovered list moved into it.
  # 2026-11-19 authoring correction (run 20261119T011742Z): Puppet 8 leaves unchanged resources out of the run report
  # (exclude_unchanged_resources true, read on the node), so the exec is looked for in the catalog's resource list and
  # its absence from the report means it made no change.
```
