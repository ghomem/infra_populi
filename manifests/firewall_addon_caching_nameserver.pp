# Puppet 8 migration: release-0.9.10 manifest; puppetlabs-firewall 8 attribute renames only (action -> jump).
# Module dependency: puppetlabs-firewall 8.3.0.
### Purpose ########
# This class provides necessary firewall configurations for caching nameservers

class puppet_infrastructure::firewall_addon_caching_nameserver (

    $lan_iface,
    $port = '53',

){

    firewall { '1301 accept nameserver': proto => 'udp', iniface => $lan_iface, dport => $port, jump => 'accept' }

}
