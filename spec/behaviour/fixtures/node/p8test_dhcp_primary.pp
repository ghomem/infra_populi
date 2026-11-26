# Node fixture p8test_dhcp_primary: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
package { 'dnsmasq-base':
  ensure => installed,
}
exec { 'p8test stand-in primary interface p8test0 with a DHCP server in netns p8testdhcp':
  command => '/bin/sh -c "ip netns add p8testdhcp && ip link add p8test0 type veth peer name p8test0p && ip link set p8test0p netns p8testdhcp && ip netns exec p8testdhcp ip link set lo up && ip netns exec p8testdhcp ip addr add 203.0.113.1/24 dev p8test0p && ip netns exec p8testdhcp ip link set p8test0p up && ip netns exec p8testdhcp dnsmasq --interface=p8test0p --bind-interfaces --port=0 --dhcp-range=203.0.113.50,203.0.113.50,12h --dhcp-option=3 --dhcp-option=6 --pid-file=/run/p8testdhcp.pid --dhcp-leasefile=/run/p8testdhcp.leases"',
  unless  => '/usr/sbin/ip link show p8test0',
  path    => ['/usr/sbin', '/usr/bin', '/sbin', '/bin'],
  require => Package['dnsmasq-base'],
  before  => Class['puppet_infrastructure::network_dhcp'],
}
