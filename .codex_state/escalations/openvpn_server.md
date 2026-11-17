# openvpn_server — category 1: puppetserver cannot load network_config when a relationship touches it (2026-11-16)

**Status (2026-11-17, HQ batch-7 ruling 5): the load error is RESOLVED at step (b), with no master change. Still
BLOCKED (category 1) on two defects of the class with puppet-openvpn on systemd hosts, which need an HQ ruling (section
"HQ ruling 5" at the end). The original 2026-11-16 analysis below is kept unchanged.**

## What happens
The batch-5 Codex dispatch fixed the ruled duplicate service (preserved as `candidates/openvpn_server.partial.pp`).
The fresh-node harness run (NODE_FRESH yes) then failed at catalog retrieval:

```
Error: Could not retrieve catalog from remote server: Error 500 on SERVER: Server Error: Could not autoload
puppet/type/network_config: Could not autoload puppet/provider/network_config/interfaces: no such file to load --
puppetx/filemapper on node puppet8node
```

puppetserver.log (2026-11-16T18:43:54Z), call path:
`relationship_validator.rb:29 validate_relationship` → `puppet/resource.rb:390 resource_type` →
`autoload.rb` loads `modules/network/lib/puppet/type/network_config.rb:9` → loads the `interfaces` provider →
`interfaces.rb:1 require 'puppetx/filemapper'` → not found.

## Why only this class
- **The trigger is a relationship:** the server validates relationships, and validating one whose target is a
  `network_config` loads the Ruby type, even though `puppet generate types` has made the pcore type
  (`.resource_types/network_config.pp`).
- **openvpn_server has such relationships:** `subscribe => Network_config['lo', $lan_iface, $local_interface,
  $lan_bridge_iface]` on three resources (manifests/openvpn_server.pp, baseline content).
- **The plan's `required_external=network` has one too:** the module's `class network` declares
  `Package[$ipaddress] -> Network_config <| |>`, another such relationship.
- **Control:** network_dhcp (done; no relationship on its `network_config`) went GREEN through puppetserver in the
  same session.
- **Why compile-only missed it:** the `puppet catalog compile` CLI (compile-only, classify_path) puts module lib dirs
  on Ruby's load path, so it compiles. puppetserver's JRuby load path is only
  `/opt/puppetlabs/puppet/lib/ruby/vendor_ruby`, and its libdir `/opt/puppetlabs/server/data/puppetserver/lib` is
  empty.

## Module level (researched)
- puppet-network 3.0.0 (2026-09-14, newest) has the same `require 'puppetx/filemapper'`; its changelog only adds a
  README note that `puppet generate types` is needed (already done here).
