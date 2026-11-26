# openvpn_set_vpn_passwd_file: authoring notes (the comments of .codex_state/checks/openvpn_set_vpn_passwd_file.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::openvpn_set_vpn_passwd_file (define; harness title the fixture's path; node
# kubuntu since 2026-11-21: a KDE desktop with kdialog and NetworkManager, which the ubuntu server node lacks). Fixture
# (params, never committed): file_path /usr/local/bin/set_vpn_passwd.sh, vpn_list [VPN1, VPN2, VPN4] (VPN4 since
# 2026-11-21), file_owner root.
# The script asks the user twice for a VPN password with kdialog and, when both match, sets it as the secret of every
# listed NetworkManager connection whose profile file /etc/NetworkManager/system-connections/<name> exists (the path
# openvpn_nm_connection writes). The exercise replaces the user at the dialogs with a stub kdialog
# (/var/tmp/p8test-kd/kdialog, first on PATH; /run is noexec) that replays scripted answers and logs each call, and
# writes VPN profiles as openvpn_nm_connection does, with password-flags=0 so NetworkManager stores the password itself.
# Measured while writing (2026-11-21, NetworkManager 1.46 on Kubuntu 24.04): modifying such a profile makes NetworkManager
# move it into netplan (/etc/netplan/90-NM-<uuid>.yaml) and delete the keyfile, so a second run of the script no longer
# finds it; escalations/openvpn_set_vpn_passwd_file.behaviour.md.
# Correction round 1, 2026-11-21 (review 20261121T163511Z, purpose): blank answers asked again; VPN4, a listed profile
# exactly as openvpn_nm_connection's template writes it (password-flags=1, permissions=user:p8testuser:;), expected to
# keep the password; cancel at either dialog leaving a listed connection's password as it was.
# Correction round 2, 2026-11-21 (review 20261121T164531Z, purpose; the last round, production use 0): every run here is
# root over SSH, with no desktop session or secret agent, so it cannot show what an agent-owned profile keeps; that check
# is removed and the outcome is an uncovered row (VPN4 stays in the setup as openvpn_nm_connection's profile shape).
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1).
# 2026-11-22 (HQ after batch 20, item 4, option A: the script asks NetworkManager whether a connection exists instead
# of testing its keyfile, local change #21): VPN1 now points at a real OpenVPN server on the ubuntu2 peer
# (203.0.113.50, routed on-link over the host-only network, a throwaway CA built on the node and handed over), which
# accepts p8testuser with the one password in its /etc/p8test-vpnpw/accepted; the peer switches that password between
# the two runs. After each run `nmcli connection up VPN1` must connect with the stored password (NetworkManager starts
# openvpn through network-manager-openvpn, installed by the setup when absent).
```
