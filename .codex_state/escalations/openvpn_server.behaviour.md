# openvpn_server — behaviour findings: the class's cipher is refused, and the server sends uncompressed (2026-11-19)

Status: OPEN, for HQ (network_vpn shares finding 1: escalations/network_vpn.behaviour.md). The reviewer reproduced both findings on fresh nodes (checks/reviews/openvpn_server/20261119T114553Z.json,
set PASS with these findings, purpose covered; reviewer run results/openvpn_server/20261119T113917Z-reviewer).
Escalated for this class under HQ batch-12 ruling 5: each finding's fix has more than one reasonable design. The run
continues with the next class.

## How they were found
- The first review of the extended set (checks/reviews/openvpn_server/20261119T112433Z.json) failed on purpose: the
  set did not cover the server unit at boot, the default cipher (openvpn_server.pp:19, 177) or the default compression
  (:30, 166).
- Correction round 1 measured both on an applied node before writing the checks (the set's header holds the
  measurements), then added three checks (commit 6f48981).
- Run results/openvpn_server/20261119T113217Z-author (commit 5a87fad), on Ubuntu 24.04 with OpenVPN 2.6.19:
  - **11 checks pass**, including the new `server-unit-enabled-at-boot` (enabled, active);
  - **2 findings**, below.

## Finding 1: a client on the class's cipher is refused
- **The baseline:**
  - `$cipher = 'AES-256-CBC'` (:19) is passed to puppet-openvpn as `cipher` (:177);
  - the rendered config holds `cipher AES-256-CBC`.
- **What the server says at start**, verbatim from its journal: "DEPRECATED OPTION: --cipher set to 'AES-256-CBC' but
  missing in --data-ciphers (AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305). OpenVPN ignores --cipher for cipher
  negotiations."
- **Check `a-client-on-the-class-cipher-connects`:**
  - a client that offers only AES-256-CBC (`data-ciphers AES-256-CBC`) logs in as p8vpnuser2;
  - the password is accepted, then the server logs "PUSH: No common cipher between server and client. Server
    data-ciphers: 'AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305', client supported ciphers 'AES-256-CBC'";
  - the client gets `AUTH_FAILED,Data channel cipher negotiation failed (no shared cipher)` and no tunnel.
- **Clients that also offer GCM connect**, and use AES-256-GCM, not the class's cipher (the set's first two clients,
  `IV_CIPHERS=AES-256-GCM:AES-256-CBC`).
- **So on 2.6 the `cipher` parameter has no effect:**
  - a client that uses only the configured cipher cannot connect;
  - every other client negotiates one of 2.6's defaults.

## Finding 2: the server no longer compresses what it sends
- **The baseline:** `$compression = 'comp-lzo'` (:30, "To disable compression this value needs to be set to 'none'")
  is passed as `compression` (:166); the rendered config holds `comp-lzo`.
- **What the server says at start**, verbatim: "WARNING: Compression for receiving enabled. Compression has been used
  in the past to break encryption. Sent packets are not compressed unless "allow-compression yes" is also set."
- **Check `the-data-channel-is-compressed-both-ways`:**
  - the node sends 20 zero-filled pings (1228-byte IP packets) to the first client, which replies;
  - UDP 1194 counters on the node:
    - sent: 1237 bytes per packet, uncompressed;
    - received: 139 bytes per packet, LZO-compressed by the client;
    - the reviewer's run measured 1237 and 140.
- **The data still flows:** clients with comp-lzo connect, and pings in both directions get through. Only the server's
  side of the compression is gone.

## Production use
- **openvpn_server:** 3 production node statements reach it, all through network_vpn (fleet_class_usage.md:
  via_composite=3).
- **network_vpn:** passes its own default `$openvpn_cipher = 'AES-256-CBC'` (network_vpn.pp:25, 57), so both findings
  reach every production use.
- **The production clients' configurations are not in this repository**, so whether any client offers only
  AES-256-CBC, or needs compression from the server, is not known.

## Options
### Cipher (finding 1)
- **A. Add the class's cipher to the server's data-ciphers.** For example,
  `custom_options 'data-ciphers' => "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:${cipher}"`.
  - A client on the class's cipher connects again, and modern clients keep negotiating GCM.
  - The fix is a manifest change under policy B, with no interface change.
- **B. Set `data-ciphers-fallback ${cipher}`.**
  - The OpenVPN 2.6 manual says this applies only to peers that do not negotiate ciphers (2.3-era clients). That is
    documented, not measured here.
  - It would not admit a 2.6 client that offers only CBC, the case measured above.
- **C. A and B together:** the class's cipher is accepted from both kinds of client.
- **D. No fix:** record that `cipher` is ineffective on OpenVPN 2.6 (the documentation list and the approval report),
  and have clients offer GCM.

### Compression (finding 2)
- **E. `allow-compression yes` on the server:** compression in both directions again, which re-enables what OpenVPN
  2.6 warns breaks encryption (compression attacks on the data channel).
- **F. Accept 2.6's receive-only compression:**
  - no fix, recorded as a behaviour change;
  - clients keep connecting, and only the server-to-client traffic is uncompressed.
- **G. Change the class's default to `compress migrate`, or to none.**
  - That is a change to the class interface's default, so it needs a ruling in any case.
  - The server would then ask clients to stop compressing.

**Recommendation:**
- **Cipher: A**, the smallest change that makes the class's declared cipher work again without refusing anyone 2.6
  admits today. Add B only if HQ knows of pre-2.4 clients.
- **Compression: F**, recorded. E trades a security default of the target release for bandwidth on one direction,
  and the class's purpose (a VPN that bridges clients) holds without it.

Either fix would be driven by these two checks, which fail before and would pass after (policy B), and recorded as a
local_changes.md row.
