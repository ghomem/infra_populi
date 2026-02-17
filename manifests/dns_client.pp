# Purpose: manage client DNS resolver nameservers via /etc/resolv.conf.
# Dependencies: `resolv_conf` class (from `puppet-resolv_conf` module).
# Note: this class is incompatible with the `network-manager` package.
class puppet_infrastructure::dns_client (
# This is a list of IP addresses that will be set as DNS servers for the client.
Array $nameservers,
) {
  if ($nameservers != []) {
    class { 'resolv_conf':
      nameservers => $nameservers
    }
  }
}
