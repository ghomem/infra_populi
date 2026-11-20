# network_static — behaviour finding: the default route never applies (it names eth0) (2026-11-20)

Status: CLOSED 2026-11-20. HQ: keep and fix (the baseline's parameters show the gateway belongs to $iface); local change #12, interface => $iface: Phase 1 PASS 20261120T084744Z, Phase 3 PASS 20261120T085040Z (the default route through the gateway on the configured interface). Was: OPEN, for HQ. The reviewer reproduced it on a fresh node (checks/reviews/network_static/20261120T012645Z.json, set
PASS with this finding, purpose covered) and confirmed the mechanism: ifupdown-extra's if-up.d/20static-routes applies
only routes lines whose last field matches the interface being brought up ($IFACE).
Escalated for this class under HQ batch-12 ruling 5: the fix has more than one reasonable design. The run continues.

## What the class does
- It declares `network_config { $iface: method => 'static', ipaddress => $ipaddress, onboot => 'true' }` and
  `network_route { 'default': gateway => $gateway, interface => 'eth0', ... }` (network_static.pp:12-13 at the
  baseline).
- The route's interface is hard-coded to `eth0`, whatever `$iface` is.
- puppet-network writes it to /etc/network/routes as `default 0.0.0.0 <gateway> eth0`. ifupdown-extra's
  /etc/network/if-up.d/20static-routes applies a routes line only when its interface comes up.

## What happens on Ubuntu 24.04
Run results/network_static/20261120T011857Z-author, after local change #11 (ifupdown declared, HQ batch-15 ruling 5):
- p8test0 comes up through ifupdown with 192.0.2.10/24, and the gateway 192.0.2.1 answers;
- p8test0 keeps its address through a restart of networking, and the node's internet stays on enp0s3;
- **no default route through the gateway is installed**: check `the-default-route-goes-through-the-gateway` reads `0`.

Ubuntu 24.04, like every release with predictable interface names, has no eth0, so the line is never applied. The
same holds for any `$iface` other than eth0, on any release.

## Production use
- 0 production node statements declare network_static (fleet_class_usage.md).
- Its sibling network_dhcp (3 statements) has no route.

## Options
- **A. `interface => $iface`.** The route goes up with the configured interface.
  - **Caution:** the route carries no metric. On a node where another interface already holds the default route (a
    netplan-managed primary, as in the lab), it takes over the node's default route.
  - A check for A would need a node where that is the intent.
- **B. The gateway in the interface stanza** (puppet-network's `options => { 'gateway' => $gateway }`), so ifupdown
  itself sets it. The same caution as A applies.
- **C. No fix.** Record that the class sets the static address and no route on releases without eth0 (the documentation
  list and the approval report).
- **D. Retire the class.** No production statement uses it.

**Recommendation:** D, or C if HQ keeps the class for later use. The class is unused, and A or B would change a node's
default route, which deserves a production need before a design.
