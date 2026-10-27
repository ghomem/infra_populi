# user_base: unguarded exec at the baseline — post-condition guard (HQ ck1 ruling 2; ruled)

Status: RULED (2026-10-27) — HQ production-facts ruling 2 (upstream defects fixed in infra_populi with the marker,
no escalation) read as confirming this guard; flagged at checkpoint 2. The other exec guards are entries in
`.codex_state/upstream_defects.md` (user_lock, mariadb_server ruled; linux_policies_user pending HQ — no post-condition).
Class content: identical to release-0.9.10 (cf477c6). Production use: 3 node statements, plus it is the base of the
whole user* family (the p8testuser fixture account).

## The command (manifests/user_base.pp:119-133, baseline text)
Only inside `if ( $ppsigs != '' ) and ( $ppwrapped != '' )` (an ecryptfs user):
```puppet
file { "${ecryptdir}/wrapped-passphrase.b64":            # content => $ppwrapped (base64), mode 0600, owner user
  ...
  notify  => Exec[ "${ecryptdir}/wrapped-passphrase" ],
}
exec { "${ecryptdir}/wrapped-passphrase":
  command => "cat ${ecryptdir}/wrapped-passphrase.b64 |base64 -d > ${ecryptdir}/wrapped-passphrase",
  user    => $myusername,
  path    => [ '/usr/local/bin/', '/bin/', '/usr/bin/' ],
  require => File[ "${ecryptdir}/wrapped-passphrase.b64" ],
}
```
No unless/onlyif/creates/refreshonly: it rewrites `wrapped-passphrase` on EVERY agent run (gate v2 RED by design;
pregate hazard 9). Its effect: `${ecryptdir}/wrapped-passphrase` = base64-decode of the .b64 file, re-asserted every run
(so an out-of-band change or deletion is repaired at the next run).

## Proposed guard — tests exactly that post-condition
```puppet
  unless  => "sh -c \"base64 -d < ${ecryptdir}/wrapped-passphrase.b64 | cmp -s - ${ecryptdir}/wrapped-passphrase\"",
```
(one added line; the command, user, path, require and the File's notify are unchanged.)

## Why the effect is unchanged
- The command runs exactly when the post-condition is false: wrapped-passphrase missing or different from the decoded
  .b64. When it is true, the command would rewrite identical bytes — a no-op — so skipping it changes nothing on disk.
- Repair of out-of-band changes is preserved (the reason not to use `refreshonly`, which would only react to a .b64
  change and would no longer restore a deleted/altered wrapped-passphrase).
- A refresh from the .b64 file still runs the command when needed: Exec refresh honours `unless`.
- Guard inversion (hazard 5) is safe here: if `cmp`/`base64` were missing the guard exits non-zero and Puppet runs the
  command — i.e. today's behaviour. Both are in coreutils/diffutils on every supported Ubuntu (present on the node).
  The guard runs as the same `user` as the command, which owns both files.

## Determinism check (HQ checkpoint-2 ruling 1)
The command is a PURE DECODE: `cat <.b64> | base64 -d > wrapped-passphrase`. Its output depends only on the bytes of
`wrapped-passphrase.b64` (no time, randomness, environment or other input; `base64 -d` is deterministic), so "the file
already equals the decode of .b64" is exactly the state the command would produce, and skipping the command in that
state cannot change anything. That is what makes `cmp`-against-the-decode a true post-condition guard rather than an
approximation. Confirmed by HQ 2026-10-27 06:10.

## Evidence (REAL lab, 2026-10-27)
- Engine fixture `.codex_state/tools/tests/fixtures/exec_guard_postcondition.pp` = this exact pattern + guard in a p8test
  directory: `test_class.sh --revert-first --fixture exec_guard_postcondition` → run 1 `executed successfully` once,
  run 2 clean → GREEN (gate v2). Then wrapped-passphrase deleted by hand: run 3 `executed successfully (corrective)`
  (repaired), run 4 clean. The unguarded form is RED (fixture `unguarded_exec`, step 1.1).
- Harness consequence for the user family: with the p8testuser fixture (`myppsigs`/`myppwrapped` empty — no ecryptfs)
  the exec is not declared at all: `test_class.sh --compile-only user_base` = COMPILE OK, no Exec in the catalog. So the
  guard is NOT what blocks user_base's harness GREEN; it matters for production users with ecryptfs. Exercising the
  branch on the node would also need `${ecryptdir}` (/home/.ecryptfs/<user>/.ecryptfs), which the manifest never
  declares (created by ecryptfs-setup-private; hazard 4) — a fixture-state gap, separate from the guard.

## Decision requested
1. Confirm the guard (or choose `refreshonly => true` and accept that out-of-band damage is no longer repaired).
2. Done: `.codex_state/upstream_defects.md` entry `user_base` → `ruled`; the class is migrated in the loop with the
   marker `[from: release-0.9.10; upstream defect fixed: exec guarded by its post-condition]`.
