# MOCK-APPLY node fixture `sysmon_server` (HQ 2026-10-27 ruling 7). The monitoring server (Naemon + Thruk) lives in
# another repository; this declares only the paths and the service account user_sysmon writes into, so the class can
# apply on the lab node. Behaviour (Thruk login, Naemon contact parsing) is NOT verified by a GREEN with this fixture.
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
