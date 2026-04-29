# @summary Enforce DROP as the default policy for selected IPv6 firewall chains.
#
# This class complements the firewall baseline by setting the IPv6 INPUT and
# FORWARD chains to DROP while leaving rule management to the shared firewall
# module.
#
# @see https://forge.puppet.com/modules/puppetlabs/firewall
# @dependencies puppetlabs-firewall
class puppet_infrastructure::firewall_ipv6_drop_policy {

  firewallchain { 'FORWARD:filter:IPv6':
    ensure => present,
    purge  => true,
    policy => drop,
  }

  firewallchain { 'INPUT:filter:IPv6':
    ensure => present,
    purge  => true,
    policy => drop,
  }
}
