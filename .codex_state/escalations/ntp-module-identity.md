# ntp module for node_base (58 servers): needs production information before a pin

Status: ESCALATED 2026-10-27 (sprint 4.1b/4.2). Blocks node_base (composite node_base_debian: `Could not find
class ::ntp`, node_base.pp:159) and node_base_domain_desktop.
The production master's ntp module identity and version were never read (diagnosis C13); production runs
Puppet 5.5.22 with hand-deployed modules (no Puppetfile). node_base declares `class { 'ntp': ... }` (node_base.pp:155) and, on another branch,
`class { 'chrony': }` / `include ::chrony` (node_base.pp:142-146): BOTH module identities are needed. ntp candidate: puppetlabs-ntp 11.0.0 (puppet >=7 <9, stdlib >=4.13.1 <10 — inside the lab's
stdlib 9.7.0), listed in `.codex_state/lab/Puppetfile.openvox-only.prepared` as NOT a pin decision.

## Needed (Salatiel, read-only on production)
`ls /etc/puppetlabs/code/environments/production/modules/ntp/` + its `metadata.json` (name, version) and the
module providing `chrony`, if any. With that: pick the Puppet-8 release of the same module whose parameters match
node_base's call (advisor tier), pin, compile.

## Resolved 2026-10-27 (production read-only, `puppet module list` on puppet.mdops.es)
- puppetlabs-ntp v8.5.0
- puppet-chrony v1.0.0
HQ ruling: pin the Puppet-8-compatible release of each on the lab, inside the module's declared range (ruling 9 applies: openvox-only releases go to the prepared list, not applied). Confirm from node_base.pp which of the two is included under which condition, and record both pins with versions in the Puppetfile export.
