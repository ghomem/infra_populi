#
# Installs the Puppet certificate health check script and grants the Naemon
# user passwordless sudo access to execute it.
#
# Dependencies:
# - Hiera data for `filesystem::localdir`
# - System package `python3-yaml`
# - `sudo::conf` defined type from the `saz-sudo` module
#
class puppet_infrastructure::sysmon_puppet_cert_status {

  $check_puppet_cert_health_deps = [ 'python3-yaml' ]
  if $facts['os']['family'] == 'Debian' {
    exec { 'sysmon_puppet_cert_status_apt_update':
      command     => '/usr/bin/apt-get update',
      path        => ['/usr/bin', '/usr/sbin', '/bin', '/sbin'],
      refreshonly => false,
      unless      => '/usr/bin/test $(/usr/bin/find /var/lib/apt/lists -type f -mtime -1 | /usr/bin/wc -l) -gt 0',
    }

    package { $check_puppet_cert_health_deps:
      ensure  => present,
      require => Exec['sysmon_puppet_cert_status_apt_update'],
    }
  } else {
    package { $check_puppet_cert_health_deps:
      ensure => present,
    }
  }

  $localdir = lookup('filesystem::localdir')
  $file_name = "${localdir}/bin/check_puppet_cert_health.py"

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

  file { "$file_name":
    mode    => '0755',
    owner   => 'root',
    group   => 'root',
    source  => 'puppet:///modules/puppet_infrastructure/sysmon/check_puppet_cert_health.py',
    require => [ File[ "${localdir}/bin" ], Package[$check_puppet_cert_health_deps] ],
  }

  # Grant the monitoring user permission to execute the health check.
  sudo::conf { 'check_puppet_cert_health':
    priority => 20,
    content  => "naemon ALL=NOPASSWD:${localdir}/bin/check_puppet_cert_health.py",
  }

}
