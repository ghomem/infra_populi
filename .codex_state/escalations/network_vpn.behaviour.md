# network_vpn — behaviour finding: a client on the class's cipher is refused (2026-11-19)

Status: OPEN, for HQ, together with escalations/openvpn_server.behaviour.md: the same cause and the same fix.

## Evidence
- **The reviewer reproduced it on fresh nodes** (checks/reviews/network_vpn/20261119T141557Z.json, set PASS with this
  finding, purpose covered; author run results/network_vpn/20261119T140625Z-author, reviewer run
  20261119T141145Z-reviewer).
- **The baseline:** network_vpn passes its own default `$openvpn_cipher = 'AES-256-CBC'` (network_vpn.pp:25) to
  openvpn_server as `cipher` (:57).
- **Check `a-client-on-the-class-cipher-connects`:** a client that offers only AES-256-CBC gets
  `AUTH_FAILED,Data channel cipher negotiation failed (no shared cipher)` and no tunnel, on OpenVPN 2.6.19. The server
  ignores `--cipher` for negotiation, and its data-ciphers (AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305) leave
  AES-256-CBC out.
- **The other 10 checks pass:**
  - a client connects, gets a pool address and the VPN's nameserver;
  - it resolves a real name recursively through that nameserver over stand-in default drops;
  - it reaches a WAN-side server that sees the masqueraded 203.0.113.50;
  - the composed rules count those flows.

## Production use
3 production node statements declare network_vpn directly (fleet_class_usage.md).

## Options and recommendation
- **The options are openvpn_server's** (A to D, cipher), since network_vpn only passes the value on.
- **A fix in openvpn_server** (option A, the class's cipher added to data-ciphers) would make this check pass with no
  change to network_vpn.
- **The compression finding is openvpn_server's alone:** network_vpn does not pass `compression`.

## Also found while running this set, for HQ (not this class's finding)
- **What happened:** with the lab NAT's IPv6 removed only as a route, the composed caching nameserver (BIND
  9.18.39) answered SERVFAIL for some names (www.debian.org, www.kernel.org).
  - The lookup "exceeded max queries ... (max-recursion-queries, ... maxqueries=50)", 49 of them IPv6 attempts that
    failed at once.
  - Disabling IPv6 on the host did not stop the attempts; named run with `-4` resolved every name.
- **In the lab:** the set's lab fixture now runs named with `-4`.
- **The open question:** whether an IPv4-only production host running caching_nameserver meets the same limit. The
  lab cannot show it. It is in the batch-4 report.
