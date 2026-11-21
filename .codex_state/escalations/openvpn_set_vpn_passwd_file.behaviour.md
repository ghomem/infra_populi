# openvpn_set_vpn_passwd_file — behaviour finding (OPEN, for HQ: more than one reasonable design)

Production use 0 (migration_order.md). The define installs `templates/openvpn/set_vpn_passwd.sh.erb` (baseline cf477c6):
a script that asks a desktop user twice for a VPN password (kdialog) and, when both match, runs `nmcli connection
modify <name> vpn.secrets password=<...>` for every listed connection whose profile file
`/etc/NetworkManager/system-connections/<name>` exists. That is the path openvpn_nm_connection writes
(openvpn_nm_connection.pp:31).

## Finding — on Ubuntu 24.04 the script can set a connection's password only once
Measured 2026-11-21 on p8lab-kubuntu (Kubuntu 24.04, NetworkManager 1.46), with profiles written at that path as
openvpn_nm_connection writes them:
- The first run set VPN1's password (`nmcli -s -g vpn.secrets` gives `password = p8test-...`).
- The modification made NetworkManager move the profile into netplan: `/etc/netplan/90-NM-<uuid>.yaml`, active from
  `/run/NetworkManager/system-connections/netplan-NM-<uuid>.nmconnection`. It deleted
  `/etc/NetworkManager/system-connections/VPN1`. This is Ubuntu's NetworkManager-netplan integration (`ls` after the
  run: only the unmodified VPN3 kept its keyfile).
- From then on, the script's existence test (template line 20, `[ -f "$CONN_LOCATION" ]`) fails for that connection.
  A later run, the next password change, silently skips it and still ends "Configuration finished."
- The set's check `a-second-run-changes-the-password` expects the second run to change the password.

Two related effects, measured but not checks:
- **openvpn_nm_connection's own profiles keep no password.** They set `password-flags=1` (agent-owned).
  NetworkManager accepts the modification (its audit log: connection-update ... vpn.secrets ... success) but stores no
  agent-owned secret, so the script leaves nothing behind for those connections. The set uses `password-flags=0`
  profiles to show the script's own behaviour.
- **A profile managed by openvpn_nm_connection and migrated to netplan** would get its keyfile written back by the next
  agent run, beside the netplan copy (the same uuid in two places). Not exercised.

## Options
- **A: test for the connection, not the file.** In the script, `nmcli -g NAME connection show | grep -qx "$vpn_name"`
  replaces `[ -f ... ]`, so later runs find migrated profiles. This is the smallest change, and it fixes the
  second-run defect. It leaves the netplan migration and openvpn_nm_connection's rewrite as they are.
- **B: keep NetworkManager from migrating keyfile profiles to netplan** on desktops, a NetworkManager/netplan setting.
  This is a node-level change outside this define.
- **C: review the pairing as a whole:** how openvpn_nm_connection's profiles should hold the password (agent-owned
  versus system-stored), together with A or B.

This needs a ruling on the design, so the run continues; the class's behaviour state stays "finding" until HQ rules.
