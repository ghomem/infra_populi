# MOCK-APPLY node fixture `p8test_domain_dns` (HQ 2026-10-27 ruling 7; HQ batch-8 ruling 6) for openvpn_domain. The class
# joins the node to an Active Directory domain and finds its DC by name (smb.conf `wins server`, the realm's DNS SRV
# records); in production the network's DNS serves the domain. The lab node's resolver is VirtualBox NAT's, which knows
# nothing of the lab domain, so this routes the domain p8test.example (realm P8TEST.EXAMPLE) to the lab DC p8lab-dc's
# DNS (Samba internal DNS on 192.168.56.25, forwarding the rest to 10.0.2.3) through a systemd-resolved drop-in; no
# interface is named. p8lab-dc must be running during the run (nodes.yml kind dc).
# Lifted by: a node on a network whose DNS (DHCP) serves the AD domain, as production's
file { '/etc/systemd/resolved.conf.d':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { '/etc/systemd/resolved.conf.d/p8test-domain-dns.conf':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "[Resolve]\nDNS=192.168.56.25\nDomains=~p8test.example\n",
  notify  => Exec['p8test restart systemd-resolved for the lab domain'],
}
exec { 'p8test restart systemd-resolved for the lab domain':
  command     => '/usr/bin/systemctl restart systemd-resolved',
  refreshonly => true,
  before      => Class['puppet_infrastructure::openvpn_domain'],
}
