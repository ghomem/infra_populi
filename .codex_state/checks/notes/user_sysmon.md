# user_sysmon: authoring notes (the comments of .codex_state/checks/user_sysmon.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_sysmon (define; harness title p8testuser; MOCK-APPLY: node fixture
# sysmon_server supplies the naemon user/group and /etc/thruk, /etc/naemon/conf.d/contacts). Fixture (params, never
# committed): myname "Puppet 8 Test User", the SHA-512 hash of the user test password (salt p8testsalt), myemail root@localhost,
# mygrouplist [admins].
# NOT shown (mock-apply): Thruk accepting the login, Naemon loading the contact.
# Note: the template renders the group list with Ruby's Array#to_s (`["admins"]`), as at the baseline.
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1). The fixture hash is now the user classes'
# known test password (p8test-user-not-a-secret), so the Thruk entry is verified with Apache's htpasswd -v.
  # 2026-11-21 authoring correction (run 1, 20261121T133647Z): the params fixture's hash changed to the known test
  # password's (salt p8testsalt, was p8fixture); the expectation follows the fixture. The behaviour is unchanged.
```
