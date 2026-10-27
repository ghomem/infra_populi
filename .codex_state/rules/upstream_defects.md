# Upstream defects fixed locally — registry and CTO batch (HQ checkpoint-1 ruling 3)

One entry per class whose tracker marker is (or will be) `[from: release-0.9.10; upstream defect fixed: <short>]`.
The reviewer reads this file: with that marker, DIFF A may contain EXACTLY the change in the entry's `Ruled change`
(plus ordinary Puppet 8 translations); anything else fails. `Status` is one of:
`ruled` (HQ ruled the fix; apply when the class is migrated), `applied <commit>`, `pending HQ` (escalated, not
authorized). Each entry is batched for the CTO (upstream maintainers) as a fix to take upstream.
The escalation files hold the evidence; this file holds only what the reviewer and the CTO need.

## filesystem_sec
- Short: default group assigned to a new variable (no parameter reassignment)
- Defect: the default branch (`restricted_group` = '') reassigns the parameter `$restricted_group`; Puppet 8 refuses
  (`Cannot reassign variable '$restricted_group'`, filesystem_sec.pp default-param compile, sprint step 2.2). The
  branch has never compiled on Puppet 8; production nodes that rely on the default would fail.
- Ruled change (HQ ck1 ruling 6): assign into a new variable instead — `$restricted_group_real` = 'wheel' (RedHat) /
  'sudo' (other) when the parameter is '', else the parameter; `file { $restricted_cmds: group => $restricted_group_real }`.
  Same values on every branch; no other line changes.
- CTO note: every production node must pass `restricted_group` explicitly until upstream takes the fix.
- Status: applied 929062b (reviewer v2 PASS 2026-10-27)

## puppet_boot_run
- Short: ensure dropped
- Defect: upstream 4ae2e35 adds `ensure => running` to a Type=oneshot unit without RemainAfterExit; the unit is
  inactive after each start, so every agent run restarts it (`ensure changed stopped to running`) — never idempotent,
  and a unit whose job is to run the agent is started from inside an agent run.
- Ruled change (HQ ruling 8, provisional; intent check passed, escalations/puppet_boot_run.md): drop `ensure =>
  running` from the service; keep `enable => true`. No other line changes.
- Status: ruled

## openvpn_nm_connection
- Short: fqdn_rand_uuid replaced by stdlib fqdn_uuid
- Defect: calls `fqdn_rand_uuid`, which is defined nowhere (not stdlib 4.25.1/9.x, not any module; production master
  inspected 2026-09-30) — the class cannot compile anywhere.
- Ruled change (HQ ck1 ruling 3 names fqdn_rand_uuid for this marker): `fqdn_rand_uuid(<args>)` → stdlib
  `fqdn_uuid(<same seed argument>)`; no other line changes.
- Status: ruled (the class is still blocked for other reasons: see blocked.txt)

## user_base
- Short: exec guarded by its post-condition
- Defect: `exec { "${ecryptdir}/wrapped-passphrase": ... }` has no unless/onlyif/creates/refreshonly at the
  baseline, so it runs on every agent run (gate v2 RED by design).
- Ruled change: PENDING — HQ ck1 ruling 2 (option a, per class) requires a guard that tests the command's
  post-condition; the proposed guard is in escalations/user_base-exec-guard.md and waits for HQ confirmation.
- Status: pending HQ

## user_lock, linux_policies_user, mysql_server
- Short: exec guarded by its post-condition
- Defect: unguarded exec at the baseline (pregate hazard 9). mysql_server: upstream 874f854 (unreleased Issue #122
  rewrite) does NOT guard it — it moves the same unguarded `generate the ssl certificates...` exec verbatim into the
  new mariadb_server.pp:99-102 and leaves mysql_server.pp with only a refreshonly AppArmor reload.
- Ruled change: none yet — one escalation per class follows HQ's confirmation of the user_base format (ck1 ruling 2).
- Status: pending HQ
