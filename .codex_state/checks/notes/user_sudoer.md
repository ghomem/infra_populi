# user_sudoer: authoring notes (the comments of .codex_state/checks/user_sudoer.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_sudoer (define; harness title p8testuser, the user-identity fixture).
# The wrapper appends the admin group to the group list (sudo; wheel on RedHat) and passes everything to user_base.
# Fixture (params, never committed): myname "P8 Test User", myhash the SHA-512 hash (salt p8testsalt) of the test
# password p8test-user-not-a-secret (user's fixture hash; a fake hash until 2026-11-20), mykey = the body of a throwaway
# RSA public key (private half discarded); defaults otherwise (ignorekey false: the key is pushed).
# Node: ubuntu (Debian branch). The RedHat branch (wheel) is an uncovered row.
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1), and the purpose as behaviour: the user
# becomes root with sudo and its password, a wrong password is refused, and an account outside the admin group is too.
```
