# user_kde_lock_screen: authoring notes (the comments of .codex_state/checks/user_kde_lock_screen.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_kde_lock_screen (define; harness title p8testuser, the user-identity
# fixture; required_base user_base creates the user; node kubuntu, Kubuntu 24.04 KDE Plasma 5.27, an X11 session).
# Fixture: params {"screenlock_timeout_minutes": 2} (grace at its default 0): two minutes keep the run short; the class's
# mechanism is the same for any value, and the default five minutes is an uncovered variant row. Without the class's
# settings an idle session does not lock in that time: measured on p8lab-kubuntu 2026-11-20, a fresh Plasma session of
# a user with no kscreenlockerrc was still unlocked 450 s after its login (LockedHint no).
# The define runs configure_lock_screen.sh as the user, guarded by the same script's --check mode; the script acts only
# when `who` lists the user and talks to the user's KDE session. The set's `session` block makes the runner log
# p8testuser in to Plasma after the apply and make two agent runs (the first applies the settings, the second must be
# clean), as a desktop user's next periodic agent run would; the checks then read the result.
# 2026-11-20 (backfill batch 6): purpose and outcomes (HQ rulings 2 and C1), the 2-minute fixture, the idle lock in the
# live session, the harness apply with the user logged out, and an exercise: the user turns the lock off in the live
# session, the node's next agent run turns it back on. Prototyped on kubuntu 2026-11-20: with a 1-minute timeout the
# session locked 71 s after login; with Autolock off it stayed unlocked 90 s past the timeout; restored and reloaded
# over D-Bus, it locked within 5 s (it had been idle longer than the timeout).
```
