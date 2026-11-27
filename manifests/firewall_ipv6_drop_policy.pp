# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependency: puppetlabs-firewall 8.3.0.
### Purpose ########
# This class provides an add on to firewall_secure that changes IPv6 firewall policies to DROP

### Dependencies ###
#  modules: puppetlabs-firewall
class infra_populi::firewall_ipv6_drop_policy {
  
  firewallchain { 'FORWARD:filter:IPv6': ensure => present, purge => true, policy => drop,  }
  firewallchain { 'INPUT:filter:IPv6':   ensure => present, purge => true, policy => drop,  }
  
}
