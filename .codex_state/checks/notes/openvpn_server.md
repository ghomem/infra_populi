# openvpn_server: authoring notes (the comments of .codex_state/checks/openvpn_server.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::openvpn_server (class; required_base network_dhcp; MOCK-APPLY: the plan's
# node_fixture p8test_dhcp_primary supplies p8test0, a stand-in DHCP primary interface; migrated with the ruled change
# "module owns the unit", upstream_defects.md openvpn_server). HQ 2026-11-17 ruling 1: with ubuntu2 as the client it
# connects, gets a pool address, reaches the server side, and a wrong password is rejected.
# Fixture (params, never committed): lan_static_ip 192.0.2.1/24, pool 192.0.2.100-150, lan_iface lo:0, bridge br0,
# local 203.0.113.50 (p8test0's DHCP address), local_interface p8test0; defaults: cipher AES-256-CBC, push_dns_server
# 8.8.8.8, client_isolation true, reneg_sec 3600, compression comp-lzo.
# The peer reaches 203.0.113.50 (a local address of the node) through a host route via the node's host-only address.
# The client filters the pushed redirect-gateway (it is checked as received): applied, it would send the peer's route
# to the server through NIC1's NAT gateway instead of the host-only path.
# Purpose and outcomes table added 2026-11-19 (backfill batch 4, HQ batch-10 rulings 2 and C1), with client isolation
# as behaviour: a second client, in network namespace p8vpn2 on the peer (masqueraded out through the peer's own
# address) and logged in as a second account (one account per client: username_as_common_name without duplicate-cn
# would drop the first session), reaches the server side but not the first client. The networking side (ifupdown and
# the networking service enabled, the bridge's stanza) gets a check of its own.
# The interfaces file's rendering was read on an applied node first (2026-11-19, harness apply): one auto line names
# br0 lo lo:0 p8test0 (p8test0 from network_dhcp's base), then "iface br0 inet static", "address 192.0.2.1", and
# indented options with "bridge_ports lo:0".
# Correction round 1, 2026-11-19 (review 20261119T112433Z FAIL, purpose): the set did not cover the server unit coming
# back at boot (:117-121 enable => 'true'), nor the default cipher (:19, :177) and compression (:30, :166) as behaviour.
# Added: the unit's enablement (the same probe level as networking's), a byte-counter measure of LZO compression in each
# direction of the data channel, and a client that offers only the class's cipher. Measured first on an applied node
# (2026-11-19 11:28:45Z and 11:29:11Z in the clients' logs, OpenVPN 2.6.19): the server says "--cipher set to 'AES-256-CBC' but missing in
# --data-ciphers ... OpenVPN ignores --cipher for cipher negotiations" and refuses a CBC-only client ("No common cipher",
# AUTH_FAILED after the password succeeded); it receives LZO-compressed packets (141 bytes per packet for 1228-byte
# zero-filled pings) but sends uncompressed ones (1237 bytes per packet; "Sent packets are not compressed unless
# allow-compression yes"). The expectations stay the baseline's (both directions compressed; the class's cipher
# usable); the two new behaviour checks are expected to fail as findings.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): another DNS server, cipher and isolation off are a check in the
# variant run `other`; force_ifupdown and compression none are an accepted gap.
```
