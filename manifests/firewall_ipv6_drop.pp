# @summary Drop inbound and forwarded IPv6 traffic.
#
# Applies IPv6 filter-table rules that drop all traffic entering the INPUT and
# FORWARD chains. Intended as an add-on to the base firewall policy.
#
# @dependencies
# - puppetlabs-firewall
class puppet_infrastructure::firewall_ipv6_drop {

  firewall { '600 Drop ALL IPv6 - INPUT':
    chain    => 'INPUT',
    proto    => 'all',
    jump     => 'DROP',
    protocol => 'IPv6',
  }
  firewall { '601 Drop ALL IPv6 - FORWARD':
    chain    => 'FORWARD',
    proto    => 'all',
    jump     => 'DROP',
    protocol => 'IPv6',
  }
}
