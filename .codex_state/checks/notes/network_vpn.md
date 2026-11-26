# network_vpn: authoring notes (the comments of .codex_state/checks/network_vpn.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::network_vpn (class; required_base network_dhcp, required_external firewall;
# MOCK-APPLY: node fixture p8test_dhcp_primary, the stand-in DHCP primary interface p8test0). It composes the caching
# nameserver for the VPN network, its firewall add-on on the bridge, the OpenVPN forwarding/NAT add-on and openvpn_server.
# Fixture (params, never committed): wan_iface p8test0 and the VPN network on an RFC 5737 range (198.51.100.1/24, pool
# .101-.200, so peer probes name no 192.168 address); openvpn_server's local/local_interface come from the lab Hiera
# (p8test0 / 203.0.113.50). Defaults: bridge br0, lan_iface lo:0, client DNS = the static IP.
# The client filters the pushed redirect-gateway (checked as received), as in openvpn_server's set.
# Purpose and outcomes table added 2026-11-19 (backfill batch 4, HQ batch-10 rulings 2 and C1), with the composition
# as behaviour: stand-ins for the base firewall's default drop (INPUT UDP 53 on br0, FORWARD from br0 and from
# p8test0) are appended after the class's rules; the VPN client resolves a real name recursively through the VPN's
# nameserver (with the lab NAT IPv6 fixture of caching_nameserver's set) and reaches a TCP server on the WAN side (the
# node fixture's namespace p8testdhcp, 203.0.113.1 behind p8test0), which sees the server's WAN address
# 203.0.113.50 (masquerade); rule counters attribute the passes to 1301, 202, 203 and 205.
# Also 2026-11-19, after openvpn_server's findings (escalations/openvpn_server.behaviour.md): network_vpn passes its own
# default cipher (openvpn_cipher AES-256-CBC, :25, :57), so a client that offers only it is checked here too, last (it
# stops the first client). The data channel's compression is openvpn_server's default, not passed by this class: it
# stays with openvpn_server's set, where it is a finding.
# Authoring correction 2026-11-19 (run 20261119T115047Z, `the-client-resolves-...` got SERVFAIL for www.debian.org
# while the WAN path passed): measured on the applied node, named answered SERVFAIL in 0.3 s because the lookup
# "exceeded max queries ... (max-recursion-queries, ... maxqueries=50)"; 49 of those queries were IPv6 attempts that
# failed at once ("network unreachable": the lab NAT has no IPv6, and the fixture had only removed the route). Run with
# -4, the same configuration resolved www.kernel.org, www.debian.org, www.wikipedia.org and example.org (NOERROR in
# 0.14-0.67 s); disabling IPv6 on the host did not stop the attempts. The lab fixture therefore tells named the network
# is IPv4-only (-4 in /etc/default/named, a file no composed class manages). Whether an IPv4-only production host
# meets the same limit is a question for HQ (batch-4 report), not something this lab can show.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): another client DNS (production sets it) is a check in the variant
# run `clientdns`; the other parameter variants are an accepted gap; the composed behaviours name what is missing.
```
