# Puppet 8 migration: release-0.9.10 manifest; local change #10: ifupdown declared (ensure_packages, shared with openvpn_server).
# Module dependencies: puppet-network 2.2.1 (network_config), puppet-filemapper 4.0.0, puppet-kmod 4.1.0, puppetlabs-stdlib 9.7.0 (ensure_packages).
### Purpose ########
# This class configures a network interface with DHCP.
#
# It was originally created because the OpenVPN server class
# needs to manage interface lo and it has been found that
# once puppet starts managing one interface it has to manage
# all of them.

class infra_populi::network_dhcp ( $iface ) {

    # ifupdown reads the stanza below at boot; Ubuntu 24.04 ships netplan only, and ifupdown-extra does not pull it in
    # (production has it from openvpn_server on the same servers). ensure_packages, as openvpn_server, so both classes
    # can share a node.
    ensure_packages(['ifupdown'], { 'ensure' => 'present' })
    package        { 'ifupdown-extra': ensure => 'installed', }
    network_config { $iface:           ensure => 'present', family  => 'inet', onboot => 'true', method => 'dhcp', hotplug => 'false' }

}
