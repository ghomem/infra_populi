# @summary Installs yum helper scripts for system updates.
#
# @dependencies
# - None. The class manages the local script directory inline.

class puppet_infrastructure::filesystem_yum {

  $localdir = lookup('filesystem::localdir')

  file { $localdir:
    ensure => directory,
    mode   => '0755',
    owner  => 'root',
    group  => 'root',
  }

  file { "${localdir}/bin":
    ensure => directory,
    mode   => '0755',
    owner  => 'root',
    group  => 'root',
    require => File[$localdir],
  }

  # security surface updates
  file { "${localdir}/bin/yum-update-surface.sh":
    mode    => '0755',
    owner   => 'root',
    group   => 'root',
    source  => 'puppet:///modules/puppet_infrastructure/yum/yum-update-surface.sh',
    require => File[ "${localdir}/bin" ],
  }

  # full updates
  file { "${localdir}/bin/yum-update-dist.sh":
    mode    => '0755',
    owner   => 'root',
    group   => 'root',
    source  => 'puppet:///modules/puppet_infrastructure/yum/yum-update-dist.sh',
    require => File[ "${localdir}/bin" ],
  }

}
