# Phase 2: renaming the module (draft for HQ review, read-only, 2026-11-18)

**Status: a draft, for HQ review. Nothing in it has been executed. HQ batch-8 ruling 7: "When items 1–6 are done, draft
the Phase 2 rename plan (read-only) and stop for HQ review."**

## What is being renamed (my reading, needs HQ confirmation)

**Proposal:** rename the module `puppet_infrastructure` to `infra_populi`, the name of this repository.
- CLAUDE.md fixes Phase 1 as "Namespace stays `puppet_infrastructure::`". Phase 1 is syntax only, so this is the first
  change that alters every name.
- Nothing in the repository defines Phase 2 further. The target name is my assumption: **HQ decision 1** below.
- Out of scope: the node data path `/opt/puppet-infrastructure` (Hiera `filesystem::localdir`) is a path on every
  node, not the module name. Renaming it would move live data on the fleet, so it is left alone (2 references).

## Inventory (counts only; fleet and consumer repositories read by names and counts, never content)

| where | what | count |
|---|---|---|
| module, manifests | `puppet_infrastructure::` (class/define names, `include`, `class { }`, resource references) | 206 in 91 manifests |
| module, manifests | `Puppet_infrastructure::` (capitalised resource references) | 3 |
| module, manifests | `template('puppet_infrastructure/…')` / `epp(…)` | 58 |
| module, manifests + templates | `puppet:///modules/puppet_infrastructure/…` file sources | 40 |
| module, templates | `scope['puppet_infrastructure::postfix_smtp_base::…']` (class variables read from ERB) | 3 (postfix_smtp_base maps) |
| module, templates | **generated Puppet code**: hashman writes `puppet_infrastructure::user {…}` / `user_sudoer` / `user_desktop` / `user_desktop_sudoer` declarations into its user database, and checks `puppet_infrastructure::hashman_web` by name | 6 lines in 2 templates (libhashman interface.py, miscutils.py) |
| module | `metadata.json` name `puppet_infrastructure` (version field says 0.9.4, stale against release-0.9.10) | 1 |
| module | names built at run time (`"puppet_infrastructure::${x}"`), `defined('…')`, `tag =>` | 0 |
| Hiera | explicit `lookup('puppet_infrastructure::…')` | 0 |
| Hiera, lab master | automatic-parameter keys `puppet_infrastructure::<class>::<param>` | 3 (all p8test fixtures in data/p8test_fixtures.yaml) |
| consumer `puppet-nodes` | references (node definitions; .pp only, no YAML keys) | 209 in 51 files |
| consumer `meaningful_puppet` | references (meaningful_desktop etc.) | 18 in 5 files |
| lab master | node files naming the module | 5 |
| engine (`.codex_state/tools`) | literal `puppet_infrastructure` (the harness prefix, review, pregate, phase3, records) | 193 in 36 files |
| engine state | plan, order file, tracker, check sets | short names, mostly unprefixed; `derived_from` paths (`manifests/x.pp`) do not carry the name |

## Hazards the plain text count does not show
1. **hashman's generated user database.**
   - The master's code tree holds files hashman wrote, declaring users as `puppet_infrastructure::user…`. Those files
     are production data, not in any repository counted here.
   - A rename must convert them with the code, or keep the old class names resolvable, or every user declaration on the
     fleet fails to compile.
   - The count of such files needs a read on a production master: **HQ/Salatiel**.
2. **Templates that read another class's variables by full name** (`scope['puppet_infrastructure::postfix_smtp_base::…']`).
   They must change together with the class name. A miss renders an empty or failing map, not a compile error at the
   class.
3. **Resource references with a capital letter** (`Class['Puppet_infrastructure::x']`, `Puppet_infrastructure::X[...]`).
   A lowercase-only search misses them.
4. **Automatic parameter lookup keys** (`puppet_infrastructure::<class>::<param>`) in production Hiera.
   - None appear in `puppet-nodes`, which keeps node data in .pp, and the lab master holds only p8test keys.
   - Production Hiera outside these repositories is not inventoried: a read is needed (**HQ/Salatiel**).
   - A missed key silently drops to the class default. It does not fail, which is the worst failure mode here.
