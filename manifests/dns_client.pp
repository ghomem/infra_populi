# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependency: saz-resolv_conf 8.0.1.
### PURPOSE #######
# This class configures the DNS servers for the client
# This class is incompatible with the package 'network-manager'
class puppet_infrastructure::dns_client (
# This is a list of IP adresses that will be set as DNS servers for the client
Array $nameservers,
) {
  if ($nameservers != []) {
    class { 'resolv_conf':
      nameservers => $nameservers
    }
  }
}
