# MOCK-APPLY node fixture `p8test_dhcp_primary` (HQ 2026-10-27 ruling 7) for openvpn_server (and network_vpn). Production's
# VPN gateways hand the class their primary interface (network_dhcp iface = $::networking['primary'] = openvpn_server's
# $local_interface): the class rewrites /etc/network/interfaces for it, for lo:0 and for the bridge br0, and restarts
# ifupdown networking. The lab node's real NICs are never handed over (fixture rule), so this supplies a stand-in
# primary interface: p8test0, one end of a veth pair whose other end lives in the network namespace p8testdhcp, where
# dnsmasq answers DHCP with the single address 203.0.113.50 and no router option (the node's default route and DNS stay
# on NIC1, its SSH path on NIC2). The class then manages p8test0 exactly as production manages the primary interface.
# Behaviour of a real uplink (clients reaching the server over the primary interface) is NOT verified by a GREEN with it.
# Lifted by: a dedicated real NIC the class may take over as its primary interface (an extra VirtualBox NIC on a gateway node; HQ batch-8 ruling 3)
package { 'dnsmasq-base':
  ensure => installed,
}
exec { 'p8test stand-in primary interface p8test0 with a DHCP server in netns p8testdhcp':
  command => '/bin/sh -c "ip netns add p8testdhcp && ip link add p8test0 type veth peer name p8test0p && ip link set p8test0p netns p8testdhcp && ip netns exec p8testdhcp ip link set lo up && ip netns exec p8testdhcp ip addr add 203.0.113.1/24 dev p8test0p && ip netns exec p8testdhcp ip link set p8test0p up && ip netns exec p8testdhcp dnsmasq --interface=p8test0p --bind-interfaces --port=0 --dhcp-range=203.0.113.50,203.0.113.50,12h --dhcp-option=3 --dhcp-option=6 --pid-file=/run/p8testdhcp.pid --dhcp-leasefile=/run/p8testdhcp.leases"',
  unless  => '/usr/sbin/ip link show p8test0',
  path    => ['/usr/sbin', '/usr/bin', '/sbin', '/bin'],
  require => Package['dnsmasq-base'],
  before  => Class['infra_populi::network_dhcp'],
}
