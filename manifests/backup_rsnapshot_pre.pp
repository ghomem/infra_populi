# Class: puppet_infrastructure::backup_rsnapshot_pre
#
# Purpose:
#   Prepare the shared rsnapshot prerequisites used by rsnapshot-based
#   backup definitions.
#
# Dependencies:
#   - Hiera data for `filesystem::bindir`
#   - `backups/rdiff.sh` file served from this module's files directory
#
class puppet_infrastructure::backup_rsnapshot_pre {

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
    source => 'puppet:///modules/puppet_infrastructure/backups/rdiff.sh',
  }

}
