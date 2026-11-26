# sysmon_mysqldump_health: authoring notes (the comments of .codex_state/checks/sysmon_mysqldump_health.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sysmon_mysqldump_health (define; harness title sysmon_mysqldump_health;
# required_base filesystem_base). It installs a Nagios check that restores each mysqldump found under `dirs` into a
# scratch database to prove the dumps load. Fixture (params, never committed): mysqluser p8test_check, a fake password,
# dirs /var/tmp/p8test-dumps.
# Observation, baseline behaviour: the script embeds the MySQL password and is world-readable (0755).
# 2026-11-21 (backfill batch 9): purpose and outcomes (HQ rulings 2 and C1), and the restores as behaviour. The define
# provides no MySQL server (production runs the check where the dumps' server is; the fleet's production server class is
# mysql_server, MySQL); the set installs Ubuntu's mysql-server 8.0 on the node in an action, creates the fixture user
# p8test_check with the fixture password, dumps a source database with mysqldump and drops the source, so the check
# restores it into a scratch database as on a backup host. Prototyped on the node.
# Correction round 1, 2026-11-21 (review 20261121T113606Z, purpose; finding a-file-that-is-not-a-dump-is-critical
# reproduced): the create and drop failures, a header-less dump, a second directory (the params fixture's dirs now names
# two). A failed create drops an existing database of the dump's name: a second finding, escalated
# (escalations/sysmon_mysqldump_health.behaviour.md).
# 2026-11-22 (HQ ruling 1, the advisor's design with conditions): before any restore the check lists the databases
# the dump would create or use; if one exists it validates the file only and says the restore test was skipped; a
# restore drops only databases it created in that run (local change #20). The live-database check expects that; an
# incomplete dump of an existing database and a --databases dump of an absent one are added.
# Correction round 3, 2026-11-23 (review 20261122T235949Z, purpose; approved by HQ 2026-11-23 ruling 2): the
# create-failure path after #20 (a database the pre-check did not see cannot be created): with CREATE revoked from
# the check's user, the check reports CRITICAL "Create database" with exit 2 and drops nothing (CREATED is empty).
# Correction round 2, 2026-11-21 (review 20261121T114625Z, purpose; the last round, production use 0): the broken dump
# sits in a dated subdirectory (find recurses); the script's group is read.
```
