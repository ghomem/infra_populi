# Puppet 8 migration: release-0.9.10 manifest, plus two local changes (policy B, HQ batch-10 ruling 4; rules/local_changes.md #3, #4): net-tools is installed, so the two connection checks find netstat, which Ubuntu 24.04 no longer ships; files/sysmon/nagios-puppet.sh looks for the agent's lock notice in its whole output, so a run in progress is UNKNOWN again under OpenVox 8.
# Module dependencies: none.
### Purpose ########
# This class provides a nagios plugin that can be used trigger and monitor puppet runs, cpu, memory and zimbra
class infra_populi::sysmon_base {

  $os_family = $facts['os']['family']
    
  case $os_family {
    'Debian': {
      $packagename = monitoring-plugins-standard
    }
    'RedHat': {
      $packagename = nagios-plugins-disk
    }
    default: {
    }
  }

  $localdir = lookup('filesystem::localdir')
  $bindir   = lookup('filesystem::bindir')

  # check_netstat_conns.sh and check_netstat_cip.sh run netstat (local change #3)
  package { 'net-tools': ensure => installed, }


# puppet
  file { "${localdir}/bin/nagios-puppet.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/nagios-puppet.sh',
  require => File[ "${localdir}/bin" ],
  }

# reboot check
  file { "${localdir}/bin/check_reboot_required.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_reboot_required.sh',
  require => File[ "${localdir}/bin" ],
  }

# file handles check
  file { "${localdir}/bin/check_file_handles.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_file_handles.sh',
  require => File[ "${localdir}/bin" ],
  }

# netstat conns check
  file { "${localdir}/bin/check_netstat_conns.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_netstat_conns.sh',
  require => File[ "${localdir}/bin" ],
  }

# netstat connections, IPs, port check
  file { "${localdir}/bin/check_netstat_cip.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_netstat_cip.sh',
  require => File[ "${localdir}/bin" ],
  }

# package count
  file { "${localdir}/bin/check_package_count.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_package_count.sh',
  require => File[ "${localdir}/bin" ],
  }

# bandwidth
  file { "${localdir}/bin/check_bandwidth.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_bandwidth.sh',
  require => File[ "${localdir}/bin" ],
  }

# disk latency
  file { "${localdir}/bin/check_dd_latency.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_dd_latency.sh',
  require => File[ "${localdir}/bin" ],
  }

# cpu
  file { '/usr/lib64/nagios/plugins/check_cpu.py':
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  content => template('infra_populi/sysmon/check_cpu.py.erb'),
  require => Class['infra_populi::packages_base'],
  }

# memory
  file { '/usr/lib64/nagios/plugins/check_mem.pl':
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_mem.pl',
  require => Class['infra_populi::packages_base'],
  }

# operating system version
  file { "${localdir}/bin/check_os_version.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_os_version.sh',
  require => File[ "${localdir}/bin" ],
  }

# ssl certificate expiration
  file { "${localdir}/bin/check_http_ssl_cert.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  source  => 'puppet:///modules/infra_populi/sysmon/check_http_ssl_cert.sh',
  require => File[ "${localdir}/bin" ],
  }

  file { "${localdir}/bin/elastic_query_check.py":
    mode    => '0755',
    owner   => 'root',
    group   => 'root',
    source  => 'puppet:///modules/infra_populi/sysmon/elastic_query_check.py',
    require => File[ "${localdir}/bin" ],
  }

}
