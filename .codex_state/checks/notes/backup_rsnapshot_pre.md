# backup_rsnapshot_pre: authoring notes (the comments of .codex_state/checks/backup_rsnapshot_pre.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::backup_rsnapshot_pre (class; no parameters; bindir from Hiera
# filesystem::bindir = /opt/puppet-infrastructure/bin). Written 2026-11-19 (backfill batch 5). The class prepares
# backup_rsnapshot (whose own set runs rsnapshot from /etc/rsnapshot.d): rsnapshot, the configuration directory and the
# rdiff.sh helper. The directory is declared 0644; Puppet adds search permission to a directory wherever read is set,
# so the effective mode is read on the node, not taken from the manifest's text. rdiff.sh runs as behaviour on two
# planted snapshots under /run (non-interactive: no second argument).
# Correction round 1, 2026-11-19 (review 20261119T183418Z FAIL, purpose): two snapshots never exercised the walk across
# pairs (the loop ran once), and my reason for leaving interactive mode uncovered was untrue: `read` takes stdin and
# `clear` only complains on stderr without a terminal. Three snapshots now, and interactive mode with ENTERs on stdin
# (measured on the applied node at 18:36:12Z: both reports in order, two prompts, Done!, exit 0).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1d): the outcome that rsnapshot is driven from /etc/rsnapshot.d is now
# a check here (a configuration placed there and run as backup_rsnapshot's cron line runs it).
```
