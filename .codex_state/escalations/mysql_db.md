# mysql_db — puppetlabs-mysql 17's MariaDB client default removes the MySQL server (2026-11-16, batch 6)

**Status: BLOCKED (category 1, dependency behaviour). Needs an HQ ruling on where the MySQL client package is set.
It also corrects my mysql_server research for HQ ruling 2.**

## What happened (fresh-node harness, mysql_db with required_base mysql_server; both from 874f854)
- Run 1 installed MySQL 8.0 through mysql_server (package, datadir, config, service restart, root password: all
  fine).
- Then `Mysql::Client::Install/Package[mysql_client]: ensure created`: puppetlabs-mysql's `mysql::db` does an
  unconditional `include 'mysql::client'` (db.pp:70), and `mysql::client`'s `package_name` defaults to
  `$mysql::params::client_package_name`, which is **`mariadb-client`** on Ubuntu ≥ 20.04 in 17.3.0 (params.pp:155-171,
  the same flavour switch as the server service).
- apt resolved the conflict by **removing the MySQL server**. From dpkg.log at 23:28:30:
  - removed: mysql-server-8.0, mysql-client-8.0, mysql-client-core-8.0, mysql-server-core-8.0;
  - installed: mariadb-client, mariadb-client-core, mariadb-common.

  mysqld got a clean shutdown ("Received SHUTDOWN from user <via user signal>"), and every `mysql_database`,
  `mysql_user` and `mysql_grant` of the define then failed with `ERROR 2002 … Can't connect … mysqld.sock`.
- **Production consequence:** with the Puppet 8 module line, any MySQL node that declares a `mysql_db` loses its
  MySQL server on the next agent run. puppetlabs-mysql 10.5.0 (production today) defaulted Ubuntu to `mysql-client`.

## Correction to the mysql_server research (HQ ruling 2)
I listed the client packages as "not consumed: the class declares no mysql::client". That is true of mysql_server's
own catalog, which is why its harness and Phase 3 run passed. But its sibling from the same upstream merge,
mysql_db, consumes `mysql::client` through `mysql::db`. The differing default that matters for the family is
therefore two settings, not one:
- the server service (set, `service_name => 'mysql'`, recorded 9152785);
- **the client package** (not set yet).

mysql_server's PASS stands for the class alone; the mysql_server + mysql_db combination needs this ruling.

## Options (HQ)
1. **mysql_server declares the client with the MySQL flavour:** `class { 'mysql::client': package_name =>
   'mysql-client' }` beside `mysql::server`.
   - mysql_db's `include 'mysql::client'` is then satisfied.
   - It depends on evaluation order: mysql_server must be declared before any mysql_db, as upstream's own node
     example does.
   - It is a module-compatibility change to mysql_server (re-migration, one added resource).
2. **Hiera binding:** `mysql::client::package_name: 'mysql-client'` in production Hiera, plus a lab fixture key. No
   code change and no order dependence, but every MySQL node depends on the key.
3. **mysql_db passes nothing and documents the requirement** (a node must declare `mysql::client` with the MySQL
   package first). Fragile; not recommended.

**Recommendation: 2, if production Hiera is acceptable to touch; otherwise 1.** I recommend 2 because the client
package is a node-level choice that several consumers could share, and a data binding has no evaluation-order
dependence.

## State
- **Repository:** nothing of mysql_db committed (the manifest is baseline-identical; no header, no record). Params
  fixture local.
- **Node:** reverted after the run.
