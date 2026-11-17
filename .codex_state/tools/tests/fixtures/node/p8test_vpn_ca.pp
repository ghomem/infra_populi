# MOCK-APPLY node fixture `p8test_vpn_ca` (HQ 2026-10-27 ruling 7; HQ batch-8 ruling 5) for openvpn_nm_connection. The
# define requires File[$ca_crt] (openvpn_nm_connection.pp:36) but never declares it: production delivers the VPN's CA
# certificate to desktops elsewhere (no class of the code tree declares it; 0 production node statements). This declares
# that file from the lab master's throwaway p8test PKI (extra_files/openvpn/keys/ca.crt, master_fixtures.sh pki) at the
# path the params fixture hands the define. The connection's behaviour against a real VPN server is NOT verified by a
# GREEN with it.
# Lifted by: a class or node definition that ships the VPN CA to desktops (none in the code tree)
file { '/etc/p8test-vpn':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { '/etc/p8test-vpn/ca.crt':
  ensure => file,
  owner  => 'root',
  group  => 'root',
  mode   => '0644',
  source => 'puppet:///extra_files/openvpn/keys/ca.crt',
}
