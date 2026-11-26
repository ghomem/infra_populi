# mount_shares_desktop: authoring notes (the comments of .codex_state/checks/mount_shares_desktop.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::mount_shares_desktop (define, title p8testuser; node gnome, Ubuntu 24.04
# GNOME; until 2026-11-23 MOCK-APPLY: node fixture p8test_desktop_home supplied /home/p8testuser/Desktop). Fixture (params, never
# committed): username p8testuser, one share {share_server: ubuntu2's host-only address, share_name p8share, domain "",
# cifs_version "3.0"} (Samba 4.19 refuses the template's SMB1 default), explorer False (gnome has no dolphin), symlinks
# False; auth_user, cache and delay at their defaults ('$USER', True, 0.5).
# HQ batch-8 ruling 5: ubuntu2 serves a test share (Samba, account p8testuser with a fake password). The node then runs
# the generated scripts as a desktop user would, with the password in $PASSWORD (the script asks kdialog only when it
# is empty) and USER=p8testuser; the scripts run as root here, so the template's `sudo` needs no sudoers rule.
# Node probes name no lab host: the server address reaches the node only through the rendered script.
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1); checks unchanged.
# Correction round 1, 2026-11-21 (review 20261121T020700Z, purpose): the scripts ran as root, so the mount was private to
# root. They now run as p8testuser, whose sudo for the template's two commands comes from a declared fixture drop-in
# (/etc/sudoers.d/p8test-shares); the mount is checked as the user's own and denied to nobody. The explorer row's
# evidence now names the plan node, not the lab.
# 2026-11-23 (HQ after batch 20, item 6, the stand-in lift "the desktop login"): node fixture p8test_desktop_login
# (a test asset) declares p8testuser and logs it in to GNOME once through GDM's automatic login (removed again);
# the session's xdg-user-dirs creates ~/Desktop with the other XDG directories, owned by the user. The checks are
# unchanged: they never relied on how ~/Desktop came to exist.
```
