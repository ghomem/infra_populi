# openvpn_nm_connection: authoring notes (the comments of .codex_state/checks/openvpn_nm_connection.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::openvpn_nm_connection (define, title p8test-vpn; node gnome, Ubuntu 24.04
# GNOME with NetworkManager 1.46 and network-manager-openvpn; MOCK-APPLY: node fixture p8test_vpn_ca declares the CA file
# the define requires, from the master's throwaway PKI). Fixture (params, never committed): vpn_username and
# local_username p8testuser, remote 203.0.113.50 (RFC 5737), ca_crt /etc/p8test-vpn/ca.crt; cipher at its default.
# Migrated with the ruled fix fqdn_rand_uuid -> stdlib fqdn_uuid (upstream_defects.md): the UUID is the RFC 4122
# version-5 UUID of the connection name in the DNS namespace, df2d3b4d-5aa3-564f-92d4-fd9bac9644f9 for p8test-vpn.
# Probes read the node's own NetworkManager (nmcli) and files only.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1); the uncovered row in the current form.
# Correction round 1, 2026-11-21 (review 20261121T034103Z, purpose): the connection is exercised. The node builds a
# throwaway CA and server certificate, replaces the fixture CA file the profile names (a node fixture, p8test_vpn_ca,
# not the class's file) and routes 203.0.113.50 on-link over its host-only interface; the peer ubuntu2 holds that
# address and runs an OpenVPN server (tap, password check, AES-256-CBC accepted, LZO) with the handed-over certificate;
# nmcli supplies the agent-owned password from a file (passwd-file), so no desktop session is needed. Prototyped.
  # 2026-11-17 authoring correction (run 1, 20261117T220444Z): `nmcli -g` escapes the ':' inside a value, so the
  # permission prints as `user\:p8testuser`; the profile file holds `permissions=user:p8testuser:;` as the template
  # renders it. The expectation now matches the escaped form; the behaviour is unchanged.
```
