# openvpn_server (+ network_vpn): upstream defects that no module version fixes — RULED: fixed locally (option A)

Status: RULED 2026-10-27 — HQ production-facts ruling 2 (upstream defects fixed in infra_populi with the marker,
no escalation) → option A; entry `openvpn_server` in `.codex_state/upstream_defects.md`. Module: puppet-openvpn 12.0.0
(runtime is OpenVox). Originally escalated in sprint 4.2. Class content = release-0.9.10 (no drift). Production use: 3 node statements.
Module now in the lab: puppet-openvpn 11.0.1 (declares puppet AND openvox >=7 <9; sprint 4.1b). Params fixture
(untracked) uses RFC 5737 addresses and p8test interface names, so compile-only never touches a real NIC.

## Evidence (REAL compile-only on puppet8master, 2026-10-27)
1. `Duplicate declaration: Service[openvpn-server@puppet_infrastructure] is already declared at
   openvpn_server.pp:117; cannot redeclare` — our manifest declares `service { 'openvpn-server@puppet_infrastructure' }`
   and puppet-openvpn's server.pp declares `Service["${openvpn::server_service_name}@${name}"]` on systemd hosts
   (server.pp:269-271/518/544). Same title on every Debian/Ubuntu node with systemd → the class cannot compile there.
2. Probe with that service block removed (throwaway, reverted): the next error is
   `Could not autoload puppet/type/network_config: Attempt to redefine entity '.../network_config'` — a
   type-loading conflict between the generated pcore type (.resource_types/network_config.pp, 2026-09-30) and the
   Ruby type when both are loaded in this compile. network_dhcp and network_static (verified) still compile;
   only this class's catalog hits it. Not investigated further (module-level; next step is a hypothesis about the
   `Network_config[$local_interface]` subscription path, not a guess).
3. The diagnosis's other predicted defect (`notify => Service['openvpn']`, openvpn_server.pp:208) is NOT a compile
   error with 11.0.1: openvpn::service declares Service['openvpn'] whenever manage_service is true and
   namespecific_rclink is false (module defaults). Whether notifying the generic unit is meaningful on a systemd
   host is a behaviour question for the ruling.

## Options
- A (recommended): authorize, as an upstream defect fixed locally (marker per ck1 ruling 3), dropping our own
  `service { 'openvpn-server@puppet_infrastructure' }` and pointing the class's notifies at the module-managed
  `Service["openvpn-server@puppet_infrastructure"]`; then investigate defect 2 at module level before migrating.
- B: set the module's `manage_service => false` and keep our service resource (behaviour: the module stops managing
  the unit; ours does). Needs a check that nothing else in the module expects its service.
- ~~C: keep blocked until upstream fixes the class~~ — withdrawn: no upstream patches, no waiting on upstream (ruling 2).
Behaviour verification (Phase 3) additionally needs the second NIC (exists: vboxnet0/enp0s8) and a client VM.
