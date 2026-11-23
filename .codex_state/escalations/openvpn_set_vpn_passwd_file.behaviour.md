# openvpn_set_vpn_passwd_file — behaviour finding (FIXED: local change #21, HQ after batch 20 item 4, option A)

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

Two related effects:
- **openvpn_nm_connection's own profiles (`password-flags=1`, agent-owned): not established.** Run as root over SSH,
  the script's update of such a profile was accepted (audit log: connection-update ... vpn.secrets ... success) and no
  secret could be read back (`VPN4: []`, run 20261121T163922Z). Review 20261121T164531Z showed this says nothing about
  the class: an agent-owned secret is saved only through the desktop user's session agent (plasma-nm with its wallet),
  and the run had no such session. That check was removed in round 2. The question stays open, as an uncovered row,
  until a fixture user's Plasma session can run the script.
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

## Round 1 (2026-11-21, review 20261121T163511Z)
The set now also exercises blank answers, cancel at either dialog (a listed connection keeps its password), and VPN4,
a listed profile exactly as openvpn_nm_connection's template writes it. Run 20261121T163922Z: every dialog path passes.
Two checks fail, both findings described above: `a-second-run-changes-the-password` and
`an-openvpn-nm-connection-profile-keeps-the-password`.

## Round 2 (2026-11-21, the last; review 20261121T164531Z)
The agent-owned check was removed, being unobservable as root, and its outcome is an uncovered row. The one finding
stays: a second run cannot find a profile that NetworkManager moved into netplan.

## Resolution (2026-11-23)
HQ after batch 20, item 4 chose option A: the script asks NetworkManager whether each listed connection exists
(`nmcli -g NAME connection show`, matched exactly) instead of testing its keyfile; the password is still set through
`nmcli connection modify ... vpn.secrets`. Local change #21 (a776f84). The set now proves it end to end: VPN1 connects to
an OpenVPN server on the ubuntu2 peer that accepts one password at a time, switched between the two runs.
- before (results/openvpn_set_vpn_passwd_file/20261123T000353Z-author): run 1 sets p8test-pass-a and VPN1 connects; run
  2 leaves p8test-pass-a and the connection fails (up rc 4);
- after (20261123T002025Z-author, on the recorded code): run 2 sets p8test-pass-c and VPN1 connects with it;
- Phase 1 review PASS (20261123T003152Z; the first review, 20261123T002612Z, failed on records only: a '|' in row
  #21's change cell); Phase 3 review PASS (20261123T003637Z).
The agent-owned profile (openvpn_nm_connection's password-flags=1) stays an uncovered row, lifted by a fixture user's
Plasma session.
