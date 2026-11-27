# Draft: the module rename (HQ review of the behaviour suite, 2026-11-27, rulings 6-10) — work plan and state

Not applied by any tool. Moves out of drafts when the rename's stop report is written.

## Order (rulings 6-10)
1. Items 1-5 done: 6ceb826 (one gate), 2bd0899 (engine through the public runner), e99ca26 (mains only), dcd1366
   (scratch hook), 529cba7 (documentation list).
2. Item 6, package cache VM p8lab-cache (192.168.56.27, apt-cacher-ng :3142, http only, direct fallback):
   - cloned from ubuntu24-puppet8-Node @ P8NODE_BASELINE_GREEN_v5, 1 GB, 1 CPU; apt-cacher-ng installed;
   - hostname, machine-id, host keys regenerated, agent disabled and its ssl removed, netplan edited to .27 (not yet
     applied: reboot pending);
   - SLIP: the host keys were regenerated before the new key was read over the verified session (sshd loads keys per
     connection). The clone now presents ED25519 SHA256:Si8nIzdsbdOdXpPgmpDmnoE3gyN03VL4lryenfgXSi0 at .20; waiting
     for Salatiel's console comparison (first_contact's documented fallback). Not trusted until then.
   - Still to do: pin under alias p8lab-cache (~/.ssh/config + known_hosts, backups), reboot to .27, keyscan match;
     nodes.yml `services:` entry so lab_power starts it before the nodes and stops it by ACPI (never a hard
     poweroff: it is never reverted) and the sleep guard sees it; nodes' apt Proxy-Auto-Detect (http only, DIRECT
     when the cache does not answer), written by revert_node.sh for Debian-family kinds until a baseline carries it;
     verify on three package-heavy classes (packages_base, node_base, extra_packages? -> Debian ones: packages_base,
     node_base, filesystem_apt) that results are unchanged; drop it and report if any class differs.
   - Checked: no class purges /etc/apt/apt.conf.d; no template or check reads apt's configuration.
3. Item 7: one fresh node baseline (option A), with the cache setting if item 6 holds; commands the settings do not
   allow go to Salatiel.
4. Item 8, the rename (approved plan escalations/phase2-rename-plan.md + DESIGN_DECISIONS 2026-11-18 "HQ rulings on round 9", "E. Phase 2
   rename" + ruling 8). Forms: puppet_infrastructure -> infra_populi, Puppet_infrastructure -> Infra_populi,
   puppet-infrastructure -> infra-populi (covers /opt/puppet-infrastructure). Inventory (2026-11-27): 243 live files
   (91 manifests, 48 sets, engine tools and tests, node-examples, templates, rules, CLAUDE.md, metadata.json).
   Left as written: history (checks results/reviews/public records, reviews, runs, escalations, diagnosis, sprint,
   candidates, DESIGN_DECISIONS + CURRENT_RULES, checks/notes), the derived order file (regenerated), source refs
   (UPSTREAM_BASELINE.md, baseline.env, CLAUDE.md "Upstream reference ~/work/puppet_infrastructure", metadata.json's
   github.com/ghomem/puppet_infrastructure URLs: the new repo's URLs and first version are Salatiel's call).
   Pieces, each committed with tests before the rename is applied:
   A. module_name.py: the name from metadata.json (P2); the engine's ~60 literals use it; commit-subject searches
      accept the old and the new name (history is immutable); baseline comparisons (drift, DIFF A, classify_path,
      pregate hazard 8) normalise new -> old; tests with a renamed fixture tree.
   B. rename_module.py + rules/rename_scope.txt (excluded paths, protected patterns, reasons).
   C. rename_check.py, independent of B: same file set; excluded files byte-identical; each changed line = its old
      line with each old form replaced; no old form left outside protected patterns.
   D. Inventory of node-visible names (paths, units, cron, file content, class tags/catalog names, reports) and what a
      re-pointed node keeps -> documentation_list cutover section.
   E. Consumer conversion (puppet-nodes .pp, meaningful_puppet, Hashman's generated user declarations, Hiera keys,
      the operator's params directory file names) with a leftover check; synthetic fixtures only.
   Then: tag pre-rename; apply; rename_check; lab master: module dir and Hiera localdir switch in one deploy.
5. Item 9: re-verification on the public runner, every class on its node kinds (harness + behaviour set); reviewer
   confirms rename-only diff + green for every class (a rename mode), and re-runs every class whose node-visible names
   changed plus a random 15% of the rest. Item 10: failures escalated per class, pass continues; stop for HQ.
