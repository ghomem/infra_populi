# network_dhcp — behaviour finding: the DHCP interface is never brought up on Ubuntu 24.04 (2026-11-19)

Status: OPEN, for HQ. The reviewer reproduced it and confirmed that ifupdown-extra does not depend on ifupdown
(checks/reviews/network_dhcp/20261119T045534Z.json, set PASS with this finding, purpose covered). Escalated for this class under HQ batch-12 ruling 5: a finding whose fix has more than one
reasonable design. The run continues with the next class.

## What the class does
- It installs ifupdown-extra and declares `network_config { $iface: onboot => 'true', method => 'dhcp' }`
  (network_dhcp.pp:11-12).
- puppet-network writes that as an ifupdown stanza in /etc/network/interfaces (`auto p8test0`,
  `iface p8test0 inet dhcp`).
- The class's comment: it exists because the OpenVPN server class manages interface lo, and once Puppet manages one
  interface it has to manage all of them.

## What happens on the target release
- **The node:** Ubuntu 24.04 is netplan-only (/etc/netplan, systemd-networkd).
- **Checked after the class applied:**
  - ifupdown is not installed (ifupdown-extra does not pull it in);
  - there is no networking service and no `ifup`;
  - the stanza is written, but nothing reads it.
- **Check `the-boot-step-gives-the-interface-a-dhcp-address`** (results/network_dhcp/20261119T045009Z-author):
  - p8test0 is joined to a namespace where dnsmasq serves DHCP;
  - the step a boot runs for /etc/network/interfaces is found missing (`boot step: none`);
  - p8test0 gets no address.
- **The DHCP server works:** `dhcpcd -1 -4 p8test0`, run by hand, got 10.251.0.146/24 from it.
- **So** on Ubuntu 24.04 the class configures nothing that takes effect: the interface is never brought up with DHCP.

## Production use
3 production node statements declare the class (fleet_class_usage.md, unconditional row).

## Options (more than one reasonable design)
- **A. Install ifupdown too** (and enable its networking service). The stanza takes effect, but ifupdown and netplan
  then both manage interfaces, a known source of conflicts on 24.04.
- **B. Write the interface into netplan** (an /etc/netplan file with `dhcp4: true`, applied with netplan). This
  replaces network_config, a larger change of design.
- **C. Write a systemd-networkd .network file** for the interface. Close to B, without netplan.
- **D. No fix:** record that the class is ifupdown-only and does nothing on netplan systems, in the documentation list
  and the approval report.

**Recommendation:** decide together with the same question for the sibling network_static, which also uses
puppet-network on a netplan-only release. It has no check set yet, and no production statement declares it.
