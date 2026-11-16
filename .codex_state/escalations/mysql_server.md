# mysql_server — puppetlabs-mysql 17 assumes MariaDB on Ubuntu ≥ 20.04; the class installs MySQL (2026-11-16)

**Status: BLOCKED (category 1, dependency behaviour). Needs an HQ ruling: a code change (upstream-defect marker) or a
data binding in production Hiera.**

## Evidence
- Class (baseline exception 874f854, identical to it): `class { '::mysql::server': package_name =>
  "mysql-server-${version}", ... }`. It passes no `service_name`, so it takes puppetlabs-mysql's default.
- Fresh-node harness run, batch 5 (fixture version 8.0, base_dir /srv, the `p8test` TLS files):
  ```
  Error: Systemd start for mariadb failed!
  Error: /Stage[main]/Mysql::Server::Service/Service[mysqld]/ensure: change from 'stopped' to 'running' failed: Systemd start for mariadb failed!
  ```
  The MySQL 8.0 package installs the unit `mysql.service`; there is no `mariadb.service`.
- **puppetlabs-mysql 17.3.0** (the lab pin; the Puppet-8-capable line), `manifests/params.pp:155-171`: Debian family
  → `provider = 'mariadb'` when the OS is Debian, Raspbian, or **Ubuntu ≥ 20.04**, so `server_service_name =
  'mariadb'`.
- **puppetlabs-mysql 10.5.0** (the production module, 2026-09-30 inspection), `params.pp:195-210`: `mariadb` only for
  `operatingsystem == 'Debian'` ≥ 9; **Ubuntu → `mysql`**, service `mysql`.
- So with the module the lab must use, the class manages the wrong service on every Ubuntu ≥ 20.04 node. Upstream's
  own example (`node-examples/db/mysql/mysql-server01.pp` at 874f854) sets no service name either, so it was written
  against the old default.

## Options (HQ)
1. **Ruled change in the class** (upstream_defects.md, marker `upstream defect fixed`): pass
   `service_name => 'mysql'` to `mysql::server` (the value 10.5 chose for Ubuntu), so the class keeps managing the
   service it always managed, whatever the module's default. The full mysql-provider set may need checking
   (provider-derived defaults in `mysql::params` beyond the service name); the harness run after the change shows it.
2. **Data binding** `mysql::server::service_name: 'mysql'` in production Hiera, next to the module upgrade. The class
   stays byte-identical, but every MySQL node then depends on that key; the lab would carry the same key as a fixture.
3. **Pin puppetlabs-mysql below the change.** Not available: the releases before the Ubuntu 20.04 → MariaDB default do
   not support Puppet 8 / OpenVox.

Recommendation: 1. It keeps the behaviour inside the class that owns it, it is a one-parameter change, and
mariadb_server (same upstream merge) is unaffected because it wants the MariaDB default.

## State
- No commit of the class: the manifest is untouched (baseline-identical); no header written, nothing recorded.
- Fixture params (local), pregate CLEAN with the provided-paths entry for /etc/mysql (29e5265), classify
  unchanged-validated; the block is the run-1 service failure above.
