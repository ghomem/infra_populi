# openvpn_server (and network_vpn) — stand-in lift "an extra network card on a gateway node" (OPEN, for Salatiel/HQ)

HQ after batch 20, item 6 asks for this lift. It needs a new lab VM and a choice of network, so it is escalated
(CLAUDE.md: new VMs or nodes are Salatiel's) and the run continues.

## The stand-in today
`p8test_dhcp_primary`: openvpn_server (declared by network_vpn) takes the gateway's primary interface, rewrites
/etc/network/interfaces for it, lo:0 and the bridge br0, and restarts ifupdown networking. The lab node's real NICs
are never handed over, so the fixture supplies p8test0, one end of a veth pair whose other end sits in a network
namespace where dnsmasq answers DHCP. What a GREEN does not show: a real uplink, with clients reaching the server over
the primary interface.

## Constraints
- Both classes run on the default node (ubuntu24-puppet8-Node). It is not a p8lab-* VM: lab_vm.sh may not modify it and
  raw mutating VBoxManage is denied.
- A NIC the class takes over must not be NIC1 (NAT: internet, DNS) or NIC2 (host-only: the harness's SSH).
- The class asks for DHCP on that interface, so the NIC's network needs a DHCP server.

## Options
- **A (recommended):** a new node kind `gateway`: `lab_vm.sh clone` of the Ubuntu server node's image as
  p8lab-gateway, with NIC3 on a VirtualBox internal network `p8lab-gw`; the ubuntu2 peer gets a NIC3 on the same
  network (a new ubuntu2 baseline snapshot, since a snapshot restore resets the VM's hardware), and its check serves
  DHCP there with dnsmasq. Clients on the peer then reach the OpenVPN server over the gateway's real uplink. New
  baseline snapshots, a nodes.yml entry, the plan's node column for both classes.
- **B:** the same gateway clone with NIC3 on VirtualBox NAT (its own built-in DHCP). One VM change only, but no client
  can reach the server through NAT without port forwarding, so the uplink is exercised only outward.
- **C:** a second host-only network (vboxnet1) with VirtualBox's DHCP: a host-level change, Salatiel's.
- **D:** keep the stand-in, for Salatiel's acceptance in the approval report.

A needs 4 GB free RAM to start (lab_vm.sh) and two new baseline snapshots; deleting anything stays Salatiel's.
