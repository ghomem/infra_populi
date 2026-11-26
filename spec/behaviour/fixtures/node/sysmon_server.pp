# Node fixture sysmon_server: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
group { 'naemon': ensure => present, system => true }
user { 'naemon':
  ensure     => present,
  system     => true,
  gid        => 'naemon',
  home       => '/var/lib/naemon',
  shell      => '/usr/sbin/nologin',
  managehome => false,
  require    => Group['naemon'],
}
file { ['/etc/thruk', '/etc/naemon', '/etc/naemon/conf.d', '/etc/naemon/conf.d/contacts']:
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
