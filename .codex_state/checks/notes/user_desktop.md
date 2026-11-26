# user_desktop: authoring notes (the comments of .codex_state/checks/user_desktop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_desktop (define; harness title p8testuser, the user-identity fixture).
# The wrapper builds the group list [<given>, <title>, cdrom, dip, plugdev, lp], passes everything to user_base, and
# declares user_kde_lock_screen for the user. Fixture (params, never committed): myname "P8 Test User", a fake SHA-512
# hash with salt p8testsalt, mykey = a throwaway RSA public key body (private half discarded); defaults otherwise.
# Node kubuntu since 2026-11-17: the set's `session` block logs p8testuser in to Plasma after the apply, then two
# agent runs (Phase 3 desktop sessions), so the KDE lock settings (formerly an uncovered note) are checked too.
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1). The fixture hash is now the user classes'
# known test password (p8test-user-not-a-secret), so the password the wrapper passes is exercised. user_base's own set
# covers the key purge and the home; user_kde_lock_screen's set covers the lock settings in depth.
# Correction round 1, 2026-11-21 (review 20261121T135622Z, purpose): the params fixture now gives mygrouplist ['users']
# (an existing Ubuntu group), so the wrapper's prepending and user_base's primary-group rule are exercised.
```
