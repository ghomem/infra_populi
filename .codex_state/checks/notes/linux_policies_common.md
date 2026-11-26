# linux_policies_common: authoring notes (the comments of .codex_state/checks/linux_policies_common.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::linux_policies_common (class; required_base filesystem_base). It deploys
# the linux-policies tree under <localdir>/linux-policies (localdir /opt/puppet-infrastructure, lab Hiera), the runner
# script COMMON/execute_linux_policies_user.sh, and an XDG autostart entry that runs it at desktop log-in. Fixture:
# none (no parameters).
# Not exercised: the desktop log-in that triggers the autostart entry (needs a desktop session).
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1); the old uncovered note in the current form.
# Correction round 1, 2026-11-21 (review 20261121T011850Z, purpose): the runner's syslog line is read, the not-found
# branch is exercised, and two `from` references are corrected to the baseline's lines.
```
