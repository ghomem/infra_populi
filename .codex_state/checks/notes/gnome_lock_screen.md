# gnome_lock_screen: authoring notes (the comments of .codex_state/checks/gnome_lock_screen.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::gnome_lock_screen (class, parameter defaults: no params file).
# Defaults: screenlock_timeout_minutes 5 -> idle-delay 300 s, screenlock_grace_seconds 0. The class installs dconf-cli,
# writes the system dconf profile, keyfile and locks, and refreshes `dconf update`, which compiles /etc/dconf/db/local.
# The node has no GNOME session: the probes read the COMPILED system database with `dconf read` (it reads the database
# files directly), which proves the refresh-only `dconf update` ran. That the desktop really locks after 5 minutes needs
# a desktop session and is not tested here.
# Purpose and outcomes added 2026-11-19 (backfill batch 5, HQ batch-10 rulings 2 and C1), with the enforcement as
# behaviour: a desktop account, in its own D-Bus session (dbus-run-session, dconf-service installed if absent: the
# writer every GNOME desktop has), cannot override the locked keys, while it can write a key the class does not lock.
# Authoring error 2026-11-19 (run 20261119T192455Z): dbus-daemon's activation messages (stderr) went into the result
# file; only the probe's stdout goes there now. The behaviour in that run was as expected.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): another timeout and grace period (production sets both) are a check
# in the variant run `timing`; the live-session row names what is missing.
# 2026-11-23 correction round 1 (review FAIL 33f9f26): (a) a-user-cannot-override-the-locked-keys read its own action's
# report as its effect; the effect now reads the account's user database through a profile holding only it, and the
# values it is served. (b) The GNOME lock was an uncovered row although the lab has a GNOME node and a GDM automatic
# login (test asset p8test_desktop_login); it is now a check in the variant `gnome` on that node.
```