- puppet-filemapper 5.0.0 (newest) still ships `lib/puppetx/filemapper.rb`; nothing about loading changed. Allowing
  it in puppet-network (#373) was closed, not merged.
- The upstream issue (voxpupuli/puppet-network #77, closed) gives the workaround: the master must have the module's
  plugins on its own load path ("pluginsync the master", `puppet plugin download` on the master).

## Options (HQ)
1. **Lab master: add the module lib to puppetserver's JRuby load path.** Add a `ruby-load-path` entry in
   `/etc/puppetlabs/puppetserver/conf.d/puppetserver.conf` for
   `/etc/puppetlabs/code/environments/production/modules/filemapper/lib`, then restart puppetserver. It is small and
   reversible, but environment-specific (the path is the production environment's module directory) and a
   lab-master configuration change.
2. **Lab master: pluginsync into puppetserver's libdir.** Put the environment's plugins into
   `/opt/puppetlabs/server/data/puppetserver/lib`, which Puppet puts on the load path. It must be repeated after every
   r10k deploy (it could go into master_fixtures.sh).
3. **Keep blocked** until production's arrangement is known. If the production master pluginsyncs itself into the
   server's libdir, option 2 is the faithful copy. Worth one read-only look on puppet.mdops.es.

Recommendation: 3, then 2 if production does it, otherwise 1. Every class with a relationship on `network_config`
or `network_route`, and every node that declares `class network`, will meet this on an OpenVox 8 server. Today that
is openvpn_server; network_vpn is worth checking when it comes up.

## HQ ruling 5 (2026-11-17): which step resolved it — (b)
1. **(a) Fleet data** (puppet-nodes 0941beb, names and counts only): network_vpn is declared by 1 production node
   statement that covers 3 servers. The same statement declares `puppet_infrastructure::network_dhcp` with
   `iface => $::networking['primary']`, which is openvpn_server's `$local_interface` default. So in production
   `Network_config[$local_interface]` is declared by **network_dhcp**. No production node, meaningful_puppet class or
   puppet_infrastructure manifest declares `class network` (0 matches). The plan's `required_external=network`
   (a55a24b) was my wrong assumption; corrected to `required_base=network_dhcp` (30c1ea7).
2. **(b) Compiled through puppetserver with network_dhcp in the same catalog** (harness, fresh node; params fixture:
   local_interface = network_dhcp's iface p8test0, lan_iface p8test2; logs `.codex_state/logs/openvpn_server.hq5-*.log`):
   - with the plan's old `class network` as well: `Duplicate declaration: Package[ifupdown-extra]` (network_dhcp.pp:13
     vs network/init.pp:67), the evidence for (a)'s correction;
   - with required_base network_dhcp: **no filemapper error**. The catalog evaluates and fails on the next, unrelated
     error (item 3.1 below);
   - with that notify retargeted (a throwaway probe, never committed): "Catalog compiled by puppet8master", then the
     agent applies and stops on a dependency cycle (item 3.2).
   - **The cause, corrected:** the relationship validator looks each target up with `catalog.resource(ref)`
     (relationship_validator.rb:29). Only when the direct title lookup misses does `Catalog#resource` build a
     `Puppet::Resource` to try aliases (catalog.rb, `resource`), and building one resolves the type
     (resource.rb:390). So the type is loaded only for a target MISSING from the catalog. `Network_config[p8test2]` (the fixture's `$local_interface`, declared by nothing in the
     lab catalog) was such a target. Resolving its type loaded the Ruby type, and the failed `puppetx/filemapper` load
     hid the real error, which was "could not find resource". In production network_dhcp declares it, so production
     never takes that path, which is consistent with HQ's finding that production has no special master setting.
   - **Steps (c) and (d) were not needed.** No master change was made, and nothing goes on the production-master
     requirements list.
3. **Remaining blockers (class level, need an HQ ruling):**
   1. **`notify => Service['openvpn']` (baseline openvpn_server.pp:208, on File['/etc/openvpn/openvpn-up.sh']).**
      puppet-openvpn declares `Service['openvpn']` only when `$facts['service_provider'] != 'systemd'` (init.pp:67-73,
      identical in 8.3.0, production's version, and in 11.0.1 and 12.0.0). Error on the node: "Could not find resource
      'Service[openvpn]' in parameter 'notify'".
      - **Correction:** my 2026-10-27 analysis (openvpn_server-upstream-defects.md item 3) said the module always
        declares it. That came from compile-only, whose fact set has no `service_provider`.
   2. **The ruled change (option A) creates a dependency cycle.** It keeps every notify that targeted our service and
      points it at the module's `Service['openvpn-server@puppet_infrastructure']`. One of those notifies sits on
      `openvpn::server { 'puppet_infrastructure': … notify => … }` itself (baseline :186), but the module declares that
      service INSIDE that define (server.pp:518-526). Result: `Service[openvpn-server@puppet_infrastructure] =>
      Openvpn::Server[puppet_infrastructure] => Service[...]`.
   - **Options:**
     - (A) drop the define's own notify (the module already notifies its service for its own config through
       `$lnotify`), and retarget :208 to the module's unit, the one the server runs as on systemd;
     - (B) set the module's `manage_service => false` and keep the class's own service resource, as the baseline does.
       This is option B of the 2026-10-27 escalation, and :208 still needs a target.
   - **Recommendation: (A).** It extends the ruled direction, and the module stays the owner of the unit.
4. **Production:** on a systemd host, the baseline cannot compile against puppet-openvpn 8.3.0 either: the
   duplicate service (option A's subject) and the missing `Service['openvpn']`. So the 3 production servers either do not run this
   baseline content or have `service_provider` other than systemd. One read-only fact would settle it: the
   `service_provider` fact, or the openvpn_server content, on one of them.
5. **Pregate:** hazard14-module-base still reports `network_config` without `class network`, for openvpn_server and
   for network_dhcp (done). In production the base class is declared nowhere, and network_dhcp installs ifupdown-extra
   itself, so the hazard's premise ("production declares the base elsewhere") does not hold for this module.
   - When the class is unblocked, classify_path will route it to context-gap. That needs either a per-class "standalone
     by production evidence" entry for hazard 14, or Codex's dispatch with the finding explained. I will propose the
     former with the ruling.
