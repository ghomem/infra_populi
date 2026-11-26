# user_kde_lock_screen_common: authoring notes (the comments of .codex_state/checks/user_kde_lock_screen_common.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_kde_lock_screen_common (class, no parameters: no params file; plan
# node ubuntu, Ubuntu 24.04 server without a desktop). The class installs configure_lock_screen.sh, the script every
# user_kde_lock_screen define runs as its user. What the script does inside a KDE session is checked in
# user_kde_lock_screen's own set (kubuntu, with a logged-in Plasma session); here the script is the deliverable: it is the
# module's exact file, root-owned and executable, and it runs as an ordinary user on a node where that user is not
# logged in (every server and every desktop between logins), leaving its note and changing nothing.
# 2026-11-20, backfill batch 6: first set.
```
