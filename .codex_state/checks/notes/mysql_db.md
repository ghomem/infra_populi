# mysql_db: authoring notes (the comments of .codex_state/checks/mysql_db.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::mysql_db (define; per-class baseline exception 874f854; required_base
# mysql_server, re-migrated with the HQ 2026-11-17 ruling-1 client declaration: mysql_server owns mysql::client with the
# MySQL client package, because puppetlabs-mysql 17's mariadb-client default removed the MySQL server, escalations/mysql_db.md).
# MySQL-only by baseline design (ruling 4: every mysql::db requires Class['puppet_infrastructure::mysql_server']).
# Fixture (params, never committed): db_name p8test_db, rw_user p8test_rw, ro_user p8test_ro, fake p8test passwords (the
# rw one appears below: a fixture value, never a real secret). Probes run as root (root@localhost via /root/.my.cnf).
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1), and the accounts as behaviour: rw writes,
# ro reads over TLS and its write is refused (the ro password appears too: a p8test fixture value).
# Correction round 1, 2026-11-21 (review 20261121T022351Z, purpose): a login from another host, from the peer ubuntu2
# over the host-only network (prototyped: TLS 1.3 as p8test_rw@%, served by puppet8node; without TLS ERROR 1045).
```
