# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: puppet-network 2.2.1 (network_config), puppet-filemapper 4.0.0, puppet-kmod 4.1.0.
### Purpose ########
# This class configures a network interface with DHCP.
#
# It was originally created because the OpenVPN server class
# needs to manage interface lo and it has been found that
# once puppet starts managing one interface it has to manage
# all of them.

class puppet_infrastructure::network_dhcp ( $iface ) {

    package        { 'ifupdown-extra': ensure => 'installed', }
    network_config { $iface:           ensure => 'present', family  => 'inet', onboot => 'true', method => 'dhcp', hotplug => 'false' }

}
