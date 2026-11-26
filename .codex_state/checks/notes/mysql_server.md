# mysql_server: authoring notes (the comments of .codex_state/checks/mysql_server.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::mysql_server (class; per-class baseline exception 874f854; migrated with the
# HQ-ruled module-compatibility change service_name => 'mysql', class_rulings.txt / HQ batch-5 ruling 2).
# Fixture (params, never committed): version 8.0, base_dir /srv (data dir /srv/mysql), the lab master's fixture TLS
# files p8test-chain.pem / p8test-key.pem / p8test.pem (under /etc/mysql/ssl), a fake root password.
# HQ ruling 2: the checks must show a MySQL (not MariaDB) server running from the managed config.
# 2026-11-20 (backfill batch 6): purpose and outcomes (HQ rulings 2 and C1), and the server's behaviour toward clients:
# TLS required and verified against the chain, root's password enforced, the default accounts gone. The fixture's root
# password stays in the params file: the checks use root's socket login (/root/.my.cnf, written by puppetlabs-mysql)
# and a throwaway account p8testsql. Prototyped on the node 2026-11-20: root's plugin is mysql_native_password (the
# module's); a caching_sha2 account fails a plaintext login in the client (ERROR 2061) before the server's transport
# rule, so the throwaway account uses mysql_native_password and the server answers ERROR 3159.
# Correction round 1, 2026-11-20 (review 20261120T115855Z, purpose gap): the TLS key's confidentiality (mysql reads it,
# other users cannot), with a mismatch reading it as nobody.
# Correction round 2, 2026-11-20 (review 20261120T120720Z, purpose gap): root accounts for hosts other than localhost
# (the rest of remove_default_accounts) are counted too.
```
