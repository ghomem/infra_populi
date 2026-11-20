# Puppet 8 migration: release-0.9.10 manifest; local changes #11: ifupdown declared (ensure_packages, as network_dhcp); #12: the default route on $iface, not eth0.
# Module dependencies: puppet-network 2.2.1 (network_config, network_route), puppet-filemapper 4.0.0, puppet-kmod 4.1.0, puppetlabs-stdlib 9.7.0 (ensure_packages).
### Purpose ########
# This class configures a network interface with static parameters.
#
# It was originally created because the OpenVPN server class
# needs to manage interface lo and it has been found that
# once puppet starts managing one interface it has to manage
# all of them.

class puppet_infrastructure::network_static ( $iface, $ipaddress, $gateway ) {

    # ifupdown reads the stanza below at boot; Ubuntu 24.04 ships netplan only, and ifupdown-extra does not pull it in.
    # ensure_packages, as network_dhcp and openvpn_server, so the classes can share a node.
    ensure_packages(['ifupdown'], { 'ensure' => 'present' })
    package        { 'ifupdown-extra': ensure => 'installed', }
    network_config { $iface:           ensure => 'present', family  => 'inet',   onboot    => 'true', method => 'static',   ipaddress => $ipaddress, hotplug => 'false' }
    # The gateway belongs to the interface the class configures (eth0 was its name before predictable names).
    network_route  { 'default':        ensure => 'present', gateway => $gateway, interface => $iface, netmask => '0.0.0.0', network   => 'default' }

}
