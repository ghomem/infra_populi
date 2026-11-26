# user_samba: authoring notes (the comments of .codex_state/checks/user_samba.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_samba (define; harness title p8testuser; MOCK-APPLY: node fixture
# samba_dc_standin stands in for Zentyal's create-user.pl / set-user-samba-hash.sh and Samba's pdbedit / ldbsearch,
# keeping a fake store under /var/tmp/p8test_samba_standin). Fixture (params, never committed): myname "P8 Testuser",
# mysmbhash a fake base64 value.
# What the stand-in store shows: the define split the name and passed user, first name, last name and hash to the two
# commands, in that order. NOT shown (mock-apply): a real Samba DC account.
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1); the real account as a capability row.
```
