# mariadb_server: authoring notes (the comments of .codex_state/checks/mariadb_server.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::mariadb_server (class; per-class baseline exception 874f854; migrated with
# the ruled certificate-exec guard (upstream_defects.md mariadb_server) and the HQ batch-7 ruling-4 module-compatibility
# change: the module's File['/var/log/mysql'] carries the class's mode and ordering through a collector override).
# Fixture (params, never committed): a fake root password and, since 2026-11-21, the users p8test_mrw (rw) and p8test_mro
# (ro) with ed25519 hashes of p8test passwords (p8test-mrw-not-a-secret, p8test-mro-not-a-secret); generate_certificates
# default true. The hashes were computed by the lab's MariaDB 10.11 itself (CREATE USER ... IDENTIFIED VIA ed25519 USING
# PASSWORD(...), then mysql.user's authentication_string): the class header's `SELECT ed25519_password(...)` does not
# exist on 10.11 (ERROR 1305), a documentation note.
# Lab Hiera: db::organization 'My Company', db::cname 'example.com', db::email 'user@example.com' (the upstream example
# common.yaml, first in the hierarchy; the p8test_fixtures.yaml keys of the same names come after it and never win).
# Probes run as root, so the mysql client authenticates as root@localhost through /root/.my.cnf (puppetlabs-mysql).
```
