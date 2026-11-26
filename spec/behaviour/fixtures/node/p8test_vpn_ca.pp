# Node fixture p8test_vpn_ca: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
file { '/etc/p8test-vpn':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { '/etc/p8test-vpn/ca.crt':
  ensure => file,
  owner  => 'root',
  group  => 'root',
  mode   => '0644',
  source => 'puppet:///extra_files/openvpn/keys/ca.crt',
}
