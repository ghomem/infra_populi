# Puppet 8 migration: release-0.9.10 manifest; firewall type attribute renames for Puppet 8 only (action -> jump, provider -> protocol).
# Module dependency: puppetlabs-firewall 8.3.0.
### Purpose ########
# This class provides an add on to firewall_secure that DROPs all IPv6 traffic

### Dependencies ###
#  modules: puppetlabs-firewall
class puppet_infrastructure::firewall_ipv6_drop {

  firewall { '600 Drop ALL IPv6 - INPUT':
    chain    => 'INPUT',
    proto    => 'all',
    jump     => drop,
    protocol => 'ip6tables',
  }
  firewall { '601 Drop ALL IPv6 - FORWARD':
    chain    => 'FORWARD',
    proto    => 'all',
    jump     => drop,
    protocol => 'ip6tables',
  }
}
