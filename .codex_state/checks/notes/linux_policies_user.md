# linux_policies_user: authoring notes (the comments of .codex_state/checks/linux_policies_user.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::linux_policies_user (define; required_base filesystem_base,
# linux_policies_common, user_base p8testuser). It composes <localdir>/linux-policies/USER/<username>.sh from the
# puppet_header template plus one line per policy, and runs the policy runner as the user (ruled guard: only while the
# user has a login session). Fixture (params, never committed): username p8testuser, policies two no-op `true` lines.
# Node kubuntu since 2026-11-17: the set's `session` block logs p8testuser in to Plasma after the apply, then two agent
# runs (Phase 3 desktop sessions); the policies then run on the agent run (the exec) and at the login (linux_policies_
# common's XDG autostart entry, composed through required_base).
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1); checks unchanged.
# Correction round 1, 2026-11-21 (review 20261121T013717Z, purpose): the fixture's policies log what they do (one names
# the user it ran as), so the checks see the policies themselves run as the user; and no policy runs before the
# user's first session (the harness's agent runs come before the login).
# Correction round 2, 2026-11-21 (review 20261121T014847Z, purpose): the login's own policy run is tied to the
# autostart: policy lines logged after the user's session started and before the first agent-run policy line can only
# come from the login (the runner's Executing line is logged before the script's own logged-in check).
# 2026-11-17 authoring correction (Phase 3 review FAIL, 20261117T012929Z): removed `no-policy-run-without-a-session`.
# It expected no linuxint-policies journal line after the agent runs, derived from the comment at manifest line 70;
# the baseline exec (lines 71-75) is unguarded and its script logs "not loged in" on every run, so 0 lines comes from
# the ruled guard (upstream_defects.md linux_policies_user), not from the baseline. Checks derive from the baseline only.
# 2026-11-17 (node kubuntu, desktop session): removed `script-skips-policies-without-a-session` (the guard's quiet side,
# run as the user outside a session); with the session up `who` lists p8testuser, so it cannot hold. The two checks
# below observe the session side, which the 2026-11-17 uncovered note named.
  # Correction round 3, 2026-11-21 (HQ after batch 18, item 1; review 20261121T015754Z): the logged-in line and the
  # policy line are counted from the first agent-run line (t1) on, as the autostart check bounds its own window, so the
  # login's autostart run alone cannot satisfy this check.
```
