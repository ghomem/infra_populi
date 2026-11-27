# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none (core file resource only).
### Purpose ########
# This class provides a script that generates checksum lists for the sysmon_integrity_node class to use
class infra_populi::sysmon_integrity_master ( $filelist = '' ) {

  $bindir   = lookup('filesystem::bindir')
  $outdir   = lookup('puppet::manifdir')
  $outfile  = '97_integrity.pp'

  # integrity, template uses the filelist variable
  file { "${bindir}/checklist-integrity.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  content => template('infra_populi/sysmon/checklist-integrity.sh.erb'),
  require => File[ $bindir ],
  }

}
