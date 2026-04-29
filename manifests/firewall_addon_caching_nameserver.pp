# @summary Allow LAN clients to query the local caching nameserver.
#
# @dependencies
# - puppetlabs-firewall

class puppet_infrastructure::firewall_addon_caching_nameserver (
  $lan_iface,
  $port = '53',
) {
  firewall { '1301 accept nameserver':
    proto   => 'udp',
    iniface => $lan_iface,
    dport   => $port,
    jump    => 'accept',
  }
}
