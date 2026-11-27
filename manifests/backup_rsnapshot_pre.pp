# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none.
### Purpose ########
# This class implements prerequisites for the backup_base_rsync defined type
class infra_populi::backup_rsnapshot_pre {

  $bindir  = lookup('filesystem::bindir')

  package { [ 'rsnapshot' ]: ensure => present, }

  file { '/etc/rsnapshot.d':
    ensure => directory,
    mode   => '0644',
    owner  => 'root',
    group  => 'root',
  }

  file { "${bindir}/rdiff.sh":
    mode   => '0755',
    owner  => 'root',
    group  => 'root',
    source => 'puppet:///modules/infra_populi/backups/rdiff.sh',
  }

}
