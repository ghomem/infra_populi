# filesystem_sec: authoring notes (the comments of .codex_state/checks/filesystem_sec.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::filesystem_sec (define; title filesystem_sec; node ubuntu). Fixture
# (params, never committed): restricted_cmds [/bin/nc, /bin/netstat, /usr/bin/wget, /usr/bin/curl, /usr/bin/lynx,
# /usr/bin/traceroute, /usr/bin/telnet, /usr/bin/ftp, /usr/bin/sftp, /usr/bin/scp, /usr/bin/make, /usr/bin/pip,
# /usr/bin/ssh, /usr/bin/gcc], restricted_mode 0750, restricted_group '' (so sudo on Ubuntu). On the clean node wget,
# curl, sftp, scp and ssh are regular files; nc, telnet and ftp are links (Puppet manages a link's owner, not a mode it
# cannot have); the others are not installed. Probes read the node's files and run the tools as two fixture accounts.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): a custom group and mode (production's come from per-node Hiera
# through node_base) and the RedHat default group are now checks in the variant runs `custom` and `rhel`.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2); the set-level uncovered list moved into it.
  # Correction round 1 (2026-11-19, review 20261119T014218Z): the linked commands (nc, telnet, ftp) and the
  # uninstalled ones got checks; the earlier rows held for the regular files only.
  # 2026-11-18 authoring correction (run 2, 20261118T124301Z): runuser exits 1, not 126, when the kernel refuses to
  # execute the command ("runuser: failed to execute /usr/bin/wget: Permission denied"); the checks now read that
  # message. The behaviour is unchanged (run 2's stderr shows the denial).
  # 2026-11-18 authoring correction (run 1, 20261118T124148Z, INVALID): on the clean node wget is 0755 and the fixture
  # account does not exist, so the drift effect matched there too; it now also shows curl still restricted by the class.
```
