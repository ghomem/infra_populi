# CANDIDATE — NOT PRODUCTION, NOT MIGRATED. Do not deploy.
# Source: reimplementation from commit 48fc434 (backed out per HQ ruling 2026-07-01).
# Status: BLOCKED. Reimplemented using raw ifupdown file-writing (file + file_line);
#   DIVERGES from release-0.9.8, which uses the network_config custom type.
#   Drops puppet-network / puppet-filemapper (failed to load on Puppet Server / Puppet 8).
#   Behavioral equivalence UNVERIFIED: original relies on the network_config all-interfaces
#   semantic ('once puppet manages one interface it must manage all') that network_vpn /
#   openvpn_server depend on; this rewrite manages only the single named interface.
#   Preserved as a candidate approach pending HQ resolution of the dependency fork (a/b/c/d).
#   See .codex_state/DESIGN_DECISIONS.md.

# @summary Manage an ifupdown DHCP configuration for one network interface.
#
# Writes a per-interface DHCP stanza under /etc/network/interfaces.d and
# ensures the main ifupdown interfaces file sources it. This keeps the class
# independent of the legacy network_config custom type while preserving the
# original interface-management behavior needed by OpenVPN-related profiles.
#
# @param iface
#   Interface name to configure for DHCP.
#
# @dependencies
#   puppetlabs-stdlib: provides the file_line resource.
#
class puppet_infrastructure::network_dhcp (
  String[1] $iface,
) {

  package { 'ifupdown-extra':
    ensure => installed,
  }

  file { '/etc/network/interfaces.d':
    ensure  => directory,
    owner   => 'root',
    group   => 'root',
    mode    => '0755',
    require => Package['ifupdown-extra'],
  }

  file { '/etc/network/interfaces':
    ensure  => file,
    owner   => 'root',
    group   => 'root',
    mode    => '0644',
    require => Package['ifupdown-extra'],
  }

  file { "/etc/network/interfaces.d/${iface}":
    ensure  => file,
    owner   => 'root',
    group   => 'root',
    mode    => '0644',
    content => "auto ${iface}\niface ${iface} inet dhcp\n",
    require => File['/etc/network/interfaces.d'],
  }

  file_line { "source-interface-${iface}":
    ensure  => present,
    path    => '/etc/network/interfaces',
    line    => "source /etc/network/interfaces.d/${iface}",
    match   => "^source\\s+/etc/network/interfaces\\.d/${iface}$",
    require => [
      File['/etc/network/interfaces'],
      File["/etc/network/interfaces.d/${iface}"],
    ],
  }
}
