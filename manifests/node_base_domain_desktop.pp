# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: puppetlabs-ntp 11.2.0 (ntp).
# Expected run-2 events: Exec[apt_update] — node_base_domain_desktop declares packages_base, whose `class { 'apt': update => { frequency => 'always' } }` runs apt update on every agent run by upstream design (justified on packages_base).
### Purpose ########
# This class provides basic desirable properties of a domain based desktop node
class infra_populi::node_base_domain_desktop (
  Boolean $customize_syslog_mode = false,
  String $syslog_mode            = 'u=rw,g=r,o=',
  $apt_surface_list = [], # if empty it will default to a builtin list
) {

  class { 'infra_populi::packages_base': unattended_upgrades => true }
  class { 'infra_populi::ssh_secure': password_authentication => true }
  include infra_populi::firewall_secure
  include infra_populi::firewall_ipv6_drop
  class { 'infra_populi::filesystem_base_desktop':
    customize_syslog_mode => $customize_syslog_mode,
    syslog_mode           => $syslog_mode,
  }
  class { 'infra_populi::filesystem_apt':
    apt_surface_list  => $apt_surface_list,
    server_mode       => false,
  }

  include ::ntp

  # desktops run puppet directly, not via sysmon
  service { 'puppet':
    ensure => running,
    enable => true,
  }

}
