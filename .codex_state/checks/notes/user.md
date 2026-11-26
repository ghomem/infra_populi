# user: authoring notes (the comments of .codex_state/checks/user.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user (define; harness title p8testuser, the user-identity fixture).
# The define is a thin wrapper: it passes its parameters to puppet_infrastructure::user_base and cannot pass
# ignorekey, so user_base's default (ignorekey false) applies and the SSH key IS pushed.
# Fixture (params, never committed): myname "P8 Test User", myhash the SHA-512 hash (salt p8testsalt) of the test
# password p8test-user-not-a-secret (a fake hash until 2026-11-19), mykey = the body of a throwaway RSA public key generated for the fixture (private
# half discarded); defaults: mygrouplist [], myhome '', myhomemode '', user_shell /bin/bash.
# Purpose and outcomes added 2026-11-19 (backfill batch 5, HQ batch-10 rulings 2 and C1), with the password login as
# behaviour (su as an unprivileged account in a pty, as in user_base's set). What user_base does on its own (the purge
# of other keys, the empty-hash refusal, the variants) is checked in user_base's set.
# Correction round 1, 2026-11-19 (review 20261119T180604Z FAIL, purpose): 'no ecryptfs' was in the purpose but in no
# outcome row; a check now shows the account exists and no ecryptfs passphrase file was written for it.
# Correction round 2, 2026-11-19 (review 20261119T181328Z FAIL, purpose): my uncovered row said the variants are
# checked in user_base's set, which is untrue (that set leaves them untested too); the row is split into what
# user_base's set covers, the untested variants, and a login with the pushed key.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the purge behind the wrapper is checked here (an agent run after a
# planted key); the passed-on parameters are a check in the variant run `locked`; the refusal and the key login name
# what is missing.
# 2026-11-23 authoring correction (sweep run 20261123T130803Z-author): the key-prefix probes of the locked variant
# printed field 2 of every line of authorized_keys, the three `# HEADER:` comment lines Puppet's ssh_authorized_key
# provider writes included; they now skip comment and empty lines, as the set's other key probes do. The keys were as
# the baseline makes it (userlocked...).
# Correction round 1 of the swept set, 2026-11-25 (review 20261125T065618Z FAIL, derived_from and purpose): the
# planted key's mutates now names the key pair its action writes under /run; the variants row's keyless placeholder is
# a check in the variant run `emptykey` (the set's fixture with mykey '').
```