5. **Reports, monitoring and PuppetDB queries** that match class or resource names. sysmon_puppet_cert_status and
   any report parsing were not inventoried; this needs one read of the monitoring side, which lives in another
   repository.
6. **Two production generations at once.** The laptop and the fleet run Puppet 5 with `puppet_infrastructure` until
   the cutover, so the rename cannot reach production before the Puppet 8 cutover. Its order relative to the cutover
   is **HQ decision 2**.

## Options for the order (HQ decision 2)
- **A. Rename at the cutover, in one step (recommended).**
  - The lab carries `infra_populi` from Phase 2 on, and production receives module, node definitions and data
    together at the cutover.
  - One renaming, and no period with two names.
  - The cutover change is larger, so it needs the conversion script and the hazard reads above done first.
- **B. Rename after the cutover.**
  - Cut over to Puppet 8 still as `puppet_infrastructure`, then rename as a separate production change.
  - Two production changes, each smaller and each verifiable alone.
  - The fleet gets one more coordinated node-definition change.
- **C. A transition shim.**
  - Ship `infra_populi` plus a thin `puppet_infrastructure` module whose classes and defines wrap the new ones.
  - Not recommended:
    - every define needs its full parameter list duplicated;
    - resource references and relationships to the old names (`Class['puppet_infrastructure::x']`) do not follow a
      wrapper;
    - hashman's generated declarations would keep the old names alive indefinitely.

## Mechanics (proposed; not executed)
1. **One scripted rename of the module tree**, reviewed as a pure rename. The script:
   - replaces exactly the six token forms in the inventory (`puppet_infrastructure::`, `Puppet_infrastructure::`,
     `template(`/`epp('puppet_infrastructure/`, `puppet:///modules/puppet_infrastructure/`, `scope['puppet_infrastructure::`,
     the hashman generator strings) and `metadata.json`'s name;
   - also corrects metadata.json's stale version to the baseline's;
   - prints every replaced line.

   Verification: a new engine check, `rename_check.py`, normalises the new name back to the old in the renamed tree and
   requires a byte-identical result against the pre-rename commit. Any other difference fails it. This is the
   rename's equivalent of DIFF A.
2. **Engine:**
   - The 193 literals become one constant, the module name. Single source (P2): read from metadata.json.
   - The harness, pregate, review, phase3 and records tools take it from there. The tracker, plan and check sets keep
     short names.
   - The lab master's module directory and node files switch with one deploy.
3. **Verification in the lab, before any production step:**
   - compile every class and the standing composites under the new name;
   - harness GREEN for all done classes (a full pass, about 92 runs);
   - reviewer per class in a new rename mode: DIFF = rename only, plus the usual harness gate;
   - re-run every Phase 3 check set (their probes name paths and services, not the module).

   This is the largest lab pass so far: roughly two days of lab time at the current per-class times.
4. **Consumers:**
   - a conversion script for `puppet-nodes` (209 references) and `meaningful_puppet` (18), run and reviewed in those
     repositories;
   - hashman's generated database converted by the same script on the master's code tree;
   - production Hiera keys renamed from the inventory read in hazard 4.

   Owners and timing are **HQ decision 3**.
5. **Commits:** one `P2: rename module to infra_populi` commit for the module tree, one engine commit, one per consumer
   repository. Each carries its own verification evidence.

## Decisions needed from HQ
1. The target name: `infra_populi` (my assumption) or another.
2. The order relative to the Puppet 8 cutover: A (recommended), B or C.
3. Who reads production for hazards 1, 4 and 5 (hashman's generated files, production Hiera keys, report and
   monitoring consumers), and who owns the consumer-repository conversions.
4. Whether Phase 2 waits for the done-class backfill after the 23rd (HQ batch-4 item 8) or runs alongside it.
