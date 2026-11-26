# users_sudoers: authoring notes (the comments of .codex_state/checks/users_sudoers.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::users_sudoers (define; harness title users_sudoers). It creates one
# user_sudoer per entry of `configs` except the names in `unmanaged_users`. Fixture (params, never committed): configs
# for p8testuser (the user-identity fixture: fake hash, throwaway RSA key) and p8testuser2, unmanaged_users
# [p8testuser2].
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1). The managed entry's hash is now the user
# classes' known test password (p8test-user-not-a-secret), so sudo is exercised; p8testuser2's stays fake. An unmanaged
# account made by hand is left alone by the node's agent run.
```
