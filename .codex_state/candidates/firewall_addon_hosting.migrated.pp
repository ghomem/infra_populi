# CANDIDATE — puppet_infrastructure::firewall_addon_hosting
# Status: MIGRATION CORRECT, VALIDATION BLOCKED.
# The action=>jump migration below is clean and behaviour-preserving (3 lines,
# no reimplementation, verified against upstream release-0.9.8).
# It is NOT committed to manifests/ because it cannot reach GREEN under the
# current one-class-at-a-time harness: this class sets OUTPUT chain to
# purge+policy=drop, permitting only RELATED/ESTABLISHED + DNS + NTP outbound.
# A puppet agent run opens a NEW outbound connection to master:8140, which is
# therefore dropped — the node loses its control plane and run 2 hangs.
# The class documents its own requirement: it needs a base firewall
# (firewall / firewall_secure) present. See blocked.txt and DESIGN_DECISIONS.md.
# Unblocks when: base-context harness capability exists (classify target class
# + its declared required base). This candidate is then the migration to apply.
#
### Purpose ########
# This class provides COMPLEMENTARY firewall configurations for hosting servers
### Warnings #######
# Do not forget to do the main firewall configuration,
# either by including one of our base classes
# (puppet_infrastructure::firewall or puppet_infrastructure::firewall_secure)
# or trough some other alternative (e.g. bash scripts).
### Dependencies ###
#  modules: puppetlabs-firewall

class puppet_infrastructure::firewall_addon_hosting {

  # override the default OUTPUT from the firewall class - can't touch this!
  firewallchain { 'OUTPUT:filter:IPv4':  ensure => present, purge => true, policy => drop }
  firewall { '149 OUTPUT ACCEPT RELATED ESTABLISHED': chain => 'OUTPUT', state => [ 'RELATED', 'ESTABLISHED'] , jump => 'accept' }

  # this is customizable
  firewall { '150 OUTPUT DNS': chain => 'OUTPUT', proto => 'udp', dport => '53' ,  jump => 'accept' }
  firewall { '151 OUTPUT NTP': chain => 'OUTPUT', proto => 'udp', dport => '123' , jump => 'accept' }

}
