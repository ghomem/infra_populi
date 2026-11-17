# mariadb_server — puppetlabs-mysql 17 declares File['/var/log/mysql'] itself: duplicate declaration (2026-11-17, batch 7)

**Status: BLOCKED (category 1, dependency behaviour). Needs an HQ ruling on how the class keeps its `/var/log/mysql`
mode. The ruled certificate guard (upstream_defects.md) is not affected.**

## Evidence
- Codex run 1 (wrapper, ruled guard only), harness run 1 exited 1 at compile:
  `Duplicate declaration: File[/var/log/mysql] is already declared at (file: …/mysql/manifests/server/installdb.pp,
  line: 34); cannot redeclare (file: …/puppet_infrastructure/manifests/mariadb_server.pp, line: 168)`.
  Codex stopped (BLOCKED, behaviour change), worktree untouched, nothing recorded.
- The class (874f854, baseline exception), lines 168-174:
  `file { '/var/log/mysql': ensure => 'directory', owner => 'mysql', group => 'adm', mode => '0755', require => Package['mysql-server'] }`.
- puppetlabs-mysql 17.3.0 (the lab pin) `manifests/server/installdb.pp:34-38`, inside `if $mysql::server::package_manage`
  (default true): `file { $log_dir: ensure => 'directory', owner => $mysqluser, group => $mysql::server::mysql_group }`
  with `$log_dir = '/var/log/mysql'`. On the Debian family `mysql_group` is `adm` (params.pp, Debian branch) and
  `$mysqluser` is the mysqld `user` option (`mysql`). `server.pp:188-190` orders `Class['mysql::server::install']`
  before `Class['mysql::server::installdb']`, so the module's directory already comes after the package.
- So the two declarations agree on ensure, owner and group, and on ordering. The class's only extra is
  **`mode => '0755'`**: without it the mode stays whatever the package created.
- Production (puppetlabs-mysql 10.5.0, the 2026-09-30 inspection) evidently does not declare it, or the class could
  never have compiled there; mysql_server (same 874f854 merge) has no such file resource.

## Options (HQ)
1. **Recommended — keep the class's attributes on the module's resource:** replace the class's `file { '/var/log/mysql': … }`
   with a resource collector override, `File <| title == '/var/log/mysql' |> { mode => '0755' }` (owner `mysql` and group
   `adm` already match the module's values; the package ordering is the module's). The managed state stays exactly
   the baseline's: directory, mysql:adm, 0755, after the package. A module-compatibility change (like mysql_server's
   service name), recorded in class_rulings.txt and the header, no defect marker.
2. **Drop the class's resource:** the module's declaration remains, without a mode. Behaviour change: the directory
   keeps the package's mode (Ubuntu's mariadb packages create it group-restricted), not 0755.
3. **`if !defined(File['/var/log/mysql'])` around the class's resource:** parse-order dependent; here the module's
   class is declared first, so it would always skip, which is option 2 in disguise. Not recommended.

## State
- Repository: nothing of mariadb_server committed besides the prerequisites (65b5363: db:: Hiera fixture keys,
  the ruled guard's exact form in class_rulings.txt, expected run-2 `Notify[Produced configs: *]`). Manifest
  baseline-identical; no header, no record. Params fixture local (`root_pw` only).
- Node: run 1 failed at catalog compile (nothing applied); the next harness reverts first.
