# user_lock: authoring notes (the comments of .codex_state/checks/user_lock.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::user_lock (define; harness title p8testuser; required_base hashman_base;
# until 2026-11-23 MOCK-APPLY with node fixture hashman_lock_standin, which seeded p8testuser's hashman entries before
# the lock: the Unix hash and the Samba hash of the lab's user test password). Migrated with the ruled upstream-defect fix: the lock exec is
# guarded by its post-condition (upstream_defects.md user_lock). hashman's own `pp_auth.py lock` marks both entries
# locked (LOCKPREFIX '!'), and hashman's auth then refuses the user (the checks below).
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1).
# Correction round 1, 2026-11-21 (review 20261121T124336Z, purpose): the refusal itself, through hashman's own auth on
# the node (hashman_base installs the same CLI and library a master runs). The node fixture now seeds the SHA-512 hash
# of the lab's user test password, so the refusal is the lock's and not a fake hash's.
# Correction round 2, 2026-11-21 (review 20261121T130357Z, purpose; the last round, production use 0): the Samba hash.
# The fixture also seeds p8testuser's Samba entry (hashes_smb.pp), which lockpw invalidates with the same prefix.
# 2026-11-23 (HQ after batch 20, item 6, the stand-in lift): the class runs on the master-role node (kind puppetserver,
# OpenVox server with its own code tree) and the user is no longer seeded: node fixture hashman_user_via_hashman (a
# test asset) has hashman create p8testuser (`pp_auth.py useradd ... SILENT`, then `unlock`), as an administrator does
# before a lock, keeping hashman's initial password in /root/p8test-hashman-initial (0600). A new user's entry carries
# hashman's expiry prefix on the salt type ($!6$, EXPIREPREFIX '!': an initial password, which auth still accepts), so
# the locked entry is '!$!6$...'; the hashes are hashman's own, so the checks match their shape, not a seeded value.
# Correction round 3, 2026-11-23 (review 20261123T015435Z, purpose; approved by HQ 2026-11-23 ruling 2): hashman's
# useradd expires the new password and an expired entry's Samba hash carries '!', so the Samba check could not show
# the lock. The fixture now also runs `pp_auth.py unexpire` and records the Samba hash's state before the lock
# (/root/p8test-hashman-smb-before-lock); the locked Unix entry reads '!$6$...'.
```
