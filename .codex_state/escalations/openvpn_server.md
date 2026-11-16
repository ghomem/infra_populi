# openvpn_server — category 1: puppetserver cannot load network_config when a relationship touches it (2026-11-16)

**Status: BLOCKED, category 1 (module level). Needs a ruling on the lab master's puppetserver configuration, which
also concerns a future production OpenVox master.**

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
