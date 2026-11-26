# user_base: authoring notes (the comments of .codex_state/checks/user_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_base (define; harness title p8testuser, the user-identity fixture).
# Fixture (params): myname "P8 Test User", myhash the SHA-512 hash (salt p8testsalt) of the test password
# p8test-user-not-a-secret, mykey a test RSA public key, ignorekey false; defaults: mygrouplist [], myhome ''
# (/home/p8testuser), myhomemode '', user_shell /bin/bash, no ecryptfs passphrase (the ruled exec-guard branch,
# user_base.pp:108-135, needs an ecryptfs home that the lab node lacks). Until 2026-11-19 the fixture had a fake hash
# and ignorekey true.
# Purpose and outcomes added 2026-11-19 (backfill batch 5, HQ batch-10 rulings 2 and C1). The fixture moved closer to
# the defaults: ignorekey false (the default) with a test RSA public key as mykey (the class always writes ssh-rsa;
# the private half is not kept anywhere in the repository), and myhash is now the SHA-512 hash (salt p8testsalt) of
# the test password p8test-user-not-a-secret, a lab fixture like the relay password, so the password can be used.
# The login with the password runs su as an unprivileged account in a pty (root's su asks no password), the password
# sent 2 s in (su flushes earlier input: measured 2026-11-19, both passwords refused without the delay).
# Correction round 1, 2026-11-19 (review 20261119T172145Z FAIL, purpose): the empty-hash refusal (:19-22) was in the
# purpose but in no outcome row. It is a row of its own now, uncovered (compile time), with a compile-only run as its
# evidence (the params fixture's myhash blanked for that one compile and restored, sha256 unchanged).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): a locked hash with other home, shell and groups, and an empty key
# (undeterminable production use: the passwd/ layer) are checks in the variant runs `locked` and `emptykey`; the
# compile refusal, the key login and ecryptfs name what is missing.
# 2026-11-23 authoring correction (sweep run 20261123T130519Z-author): the key-prefix probes of the locked and emptykey variant
# printed field 2 of every line of authorized_keys, the three `# HEADER:` comment lines Puppet's ssh_authorized_key
# provider writes included; they now skip comment and empty lines, as the set's other key probes do. The keys were as
# the baseline makes them (userlocked..., emptykey...).
# Correction round 1 of the swept set, 2026-11-25 (review 20261125T063430Z FAIL, purpose): the ignorekey branch
# (user_base.pp:93-102, for encrypted homes) was in no row. The purpose names it, and the variant run `ignorekey` (the
# base fixture with ignorekey true) checks that no key is then written.
```
