# Node fixture p8test_domain_dns: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
file { '/etc/resolv.conf':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "domain lan\nnameserver {{PEER_ADDR}}\nnameserver 1.1.1.1\nnameserver 8.8.8.8\n",
  before  => Class['puppet_infrastructure::openvpn_domain'],
}
