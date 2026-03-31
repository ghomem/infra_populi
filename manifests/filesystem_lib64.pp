# Class: puppet_infrastructure::filesystem_lib64
#
# Purpose:
#   Creates a `/usr/lib64/nagios` compatibility symlink for hosts where Nagios
#   plugins are installed under `/usr/lib/nagios`.
#
# Dependencies:
#   None.
class puppet_infrastructure::filesystem_lib64 {

  file { '/usr/lib64/':
    ensure => 'directory',
    owner  => 'root',
    group  => 'root',
  }

  file { '/usr/lib64/nagios/':
    ensure  => 'link',
    target  => '/usr/lib/nagios',
    require => File['/usr/lib64/']
  }

}
