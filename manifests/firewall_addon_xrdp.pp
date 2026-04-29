# @summary Adds firewall rules required for XRDP helpdesk access.
#
# @dependencies
# - puppetlabs-firewall
#
# @note XRDP attempts the local VNC connection over IPv6 before falling back to
#   IPv4. Allowing local IPv6 VNC traffic avoids hangs when the default IPv6
#   policy drops packets without causing an XRDP-visible connection failure.
#
# @see https://github.com/neutrinolabs/xrdp/issues/1596

class puppet_infrastructure::firewall_addon_xrdp {

  firewall { '3389 allow xrdp':
    proto => 'tcp',
    dport => 3389,
    jump  => 'accept',
  }

  firewall { '3389 allow xrdp to vnc ipv6':
    proto    => 'tcp',
    iniface  => 'lo',
    dport    => 5900,
    jump     => 'accept',
    protocol => 'IPv6',
  }

  firewall { '003 Allow established ipv6':
    proto    => 'tcp',
    state    => 'ESTABLISHED',
    sport    => '5900',
    jump     => 'accept',
    protocol => 'IPv6',
  }

}
