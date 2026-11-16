# Lab: the node intermittently gets no DHCPv4 lease on the bridged Wi-Fi NIC (2026-11-16) — batch 4 stopped

**Status: STOPPED for HQ.**
- Batch 4 stopped at 5/7 when openvpn_server's wrapper revert failed with `REVERT_FAILED`.
- No lab change was made in response. The node is restored to P8NODE_BASELINE_GREEN_v3, without an IPv4 address on
  NIC1.

## Evidence
- **13:51Z, the first failure.** A gnome_lock_screen reviewer revert left the node with only IPv6 on enp0s3 (DHCPv6
  `fd71:cd3c:36d5::afc`, no IPv4, no default route).
  - `apt-get update` exited 0 on its fetch failures, so the revert reported SUCCESS.
  - The apply then could not install dconf-cli.
  - The next revert, at 13:5x, got the usual lease (192.168.77.185) and apt was clean.
- **Engine response (1a24f54):** a revert now waits up to 60 s for an IPv4 default route and fails without one.
- **14:00Z, the second failure:** openvpn_server's wrapper revert hit that check (`ERROR: The node has no IPv4 default
  route after 60s`).
  - At 14:01:51Z, 80 s after link-up, the node still had no IPv4 lease.
  - systemd-networkd logged carrier at 14:00:31 and DHCPv6 at 14:00:34, and no DHCPv4 line.
- **The rest of the lab is unaffected:**
  - The master keeps its lease (192.168.77.166, not rebooted). The laptop is on 192.168.77.200 (it was .203 before
    step 10's Wi-Fi off/on).
  - The host-only path is unaffected: every check over 192.168.56.x passes.
- **Diagnosis (the cause is not proven):** the home router's DHCPv4 does not reliably answer a client bridged over
  Wi-Fi. VirtualBox's wireless bridging rewrites the frame source MAC, and some access points drop or mis-answer such
  DHCP requests. This is exactly the home-LAN dependency that the NAT plan removes.

## Options
1. **(Recommended) Review and run the NAT plan** (`escalations/lab-network-nat.md`), then resume batch 4 at
   openvpn_server.
   - With NIC1 on VirtualBox NAT, the node's IPv4 address and default route come from VirtualBox's own DHCP (10.0.2.x),
     independent of the router.
   - Its steps 1–3 and 5 need Salatiel.
2. **Retry now and resume batch 4 on the bridged NIC**, accepting the intermittent failures. The revert check fails
   closed, so no wrong result can be recorded; only time is lost.
3. **[HUMAN] Look at the router** (DHCP lease table, a reservation for the node's MAC 08:00:27:76:5E:C6).
   This keeps the home-LAN dependency.
