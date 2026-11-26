# user_desktop_sudoer: authoring notes (the comments of .codex_state/checks/user_desktop_sudoer.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_desktop_sudoer (define; harness title p8testuser, the user-identity
# fixture; node kubuntu, Kubuntu 24.04, which carries the lpadmin and sambashare groups). The wrapper builds the group
# list [<given>, <title>, cdrom, dip, plugdev, lp, lpadmin, sambashare, adm, sudo], passes everything to user_base and
# declares user_kde_lock_screen for the user. Fixture (params, never committed): as user_desktop's: myname "P8 Test
# User", a fake SHA-512 hash with salt p8testsalt, mykey = a throwaway RSA public key body; defaults otherwise.
# Adapted from user_desktop's reviewed set, plus the sudo right the extra groups grant. Since 2026-11-17 the set's
# `session` block logs p8testuser in to Plasma after the apply, then two agent runs (Phase 3 desktop sessions), so
# the KDE lock settings the wrapper declares (formerly an uncovered note) are checked too.
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1). The fixture hash is now the user classes'
# known test password (p8test-user-not-a-secret), so the password and sudo are exercised for real. The params fixture
# gives mygrouplist ['users'] (an existing Ubuntu group), so the wrapper's prepending and user_base's primary-group rule
# are exercised (as user_desktop's set after its review 20261121T135622Z).
```
