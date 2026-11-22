# Puppet 8 migration: release-0.9.10 manifest; local changes #18: a .sql file that is not a mysqldump is reported CRITICAL; #20: a dump whose database exists is validated, not restored, and a restore drops only the databases it created (check-mysqldump-health.sh.erb).
# Module dependencies: none (core file resource only).
### Purpose ########
# This class provides a nagios plugin that can be used trigger and monitor MYSQL db test restores
define puppet_infrastructure::sysmon_mysqldump_health ( $mysqluser, $mysqlpassword, $dirs) {

  $bindir   = lookup('filesystem::bindir')
  $script_prefix = 'check-mysqldump-health'
  $scriptname = "${script_prefix}.sh"

  file { "${bindir}/${scriptname}":
    mode    => '0755',
    owner   => 'root',
    group   => 'root',
    content => template("puppet_infrastructure/sysmon/${script_prefix}.sh.erb"),
    require => File[ $bindir ],
  }

}

