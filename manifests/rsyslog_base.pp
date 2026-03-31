#
# Configures the base rsyslog service and copies this node's Puppet TLS
# materials so rsyslog can use them for encrypted forwarding.
# Dependencies: Puppet agent SSL state, rsyslog, rsyslog-gnutls.
#
class puppet_infrastructure::rsyslog_base {

  # Install the base rsyslog packages.
  package { ['rsyslog', 'rsyslog-gnutls']:
    ensure => installed,
  }

  # Preserve the legacy syslog account expected by the EL rsyslog package.
  if $facts['os']['family'] == 'RedHat' {
    group { 'syslog': ensure => present, gid => 0, allowdupe => true }
    user  { 'syslog': ensure => present, uid => 0, allowdupe => true }
  }

  # Copy Puppet certificates so rsyslog can read them.
  $ssldir   = $settings::ssldir
  $certname = $trusted['certname']

  file { '/etc/rsyslog.d/tls':
    ensure => directory,
    owner  => 'syslog',
    group  => 'syslog',
    mode   => '0755',
    require => Package['rsyslog'],
  }

  file { '/etc/rsyslog.d/tls/ca.pem':
    source => "file://${ssldir}/certs/ca.pem",
    owner  => 'syslog', group => 'syslog', mode => '0644',
    require => File['/etc/rsyslog.d/tls']
  }

  file { "/etc/rsyslog.d/tls/${certname}.pem":
    source => "file://${ssldir}/certs/${certname}.pem",
    owner  => 'syslog', group => 'syslog', mode => '0644',
    require => File['/etc/rsyslog.d/tls']
  }

  file { "/etc/rsyslog.d/tls/${certname}.key":
    source => "file://${ssldir}/private_keys/${certname}.pem",
    owner  => 'syslog', group => 'syslog', mode => '0600',
    require => File['/etc/rsyslog.d/tls']
  }

  # Ensure the service is enabled and reacts to TLS directory changes.
  service { 'rsyslog':
    ensure     => running,
    enable     => true,
    provider   => 'systemd',
    subscribe  => File['/etc/rsyslog.d/tls'],
  }
}
