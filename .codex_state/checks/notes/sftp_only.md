# sftp_only: authoring notes (the comments of .codex_state/checks/sftp_only.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sftp_only (define; harness title sftp_only; required_base ssh_secure). It
# writes two sshd Match blocks for one user: from the whitelisted addresses, a chroot to the directory's parent with
# internal-sftp forced into the directory and a umask; from every other address, DenyUsers. Fixture (params, never
# committed): user_name p8testuser, ip_whitelist [127.0.0.1], directory /srv/p8test-jail/upload (/var/lib until
# 2026-11-21, a jail the user cannot write into); umask 007 and password_authentication no at their defaults. Lab Hiera:
# ssh_secure's AllowGroups includes p8testgroup (master_fixtures.sh). The define manages neither the user nor the
# directories (its warning 1), so the exercise creates them; the unlisted address is the node's own ::1. The upload
# uses curl as the SFTP client (an sftp:// URL to 127.0.0.1): the runner's host rules forbid the sftp, scp and rsync
# commands as copies to another host, and this transfer stays on the node.
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1).
  # 2026-11-21 authoring corrections: run 1 (20261121T154535Z) expected 660, but curl asks for mode 0644 and umask 007
  # removes the others' bits, giving 640 (the umask's effect: nothing for others); run 2 (20261121T154957Z) asked for
  # 0666 with --new-file-perms, which this curl does not have (the upload never started). The expectation is now 640
  # from curl's 0644. The behaviour was as expected in run 1.
```
