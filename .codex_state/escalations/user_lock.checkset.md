# user_lock — the check set after the stand-in lift: purpose FAIL past the correction cap (OPEN, for HQ)

Phase 1 PASS (review 20261123T014847Z). The set after the lift (7175bca: on the master-role node, the user created by
hashman itself) ran ALL_PASS (14522e1); Phase 3 review 20261123T015435Z reproduced it and found no behaviour finding.

## The gap (purpose)
Outcome 1 says the lock also invalidates the user's Samba hash. Under the new fixture, check
`the-samba-hash-is-locked-too` cannot tell user_lock's lock from the fixture's state: hashman's `useradd` expires the
new password (`expirepw`), and `mk_smb_lockness` prefixes the Samba hash of an expired entry with '!'
(miscutils.py.erb:137-142). The fixture's `pp_auth.py unlock` removes the Unix lock only; the entry stays expired
(`$!6$`), so the Samba hash is already '!'-prefixed before user_lock runs, and lockpw returns it unchanged. The check
would pass if the lock never touched the Samba hash. The old seeded stand-in did not have this property; the lift
introduced it.

## Why escalated
The set used its two correction rounds on 2026-11-21 (production use 0: cap two); this would be a third.

## The fix I would make (one clear change, in the test-asset fixture)
After `unlock`, the fixture runs hashman's own `pp_auth.py unexpire p8testuser`, so before the lock the user is
neither locked nor expired and its Samba hash is valid (no '!'); the Unix entry then reads `$6$...`. The checks follow:
the locked Unix entry is `'!$6$...'`; the Samba check also shows (through the clean phase or a read before the apply
in the fixture's own output) that the hash had no '!' before the lock; the refusal check stays, with the plain
`$6$` form. Then the run and one more Phase 3 review.

- **For HQ:** allow that third round, or let the set stand with the Samba part as an open row.
