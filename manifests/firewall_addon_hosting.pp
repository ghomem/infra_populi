# Puppet 8 migration: release-0.9.10 manifest; action renamed to jump and HQ-ruled master OUTPUT rule.
# Module dependency: puppetlabs-firewall 8.3.0.
### Purpose ########
# This class provides COMPLEMENTARY firewall configurations for hosting servers
### Warnings #######
# Do not forget to do the main firewall configuration,
# either by including one of our base classes
# (infra_populi::firewall or infra_populi::firewall_secure)
# or trough some other alternative (e.g. bash scripts).
### Dependencies ###
#  modules: puppetlabs-firewall

class infra_populi::firewall_addon_hosting {

  # override the default OUTPUT from the firewall class - can't touch this!
  firewallchain { 'OUTPUT:filter:IPv4':  ensure => present, purge => true, policy => drop }
  firewall { '149 OUTPUT ACCEPT RELATED ESTABLISHED': chain => 'OUTPUT', state => [ 'RELATED', 'ESTABLISHED'] , jump => 'accept' }

  # this is customizable
  firewall { '150 OUTPUT DNS': chain => 'OUTPUT', proto => 'udp', dport => '53' ,  jump => 'accept' }
  firewall { '151 OUTPUT NTP': chain => 'OUTPUT', proto => 'udp', dport => '123' , jump => 'accept' }
  firewall { '152 OUTPUT PUPPET MASTER': chain => 'OUTPUT', proto => 'tcp', dport => '8140', destination => $server_facts['servername'], jump => 'accept' }

}
