# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none (core file resource only).
### Purpose ########
# This class provides a nagios plugin that can be used trigger and monitor integrity checks
class infra_populi::sysmon_integrity_node ( $checklist = '' ) {

  $bindir   = lookup('filesystem::bindir')

  # integrity, template uses the checklist variable
  file { "${bindir}/nagios-integrity.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  content => template('infra_populi/sysmon/nagios-integrity.sh.erb'),
  require => File[ $bindir ],
  }

}
