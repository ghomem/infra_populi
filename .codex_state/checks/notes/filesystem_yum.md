# filesystem_yum: authoring notes (the comments of .codex_state/checks/filesystem_yum.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::filesystem_yum (class; node rhel9 since 2026-11-18: production declares it
# only in node_base's RedHat branch, and its scripts call /usr/bin/yum, which Ubuntu lacks). Fixture: defaults (the
# class has no parameters); filesystem_base's lab Hiera puts the scripts in /opt/puppet-infrastructure/bin. The rhel9
# node is registered (BaseOS + AppStream), so the update scripts reach Red Hat's repositories. Probes read the node's
# own files and run its package manager.
# Outcomes table added 2026-11-19 (backfill batch 4, HQ batch-10 ruling 2).
  # 2026-11-18 authoring correction (run 1, 20261118T125339Z): on RHEL 9, `yum update` (dnf) exits 1 for a package
  # that is not installed ("Package nginx available, but not installed"), so the script prints "error updating
  # package" for nginx and httpd, which the node lacks; the installed ones were updated. The expectation now allows
  # error lines only for packages that are not installed. The behaviour is unchanged (noted in the purpose triage).
  # 2026-11-18 derivation correction (review 20261118T131226Z): the pending-update query ran in the action, so the
  # effect only repeated the action's output; the effect now queries dnf itself.
```
