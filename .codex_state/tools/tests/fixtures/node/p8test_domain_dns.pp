# MOCK-APPLY node fixture `p8test_domain_dns` (HQ 2026-10-27 ruling 7; HQ batch-8 ruling 6) for openvpn_domain. The class
# joins the node to an Active Directory domain and finds its DC by name (smb.conf `wins server`, the realm's DNS SRV
# records); in production a domain member's DNS is the domain's. The lab node resolves through a static
# /etc/resolv.conf (1.1.1.1, 8.8.8.8; systemd-resolved in foreign mode, so libc and Samba read only that file), which
# knows nothing of the lab domain p8test.example. This puts the lab DC p8lab-dc's DNS (Samba internal DNS on
# 192.168.56.25, forwarding everything else to 10.0.2.3) first, ahead of the node's own resolvers.
# p8lab-dc must be running during the run (nodes.yml kind dc).
# 2026-11-17: first version routed the domain through a systemd-resolved drop-in; libc never consults resolved here
# (Codex run 1 BLOCKED: getent failed, net join could not find the DC). A manual join with this file succeeded.
# Lifted by: a node on a network whose DNS (DHCP) serves the AD domain, as production's
file { '/etc/resolv.conf':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "domain lan\nnameserver 192.168.56.25\nnameserver 1.1.1.1\nnameserver 8.8.8.8\n",
  before  => Class['puppet_infrastructure::openvpn_domain'],
}
