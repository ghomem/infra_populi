# Engine diagnosis — infra_populi Phase-1 migration engine

Date: 2026-10-26. Author: advisor (Claude). Mode: read-only diagnosis; nothing outside `.codex_state/diagnosis/` was written, no VM/master/node state changed, no `puppet agent` run, no commit.

Evidence conventions: `file:line` = path in `~/work/infra_populi` unless prefixed; `<hash>` = commit in this repo; `upstream` = `~/work/puppet_infrastructure`; `log:` = `.codex_state/logs/<file>`; `report:` = agent report YAML copied read-only from the master (`/opt/puppetlabs/server/data/puppetserver/reports/puppet8node/`). "unverified" marks statements I could not confirm from an independent source. Code comments were treated as leads only.

Companion files in this directory: `2026-10-26-summary.md` (one page), `fleet_class_usage.md` (section B data), `metrics.csv` (section C data, one row per attempt/event).

---

## A. State reconciliation

### A.1 Counts, by source

| Source | done | blocked | gated | owner-validated | pending | total | evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| git (`P8: migrate` commits, unique classes, minus blocked) | 31 | — | — | — | — | — | `git log --format=%s \| grep 'P8: migrate'` = 32 commits, 31 unique (network_dhcp twice: 48fc434 reverted by 03cb002, re-done 0ecf985) |
| `migrated_classes.txt` (lines containing `Done`) | 31 | — | — | — | 56 lines without `Done` | 87 | file has 87 lines; forms `X Done`, `Done X`, `X Done [from: release-0.9.8]`, and one mixed `Done filesystem_yum [from: release-0.9.8]` |
| `blocked.txt` | — | 7 | — | — | — | — | 7 non-comment lines, all with a category |
| `migration_order.md` (generated 2026-10-05 14:11 UTC) | 31 | 7 | 1 (network_vpn) | 1 (postfix_smtp_base_config_file) | 47 | 87 | `migration_order.md:9`; `status.py` re-render today gives the identical line |
| `migration_plan.md` rows | — | — | — | — | — | 87 | table rows |
| `release-0.9.8` manifests | — | — | — | — | — | **90** | `git -C upstream ls-tree release-0.9.8 manifests/` |
| upstream HEAD (0.9.10 + Issue #122 work) | — | — | — | — | — | 92 | adds `mariadb_server.pp`, `mysql_db.pp` |

The three sources that are supposed to agree (git, tracker, order file) agree: 31/31/31. The brief's "~28 of 87" undercounts by 3; 31 is the figure.

### A.2 Inconsistencies found (each is a finding)

1. **Scope gap: 3 classes exist in the declared baseline and are used in production but are absent from the plan, the tracker and `manifests/`.** `firewall_ipv6_drop_policy_desktop`, `gnome_lock_screen`, `rsyslog_apparmor_exception` are in `release-0.9.8` (90 manifests) but not in the 87 local manifests (`d93f147 Baseline import` predates them). Fleet data: `meaningful_puppet::meaningful_desktop` declares `gnome_lock_screen` and `firewall_ipv6_drop_policy_desktop` (so the whole 20-laptop desktop fleet depends on them) and one production server declares `rsyslog_apparmor_exception` directly (see `fleet_class_usage.md`). The engine cannot reach "all 87 done" and still break the company layer.
2. **SKILL.md references a "7-item checklist" (`.claude/skills/migrate-next/SKILL.md:16`) while CLAUDE.md has 8 items** (item 8, baseline drift, added 2026-10-01 in 1341285 / CLAUDE.md). The runbook (`~/.config/infra_populi/CODEX_RUNBOOK.md` §5) carries a third, differently-worded hazard list with 8 bullets that lacks item 8 and item 7's exact wording. Three copies of one checklist, all hand-maintained.
3. **Design log vs reality on the toolchain.** `DESIGN_DECISIONS.md` 2026-07-26 records Codex 0.145.0 and model `gpt-5.6-sol`. Actual: `codex-cli 0.159.2`, `~/.codex/config.toml` model `gpt-6.1-sol` (config backups `config.toml.bak.20260930_234019` show the change happened 2026-09-30); every log header reads `OpenAI Codex v0.159.2 / model: gpt-6.1-sol`. No decision entry records the change. The `user_kde_lock_screen_common` run also shows Codex loading a plugin skill (`~/.codex/plugins/cache/openai-curated-remote/superpowers/6.4.2/...`, `log:user_kde_lock_screen_common.1791208431.log:111,183`) — an undocumented behaviour-shaping input to the executor.
4. **Design log superseded in practice without a superseding entry.** 2026-07-01 "Generation model: Codex GENERATES + COMMITS all in-repo artifacts; artifacts are born via Codex, never in Claude's environment" is contradicted by current practice: baseline-syncs (eb024e1, 5e00660, dd3e1dc), plan fixes (11 `plan(...)` commits), blocks/escalations and decision entries are advisor-authored, and the 2026-10-01 ruling explicitly says "advisor tier; it is a verbatim copy, so no Codex call". Git is the fact; the log should say so.
5. **`blocked.txt` entries are not refreshed when the diagnosis moves.** `firewall_addon_openvpn_server` still says "no sysctl module ... Forge search found no module stating Puppet 8 support" (`blocked.txt:5`), while the 2026-09-30 decision entry identifies production's `thias-sysctl 1.0.7` and a candidate replacement (`puppet/augeasproviders_sysctl`). `extra_packages_el` still says "a RHEL9 VM exists — state unverified"; verified today: `RHEL9` VM powered off since 2025-04-10, snapshot "Joined to Puppet" taken against the old Puppet 5 master (`.vbox` timeStamp 2025-04-10T12:53:31Z).
6. **`UPSTREAM_BASELINE.md` carries a stale "KNOWN INCONSISTENCY" about `migrated_classes.txt`** (lines 48-52) that the 2026-07-01 decision "migrated_classes.txt was already correct (no fix)" retired. It is a current-state document that was not updated.
7. **Tracked/untracked boundary is inconsistent and causes friction.** `.codex_state/` is excluded wholesale via `.git/info/exclude` (local-only, not `.gitignore`), yet 18 files under it are tracked. Consequences: every new tracked file needs `git add -f` (SKILL.md step 2; Codex logs show `git check-ignore`/`git add -f` probing in 5 of 8 runs); a fresh clone has no exclude at all; the wrapper tells Codex "Do not force-add ignored trackers" while the skill tells the advisor to force-add — contradictory. `necessary_modules.txt` is untracked (per CLAUDE.md) but the wrapper asks Codex to record modules there; it carries no versions, so it cannot reproduce the master.
8. **The Codex authority document is unversioned.** `~/.config/infra_populi/CODEX_RUNBOOK.md` (8.7 KB, mtime 2026-09-01) is injected verbatim into every run (`codex_migrate_class:33`) but lives outside the repo with no history. The wrapper copy at `~/.local/bin/codex_migrate_class` is a plain copy of the tracked one (identical today, can drift); `test_class.sh` is a symlink (good). `~/.local/bin/infra_populi_tools/` also holds `test_class.sh.bak` and `.presymlink` leftovers.
9. **Module version truth lives only on the master.** The Puppetfile with pins (`/home/deployment/infra_populi_env/Puppetfile`) is on the master VM, which must never be restored (its `P8MASTER_BASELINE_GREEN` snapshot of 2026-06-30 says "7 modules"; the master now has 18 + `puppet_infrastructure`). A master disk loss loses the pins; `necessary_modules.txt` has names only. Also: `mod 'saz-resolv_conf'`, `'puppetlabs-stdlib'`, `'puppetlabs-resource_api'`, `'puppetlabs-puppetserver_gem'`, `'saz-sudo'` are **unpinned** in that Puppetfile, violating the 2026-09-30 rule "never leave `mod` unpinned".
10. **`puppet module list` on the master warns about missing `puppetlabs-powershell` and `puppetlabs-reboot`** (dependencies of docker 10.4.1). The project rule treats only `invalid` as failure; the warning class is unhandled (Windows-only deps; harmless, but the rule should say so).
11. **`metadata.json` says version 0.9.4** both locally and at `release-0.9.8`; the master lists `puppet_infrastructure (v0.9.4)`. Cosmetic, but it makes "which baseline is deployed" unreadable from the master.
13. **Tracker typo:** `migrated_classes.txt:42` reads `nginx_proxy_smtp_autha`, not `nginx_proxy_smtp_auth_ppa`. The order file is unaffected (it derives from git and the plan), but any tool that matches tracker lines by name will miss this class.
12. **Logs are not durable.** `.codex_state/logs/` is excluded from git; all throughput evidence in section C exists on one laptop. The reviewer's verdicts are not persisted anywhere (they exist only in the advisor's chat context).

---

## B. Fleet usage

Full table: `fleet_class_usage.md`. Method: transitive closure over three layers (node files → `meaningful_puppet` → `puppet_infrastructure` composites), names-and-counts only; `passwd/` not read.

### B.1 Shape of the fleet
- 47 node files in 9 groups. Production: 58 server node statements across 6 production groups, plus 1 regex desktop statement (≈20 laptops per the CTO document). Excluded: 9 deleted statements and 1 test statement. The 58 matches the CTO document exactly. Group names are deliberately not reproduced here.
- **Every server declares `puppet_infrastructure::node_base` directly** (58/58, plus all deleted and the test node). The server fleet therefore stands or falls on `node_base`'s closure: packages_base, sysmon_base, ssh_secure, firewall_secure (or firewall_secure_extra), firewall_ipv6_drop, filesystem_base, filesystem_apt + filesystem_lib64 (or filesystem_yum on RedHat), filesystem_sec, puppet_boot_run, dns_client, plus external `ntp`/`chrony`.
- **The desktop fleet does not use `node_base_desktop`/`node_base_domain_desktop` at all.** It uses `meaningful_puppet::meaningful_desktop`, whose puppet_infrastructure closure is: filesystem_base_desktop, firewall_ipv6_drop_policy_desktop (missing locally), firewall_secure, gnome_lock_screen (missing locally), packages_base, rsyslog_client, user_kde_lock_screen, user_kde_lock_screen_common, filesystem_base, rsyslog_base.
- `rsyslog_client` is declared directly by 57 server statements (not via node_base); `docker_container` directly by 13; the nginx stack reaches 24–37 servers mostly via the company classes `adam_nginx` (12 nodes), `vtlsuite_nginx`/`vtlsuite_nginx2` (8 each), `md_simple_app` (1).

### B.2 High-use classes still pending (production node statements)
| class | prod | status | note |
|---|---:|---|---|
| packages_base | 59 | PENDING | node_base + meaningful_desktop |
| firewall_secure | 59 | PENDING | node_base else-branch + meaningful_desktop |
| extra_packages_el | 59* | BLOCKED cat 5 | *RedHat-only branch; real count = number of RHEL servers (unverified; 8 node files mention rhel) |
| node_base | 58 | PENDING | the composite itself; deps unmet until the rows above are done |
| filesystem_apt | 58 | PENDING, drifted vs 0.9.8 | non-RedHat branch |
| firewall_secure_extra | 58* | PENDING | *only if `$firewall_secure_extra` |
| puppet_boot_run | 58* | PENDING, drifted | *only if `$run_puppet_on_boot` |
| sysmon_base | 58 | PENDING | monitoring triggers the fleet's agent runs (CTO doc) |
| ssl_base | 38 | PENDING | baseline-synced 2026-10-01, gates 3 wrappers |
| ssl_nginx_domain | 37 | PENDING | |
| nginx_frontend_domain | 35 | PENDING | 714 lines, cx 10 |
| nginx_base | 33 | PENDING | |
| nginx_frontend | 24 | PENDING | |

### B.3 Unused (zero declarations in node files) — candidates for a CTO decision not to migrate
33 classes have zero declarations anywhere (including deleted/ and tests/): firewall (the non-secure base; production uses firewall_secure), firewall_addon_hosting (blocked cat 3), firewall_addon_xrdp, firewall_ipv6_drop_policy, letsencrypt_certificate†, linux_policies_common, linux_policies_user, mount_shares_desktop (blocked), network_static, nginx_frontend_mail, nginx_proxy_smtp_auth_ppa, nginx_static, node_base_desktop, node_base_domain_desktop, openvpn_domain, openvpn_nm_connection (blocked), openvpn_set_vpn_passwd_file, postfix_smtp_base, postfix_smtp_base_config_file, sftp_only†, ssl_nginx, ssl_postfix, sysmon_fs_health, sysmon_integrity_master, sysmon_integrity_node, sysmon_mysqldump_health, sysmon_puppet_cert_status, user_desktop, user_desktop_sudoer, user_lock†, user_samba† (blocked), user_sysmon† (blocked), users_sudoers†. `hello_world_flask*` appear only in `tests/`.
† = user/identity/secret-bearing defines that are declared from the confidential `passwd_*` layer (188 references from node files) — **these are under-counted, not unused**. The engine already spent 4 of its 7 blocks (user_samba, user_sysmon, mount_shares_desktop, openvpn_nm_connection) and 4 of 31 greens (firewall_addon_xrdp, firewall_ipv6_drop_policy, network_static, openvpn_set_vpn_passwd_file, sftp_only) on classes with no node-file usage; the plan orders by complexity, not by fleet impact.

### B.4 Company layer → puppet_infrastructure (what `meaningful_puppet` breaks on)
| company class | nodes | puppet_infrastructure closure |
|---|---:|---|
| adam_nginx | 12 | nginx_base, nginx_frontend, nginx_default_removal, ssl_nginx_domain, nginx_frontend_domain, ssl_base |
| vtlsuite_nginx / vtlsuite_nginx2 | 8 / 8 | nginx_base, nginx_frontend_domain, ssl_nginx_domain, nginx_default_removal, ssl_base |
| md_simple_app | 1 | nginx_frontend closure (5) |
| meaningful_desktop | 1 (≈20 laptops) | the 10 classes listed in B.1 incl. 2 missing locally |
| postgresql_server / postgresql_db / postgresql_backup | 6 / 2 / 3 | none from puppet_infrastructure; uses `puppetlabs-postgresql` directly (postgresql::globals, ::server, ::server::role/db/grant/pg_hba_rule) |
| docker_prune (18), docker_gitlab_* (1+1), gitlab_backup_verify, log_scanner, webfilter_master, vtlsuite_docker/2 (3+3), disable_usb_storage, docker_dev_script | — | none |
Implication: the company layer's exposure to this migration is exactly the nginx/ssl stack (7 classes) and the desktop closure (10 classes). Everything else in `meaningful_puppet` depends on community modules (postgresql, docker, gitlab_registry) whose Puppet 8 compatibility is outside the 87 but inside the production upgrade.

---

## C. Throughput

Data: `metrics.csv` (114 rows: every commit classified as GREEN / BLOCKED / BASELINE_SYNC / PLAN_FIX / RECORD / TOOLING / BOOKKEEPING, joined to Codex logs, advisor notes and agent reports). Raw sources: 108 commits; 10 Codex run logs (2026-09-30 → 10-05; the logs directory did not exist before 2026-09-30); 7 advisor hazard notes; 121 agent reports on the master (2026-01-12 → 10-05).

### C.1 What a class costs today (engine era, 8 GREEN classes with full logs)
| class | Codex wall | tokens | exec cmds | harness runs in Codex | reverts in Codex | advisor note → Codex start | notes |
|---|---:|---:|---:|---:|---:|---:|---|
| network_static | 224 s | 71,129 | 56 | 1 | 1 | 58 s | reviewer FAIL (header lacked deps) → `codex exec` fix hung 47 min → 1e846b7 |
| filesystem_base_desktop | 269 s | 65,487 | 31 | 2 | 3 | 58 s | |
| filesystem_base | 985 s | 91,051 | 30 | 2 | 2 | 56 s | revert failed once ("Node did not become reachable by SSH within 120s", log:…13652.log:1958); Codex debugged VBox networking (~12 min) |
| puppet_commush | 281 s | 52,423 | 24 | 2 | 2 | 62 s | |
| hello_world_flask_common | 261 s | 77,145 | 27 | 1 | 4 | 6 s | |
| user_kde_lock_screen_common | 287 s | 61,400 | 18 | 1 | 1 | — | baseline-sync of a shared file first (dd3e1dc) |
| backup | 326 s | 84,658 | 49 | 3 | 3 | 49 s | first harness run died: params JSON missing (log:…08882.log:112) |
| puppet_backup | 199 s | 48,868 | 21 | 1 | 1 | 50 s | |
| **median** | **275 s** | **68 k** | 29 | | | | **all 8 were "validated unchanged": the committed diff is a 1–2 line header** |

Wall-clock per class including the advisor and the reviewer (from commit gaps): the 2026-10-05 batch did 3 classes in 19.5 min (14:52:46 → 15:12:56) = **6.5 min/class**; the 2026-10-01 batch did 5 greens + 2 pre-Codex blocks + 1 reviewer fix in 109 min including a 47-min hang = **12 min per green excluding the hang**. The reviewer's re-harness is visible in the reports as a run 1–3 min after each Codex log ends (e.g. report 2026-10-01T00:12:31Z/00:14:36Z after the filesystem_base_desktop log ended 00:11:46Z).

Where the time goes inside a median run (from the command sequences in the logs): roughly 60–80% of the 20–56 commands are orientation reads — searching for `AGENTS.md` in 4–6 paths (none exists), `cat`/`sed` of `test_class.sh`, `revert_node.sh`, `migration_plan.md`, `UPSTREAM_BASELINE.md`, `DESIGN_DECISIONS.md`, the tracker, the order file, upstream `git show`, and in one case Codex's own live log (`log:backup…:1158` — the log then contains itself, doubling its size). The actual work (harness, revert, header edit, tracker edit, 2 commits, regen) is 8–12 commands. The wrapper gives Codex no orientation, so it rebuilds it from disk every run at ~50–90 k tokens.

### C.2 Failure modes observed
- **Compile failure (Error 500)**: 37 of 121 agent runs (31%) — every iteration on a broken manifest costs one. Cheap individually (median agent run 3.7 s; catalogs are tiny, median 9 resources) but each costs a Codex think–edit–rerun loop.
- **Apply failure on undeclared prerequisite**: 5 runs (`Cannot create /opt/puppet-infrastructure/bin`, `Could not set 'file' on ensure: No such file or directory`) — the hazard-4 class of problem, which produced the `required_base` capability and 11 `plan(...)` commits.
- **Environment-mismatch**: `pdbedit` missing (user_samba), `/etc/network/interfaces` missing (network_dhcp, ifupdown absent on netplan node).
- **Harness pre-flight death**: params JSON missing for a define (`backup`) — twice in one run because Codex re-ran before writing the file.
- **Infrastructure**: revert timeout (node SSH not back in 120 s) once in 8 runs; master `Error 500` from `Could not retrieve information from environment production` once (2026-03-31) — the r10k purge of `puppet_infrastructure` described in the runbook.
- **Hang**: `codex exec` with an open stdin idled 47 min (2026-10-01, DESIGN_DECISIONS); fixed by `</dev/null` in the wrapper (4cb52b3) but the rule for ad-hoc calls is prose only.
- **Retries/reverts**: Codex ran `revert_node.sh` 1–4 times per class (17 reverts for 8 greens) and the harness 1–3 times; the wrapper's "First action: run the harness" fires before any revert, so run 1 of every class executes on whatever state the previous class left (reports show first-runs as `unchanged` where a fresh node would have shown creations; e.g. 2026-10-05T13:54:22Z).

### C.3 History before the engine era (git only)
- 2026-02-17 → 04-29: 15 classes in 3 working days by a human + Codex (inter-commit gaps 4–50 min).
- 2026-07-01, 07-26/27/29, 09-01: tooling-building sessions; 9 greens, 11 blocks, 1 revert, 2 reblocks/unblocks; ~70 commits of state/tooling for 9 class migrations.
- 2026-09-30 → 10-05: the engine (CLAUDE.md + skill + reviewer, 60f796b) ran two sessions: 8 greens, 2 pre-Codex blocks (later unblocked by ruling), 1 reviewer FAIL/fix, 3 baseline-syncs, 6 plan fixes, 3 tooling commits.
- Net: 31 greens in ~9 working days spread over 8 months; **zero** classes with complexity ≥ 6 are done (the done set's max complexity is 5; the pending set's median is 5 and 19 classes are ≥ 7).

### C.4 What the data cannot tell you, and the missing instrumentation
- Codex logs have **no timestamps** (plain `codex exec` output). Decomposition inside a run (revert vs harness vs thinking) is impossible; only start (filename epoch) and end (mtime) are known.
- Reviewer duration and verdicts are **not recorded** anywhere; "PASS" in metrics.csv is inferred from the absence of a corrective commit.
- The master's store reports are named `YYYYMMDDHHMM.yaml` by completion minute, so the harness's two back-to-back runs usually **collapse into one file** (e.g. 13:54 and 13:56 files for one harness invocation on 2026-10-05); report counts are lower bounds. No PuppetDB, no report processor.
- Revert duration is not logged (nominal ~2 min: ACPI poweroff wait + restore + boot + Wi-Fi bridge settle).
- Advisor and reviewer token/time costs (Claude side) are not recorded at all; Codex tokens are (`tokens used` footer).
- Human wait time between sessions (days to weeks) dominates calendar throughput and is invisible.
Minimum instrumentation: `codex exec --json` or `ts`-stamped logs, a per-run JSON record written by the skill (class, attempt, start/end, revert_s, codex_s, harness_runs, reviewer_s, verdict, tokens), persisted reviewer verdicts, and reports keyed by `configuration_version`/`transaction_uuid` rather than minute.

---

## D. Verification quality

### D.1 What GREEN proves today
The harness (`test_class.sh`) proves four things and nothing else:
1. The catalog for `puppet8node` compiles on OpenVox server 8.11 with the target class, its declared `required_base`/`required_external`, **and `passwd_common`** (the master's node file includes it outside the managed block).
2. Run 1 exits 0 or 2 (`test_class.sh:361`).
3. Run 2 exits 0 or 2 (rc 2 = "changes applied" is accepted).
4. Run 2's stdout matches none of `Notice: .*changed | Notice: .*created | Notice: .*defined content as | Info: .*Scheduling refresh of` (`test_class.sh:403`).

It does **not** prove: that the class does what upstream intends; that any branch other than the one the single params fixture selects compiles; that the class composes with the other classes production declares beside it; that runtime effects happened (services listening, rules effective, files consumed); or that the node was clean at run 1 (G #7).

### D.2 By class category: where an idempotent-but-wrong migration passes
| Category (examples) | GREEN is strong evidence of | Passes GREEN while wrong when… | Concrete instance |
|---|---|---|---|
| File/script deployment (filesystem_*, puppet_commush, backup*, sysmon_* checks, user_kde_lock_screen_common) | files exist with expected mode/owner/content | a template renders a **legacy fact as empty** (Puppet 8 `include_legacy_facts=false`): ERB `@hostname`, `@osfamily`, `$::fqdn` become empty strings, the file is still written, and run 2 is clean | `templates/openvpn/smb.conf.erb:5` uses `@hostname` (openvpn_domain, pending) — would render an empty NetBIOS name and still be GREEN; postfix_smtp_node templates carry legacy facts too (cluster audit) |
| Config consumed by a service (ssh_secure, rsyslog_*, nginx_*, postfix_*, caching_nameserver) | config file content | the service rejects or ignores the config (no validation, no restart check); a service restart failure surfaces only if Puppet manages the service | ssh_secure is GREEN; nothing asserts `sshd -t` or that the harness's own SSH still authenticates with the new settings |
| Firewall rules (firewall*, addons) | rules present in iptables | rule semantics change across puppetlabs-firewall 8 (`action`→`jump`, `provider`→`protocol`), rule order/chain wrong, or policy changes that only matter for traffic the harness never sends | historical `firewall` migration also removed the 0.9.8 resource default `Firewall { require => undef }` (diff vs release-0.9.8) — a dependency-graph change no test observes |
| Execs (openvpn_domain join, user_samba, mysql_server, letsencrypt_base, hashman) | exec did not fail | an exec with a weak guard **runs every time**: its notice is `executed successfully`, which the regex does not match (G #4) | none yet observed (`executed successfully` appears in 0 of 10 logs); openvpn_domain's `id user@DOMAIN` guard is a known non-idempotency risk once a DC exists (cluster audit) |
| Interface/network config (network_dhcp, network_static) | files written | the files are for a stack the node does not run | network_static writes ifupdown config on a netplan-only node; `ifupdown` is not installed, so the config is never applied (`network_static.advisor.log`) — GREEN validated a no-op |
| Defines with one fixture (backup, docker_container, sync, users) | the fixture's branch | other branches never compile | docker_container's registry-login, digest and named-volume branches (lines 58–79) never executed (cluster audit) |
| Classes needing master-side context (ssl_base `puppet:///extra_files`, hashman Hiera, postfix_smtp_node Hiera) | — | they cannot go GREEN without lab-master changes; risk is Codex "fixing" by changing source paths | pending; flagged by cluster audits |

### D.3 Reviewer audit
**What it checks** (`.claude/agents/reviewer.md:11-28`): git state; commit scope; manifest diff vs `origin/release-0.9.8` judged syntax-only; tracker/order/header records; a fresh harness run; fixture names.

**What it caught.** One FAIL is recorded in git: network_static's header lacked module dependencies → advisor-issued `codex exec` fix 1e846b7 (`P8: record module dependencies…`). Every other reviewer verdict is unrecorded (A.2 #12); no corrective commits follow the other 7 engine-era greens, so they are inferred PASS.

**What it missed or could not apply.**
- Four forward migrations violate the header rule and carry `[from: release-0.9.8]`: `docker_container` and `sftp_only` have **no header at all** (diff vs 0.9.8 = 0 lines), `ssh_secure` has no header (its only change is `$::osfamily` → `$facts['os']['family']`, a correct syntax fix), and `network_dhcp`'s header omits its module dependencies (puppet-network 2.2.1, filemapper 4.0.0, kmod 4.1.0), which DESIGN_DECISIONS 2026-10-01 already noted. All four predate the reviewer (60f796b, 2026-09-30 23:49), so they were never reviewed; nothing re-reviews them. I could not determine which two cases the brief's "two missed annotation cases" refers to; these four are what the tree shows today.
- Historical reimplementation shapes in plain-`Done` classes, invisible to a reviewer that only runs on new migrations: `rsyslog_base` replaced 0.9.8's `ssldir_override` parameter + hardcoded path with `$settings::ssldir` (evaluated on the **master**, used as an agent-local `file://` source — correct only while both share `/etc/puppetlabs/puppet/ssl`); `firewall` dropped `Firewall { require => undef }` and added inline `/opt/puppet-infrastructure{,/bin}` directories that duplicate `filesystem_base.pp:21` with a different mode (composition-time duplicate declaration); `sysmon_puppet_cert_status` is not composable with `filesystem_base` (duplicate File declarations, cluster audit); `backup_rsnapshot` reformatted its parameter list. These are reconciliation-pass items, but nothing tracks them.
- Further defects found by the independent edit audit (three agents re-diffed all 31 done classes against `release-0.9.8`):
  - **`filesystem_yum` carries false provenance.** It is stamped `Done filesystem_yum [from: release-0.9.8]` (`migrated_classes.txt:13`, fix commit 0394854), but its code adds `file { $localdir }` and `file { "${localdir}/bin" }` (`manifests/filesystem_yum.pp:10-23`). Those resources are absent from 0.9.8 and duplicate `filesystem_base.pp:18-21` with a different mode (`0755` vs `0644`). `node_base.pp:105,110-111` declares both on RedHat, so **node_base on a RHEL server would fail to compile with a duplicate declaration**. The marker was assigned by date, not by content diff.
  - **`sysmon_puppet_cert_status` is a reimplementation, not a migration.** It replaced the dependency on puppetlabs-apt's `Exec['apt_update']` with its own guarded `exec { 'sysmon_puppet_cert_status_apt_update': command => '/usr/bin/apt-get update', unless => …find /var/lib/apt/lists -mtime -1… }` (`manifests/sysmon_puppet_cert_status.pp:14-23`), plus the same inline directories. Production behaviour changes (an extra apt-get update path), and it does not compose with filesystem_base.
  - **The `network_dhcp` migrate commit 0ecf985 also unblocked other classes and deleted a candidate.** It removed 4 lines from blocked.txt for network_static, openvpn_server and network_vpn, and deleted `candidates/network_dhcp.reimplemented.pp` (`git show --stat 0ecf985`). The reviewer's scope check would fail this; it was committed 21 minutes before the reviewer existed.
  - **Two `P8: migrate` commits change no manifest** (docker_container ca30e2a, sftp_only 76286a4: `.codex_state/*` only). The message claims a migration that the manifest gives no evidence of.
  - **A header names a module that does not exist under that name.** `dns_client.pp:2` says `puppet-resolv_conf`; the class comes from `saz-resolv_conf` 8.0.1. No historical header carries a module version.
  - **`filesystem_sec`'s header documents a branch the code cannot execute.** The header says the default group falls back to wheel/sudo by OS; the code reassigns a parameter variable, which is a compile error on Puppet ≥4. The fixture passes `restricted_group`, so the default branch was never compiled (`filesystem_sec.pp:1-27`).
  - **An untracked params fixture names the node's real NIC.** `puppet_infrastructure::firewall_addon_caching_nameserver.json` contains `enp0s3` (grep, filename only), against the CLAUDE.md fixture rule (`p8test0`). It is harmless for a DNS accept rule, but the reviewer's fixture check only looks at classes it reviews.
  - **`rsyslog_client`'s 68-line delta is baseline drift, not Codex work.** For example, `String $target_ip` is mandatory locally but Optional in 0.9.8. The two-diff method (pre-migrate vs 0.9.8, then the migrate commit itself) separates drift from edits; the reviewer uses one diff.
  - **Body comments and upstream warnings were deleted** in header rewrites (firewall_addon_xrdp lost a 14-line rationale for its ESTABLISHED/5900 rule; the ipv6 classes lost their "add-on to firewall_secure" warning).

**Structural blind spots** (why a wrong migration can pass both gates):
1. *Same node, already converged.* The reviewer's harness run is runs 3–4 on the node Codex left; it proves stability, not first-apply correctness. It does not revert first (the reviewer has no revert step).
2. *Manifest-only diff.* Templates and files are in scope only "if genuinely needed"; a template change (or a template that silently depends on a legacy fact) is not diffed against 0.9.8.
3. *Fixtures are Codex-authored.* Params JSON is written by Codex and lives untracked; the reviewer reads the same file to judge fixtures, so a fixture that steers the class away from its risky branch passes.
4. *No coverage signal.* Neither gate checks that the catalog contains the class's resources (count or titles). A class whose body is skipped by a conditional applies "cleanly".
5. *No behaviour evidence.* By design for Phase 1, but it means 100% of the Phase-3 question is open for all 31 greens.
6. *Outputs not persisted.* A reviewer PASS cannot be audited later.
7. *No composition compile.* Each class is compiled alone (plus its declared base). Duplicate declarations between a leaf and a base (filesystem_yum, firewall, sysmon_puppet_cert_status vs filesystem_base) are invisible until node_base is compiled. A compile-only check of every class together with its `internal_deps`, and of each production composite (node_base on Debian and RedHat facts, meaningful_desktop), would catch them in seconds.
8. *Default branches unexercised.* Fixtures choose non-default values (filesystem_sec, docker_container), so a default path that cannot compile is never seen. Compiling with default parameters, plus one fixture per branch, closes this.
9. *Exit-code blindness.* Run 2 with rc 2 passes (G #4). `puppet agent -t` already returns detailed exit codes; requiring rc 0 on run 2 is a one-line fix that also catches `executed successfully` and `removed`.

### D.4 Codex edit quality (from git)
- **Good, forward era (2026-09-30 →):** 8 of 8 greens are verbatim 0.9.8 manifests plus a 1–2 line header; scope stays to manifest + tracker; commit messages follow convention; Codex refused to reimplement (user_samba, user_sysmon blocks carry exact error text, traced chains and unblock conditions — `blocked.txt:8,11`); it caught the unsafe real-account params override in mount_shares_desktop and corrected it itself (`blocked.txt:9`).
- **Good, historical era:** correct Puppet 8 syntax fixes (`action`→`jump`, legacy facts → `$facts[...]`).
- **Bad / risky:** (a) header **rewrites** that replace the upstream `### Purpose` block with pseudo-puppet-strings prose, often with whole-file re-indentation, in 15 classes (historical plus four July-era forward ones; e.g. openvpn_set_vpn_passwd_file 55 changed lines, firewall_addon_xrdp 47, filesystem_yum 41). This noise masks real changes in review and breaks "syntax only". The 2-line header convention adopted on 2026-10-01 is the good counter-pattern; (b) the one-off reimplementation of network_dhcp (48fc434, reverted 03cb002); (c) logic changes in historical classes (D.3); (d) headers that claim "Module dependencies: none (uses Puppet built-in … lookup())" are accurate for those classes, but `backup`/`puppet_backup` claim "puppetlabs-cron_core 1.3.0 (vendored)" — correct but a pattern the reviewer cannot verify mechanically; (e) heavy re-orientation per run (C.1).
- **Division-of-labour implication:** for the 8 "validated unchanged" classes the Codex contribution was a header line and a tracker line at ~68 k tokens and ~4.6 min each; the judgement that mattered (hazards, required_base, baseline-sync) was the advisor's, made before Codex started. See F.8.

---

## E. Blocked and hard classes

Sources: 11 read-only cluster audits (one agent per cluster, re-verified where stated). Every manifest was diffed against `release-0.9.8` and `release-0.9.10`. Each claim below carries the file:line the audit cited. Items marked *predicted* come from reading module type definitions and Puppet source; no catalog was compiled.

### E.0 The next class in the queue is predicted RED
`puppet_boot_run` heads the order file (`migration_order.md:75`). It is drifted vs 0.9.8, and the 0.9.8 version (upstream 4ae2e35) adds `ensure => running` to a `Type=oneshot` unit with no `RemainAfterExit` (`templates/etc/puppet_boot_run.service.erb:6-8`). The unit is inactive after each start, so every run reports `ensure changed stopped to running` and the harness regex fails run 2. Fixing it means `RemainAfterExit=yes` or dropping `ensure`, which is a behaviour change, so this is Salatiel-tier. **Write the escalation before the next `/migrate-next`, or the loop will spend a Codex run discovering it.**

### E.1 Blocked classes (`blocked.txt`)
| class | cat | real unblock path (today's evidence) | behaviour check that proves it works | prod use |
|---|---|---|---|---|
| firewall_addon_openvpn_server | 1 | Module ruling on `sysctl`. Option one: thias-sysctl 1.0.8 is still on the Forge (puppet <9, so it installs; OS list ends at old Ubuntu; open Puppet 8 issue #80). Option two: augeasproviders_sysctl 4.1.0 (same call shape, but persists to `/etc/sysctl.conf`, not `/etc/sysctl.d/<key>.conf`, a behaviour delta to rule on). Then 3 `action`→`jump` edits (`:17-19`). The blocked.txt text is stale (A.2 #5). | `sysctl net.ipv4.ip_forward` = 1 after reboot; `iptables -t nat -S POSTROUTING` shows MASQUERADE on wan_iface; a client behind br0 reaches an outside address (2 nodes) | 3 |
| firewall_addon_hosting | 3 | Production info: does any hosting node run agent-mode? If masterless, the class is correct and untestable in agent/master. If not, upstream bug. A harness alternative is `puppet apply` on the node from a staged module copy, which removes the 8140 dependency. | OUTPUT policy DROP; DNS (udp/53), NTP (udp/123) and established traffic still pass; any other new outbound (e.g. `curl` to 443) is refused | 0 |
| extra_packages_el | 5 | RHEL-family node plus harness node selection (`test_class.sh:29`). Rocky/Alma lack `subscription-manager`, so the CRB exec's guard inverts there too; only real RHEL (developer subscription) runs this class faithfully. | `dnf repolist` shows epel and codeready-builder enabled; listed packages installed | RedHat servers only (count unverified) |
| user_sysmon | 1 | Replace leinaddm-htpasswd 0.0.3 (`Puppet.newtype`, Puppet 3 API). Candidates need a module ruling (behaviour-change tier if semantics differ); alternatively patch/fork the two types. Also needs a Naemon/Thruk server context (`/etc/thruk`, `/etc/naemon/conf.d/contacts`, `naemon` user), i.e. the monitoring server. | `htpasswd -v /etc/thruk/htpasswd p8testuser` succeeds with the fixture password; Naemon contact file parses (`naemon -v`) | via the passwd layer (unread) |
| mount_shares_desktop | 3 | Desktop fixture: a baseline where `/home/<user>/Desktop` exists (Kubuntu/Ubuntu desktop VM, both exist powered off), or a harness "fixture state" capability. Behaviour also needs an SMB server. | the deployed mount script mounts a test share from a second host; unmount script cleans up | 0 in node files (likely passwd layer) |
| openvpn_nm_connection | 1→upstream bug | DESIGN_DECISIONS 2026-09-30 already **confirmed** `fqdn_rand_uuid` is defined nowhere on production. blocked.txt still says "settle by inspecting". Needs a Salatiel/Gustavo ruling to correct it to `fqdn_uuid` (stdlib) as an authorized bug fix. Needs a NetworkManager desktop node for behaviour. | `nmcli connection show` lists the connection with a stable UUID across runs; `nmcli con up` reaches the test VPN server | 0 |
| user_samba | 5 | Samba DC. A plain `samba-tool domain provision` DC satisfies `pdbedit`/`ldbsearch`/`sam.ldb`, but **not** `create-user.pl`, which uses Zentyal's EBox Perl API (`templates/samba/create-user.pl.erb:8-9,33`). Faithful = a Zentyal VM. The helper scripts are deployed by nothing in-tree (production inspection item). | `samba-tool user show p8testuser`; `ldbsearch ... unicodePwd` matches the fixture hash; second run no-op | likely passwd layer |

### E.2 Hard pending classes — Phase-1 blocker, capability, behaviour proof
| class (prod) | Phase-1 blocker found | capability that unblocks it | behaviour check |
|---|---|---|---|
| **node_base (58)** | `Could not find class ::ntp` (`node_base.pp:159`): no ntp module on the lab; production's ntp module identity unread. Composite of 10 pending/done classes; all components must be done first. | Forge pin (puppetlabs-ntp 11.x, after reading production's version) + ordering | all component checks + `timedatectl`/`ntpq -p` |
| **packages_base (59)** | Compiles with apt 11.3.2, but `Exec[apt_update]` **runs every run** and prints only `executed successfully`. The harness regex does not match it, so GREEN is reachable while non-idempotent. | Harness exec-idempotency gate (G #4); fixture for both `unattended_upgrades` values | `dpkg -l` for the package list; second run reports 0 events |
| **firewall_secure (59)** / **firewall_secure_extra (58)** | 11 / 45 `action =>` (no such attribute in firewall 8.3.0). *Predicted* Resource-API type errors: `rseconds => '60'`, `rhitcount => '15'`, `connlimit_above` from a `String` parameter, all typed Integer in 8.3.0. Hazard 4: required_base=filesystem_base missing. secure_extra also needs xtables-addons/geoip and a second host behind `forward_iniface`. The class rate-limits SSH, which can throttle the harness's own SSH (needs ControlMaster). | Plan fix + Codex syntax loop + SSH ControlMaster in the harness; second host for behaviour | `iptables-save` normalized diff against expected; SSH from a whitelisted vs a non-whitelisted host; ICMP; rate-limit hit test |
| **sysmon_base (58)** | Plan gap: needs required_base=filesystem_base,packages_base,filesystem_lib64. packages_base must be done first. No exec; manifests identical to 0.9.8. | Plan fix + ordering | run each deployed check script; exit codes 0–3 with parseable output |
| **filesystem_apt (58)** | Drifted: 0.9.8 adds rsyslog packages; `files/apt/apt-update-kernel.sh` fully rewritten upstream (local greps `/boot/grub/menu.lst`, absent on node). | Baseline-sync (advisor) + required_base | run scripts with `--dry-run` equivalents; cron entries present |
| **ssl_base (38)** → ssl_nginx, ssl_nginx_domain (37), ssl_postfix | Code is Puppet-8 clean. Sources `puppet:///extra_files/ssl/*`, but the lab master has no `extra_files` mount, so apply fails (*predicted*). | Master fileserver mount + self-signed p8test PKI (never production certs); Salatiel-approved lab-master change | `openssl x509 -noout -subject -enddate` on deployed files; key/cert modulus match; perms/owner; notified service reloaded |
| **nginx_base (33)**, nginx_frontend_domain (35), nginx_frontend (24), nginx_static_domain | puppet-nginx not installed; recommended pin 8.4.0 (openvox ≥8.19; every parameter used was checked against 8.x). Needs required_external=apt (`Exec['apt_update']`). **One real Puppet-8 break: `nginx_frontend_domain.pp:247 port => $element_split[1] + 0`**: string→number coercion is an error under `strict=error` (Puppet 8 default). Fix is `Integer($element_split[1])`; it propagates to frontend and frontend_mail. Also needs the extra_files cert fixture. | Forge pin + plan fix + Codex syntax fix + master fixture | HTTP/TLS probes per vhost (status, redirects, HSTS, upstream pass-through to a fixture backend on 127.0.0.1:8080, cert served), `nginx -t` |
| letsencrypt_base / letsencrypt_certificate | Drifted (lacks 0.9.8's `hetzner-cloud` provider and pip pins). puppet-letsencrypt 13.4.0 + its hard dep puppet-epel. Ubuntu 24.04 PEP 668 blocks the pip branch (upstream issue). The certificate needs a real ACME flow. | Baseline-sync; Forge pins; ACME sandbox (Pebble or a Let's Encrypt staging + sandbox DNS zone); production info on the provider used | `certbot certificates`; cert chain issued by the staging CA; renewal hook dry-run |
| mysql_server (1) | puppetlabs-mysql absent; production 10.5 cannot run on Puppet 8. Candidate 17.x (Forge audit). Ubuntu-only package names without OS guard. Upstream has an unmerged rewrite (H4). | Forge pin; params fixture; decide 0.9.8 vs the unmerged rewrite (CTO) | `mysql -e 'SELECT 1'` over TLS as the rw user; grants as declared; self-signed cert deployed |
| openvpn_server (3) / network_vpn (3) | puppet-openvpn 12.0.0 (first Puppet-8 line is 11.x) **plus two upstream defects that no module fixes**: `notify => Service['openvpn']` (`:208`) references a resource the module declares only on non-systemd hosts (compile error), and `service { 'openvpn-server@puppet_infrastructure' }` (`:117`) duplicates the module's own title on Debian-family. Undeclared `Network_config[$local_interface]` subscription. sysctl ruling. Bridge `br0` with `lo:0` as port. | Upstream-bug ruling (escalation), Forge pins, second NIC on the node VM, test PKI, second VM as client | client VM connects (tap), gets a pool address, pings br0 and a LAN host; PAM password auth works; wrong password rejected |
| openvpn_domain (0) | **Legacy fact in a template**: `templates/openvpn/smb.conf.erb:5` uses `@hostname`, which renders empty under Puppet 8. Silent, still GREEN (D.2). `id user@DOMAIN` guard can rerun forever. Needs a DC to go GREEN at all. | Legacy-facts rule (hazard addition) + Samba DC | `net ads testjoin`; `wbinfo -u`; `getent passwd user@DOMAIN` |
| hashman_base / hashman_web (1) | Gated by the nginx stack and Hiera keys; needs an MTA for mail flows; Flask/gunicorn on the master role. | nginx stack, Hiera fixture, local MTA (postfix_smtp_* pending) | headless browser: load login page, submit a password change for a fixture user, verify the `.pp` record written and the mail captured |
| rsyslog_server (1) | Baseline-synced to 0.9.8, but production 0.9.10 changed it again (+64 lines, retention script, logrotate timer). The plan's "external rsyslog module" column is a **false lead**: no `rsyslog::` token exists in any version since 0.9.8. | CTO ruling: migrate 0.9.8 now or catch up to 0.9.10 first; second node for TLS forwarding | client → server over TLS 6514: a `logger` line on the client appears in the server's per-host file; cert verification on |
| postfix_smtp_node (3) / postfix_smtp_base | Hiera fixture keys on the master; legacy facts in templates; extra_files certs; second node for relay. | Hiera fixture + legacy-facts rule + PKI + second node | `postfix check`; `swaks` relays via the base server with SASL; message delivered to a fixture mailbox |
| user_base and the user* family (passwd layer) | Code clean (`fqdn_rand_string`, ecryptfs). Fixture `p8testuser` must be created by user_base first (2026-10-05 entry). Drift: user_kde_lock_screen, user_desktop, user_desktop_sudoer (param renames) must be synced in order. | Baseline-sync order + plan fixes | `getent passwd p8testuser`; `su - p8testuser -c true` with the fixture password; `sudo -l -U p8testuser`; SSH key login |
| node_base_desktop / node_base_domain_desktop (0) | Unused in production (B.3). Syncing node_base_desktop requires the 3 missing classes. | CTO decision to retire or keep | — |
| nginx_proxy_smtp_auth_ppa (0) | PPA publishes focal only; template hardcodes kinetic/20.04; the feature is stock nginx since 1.19. Unused. | CTO decision to retire | — |

### E.3 Capabilities grouped, with class counts
| # | capability | classes it unblocks (Phase 1 / Phase 3) | tier | cost |
|---|---|---|---|---|
| C1 | **Plan fixes** (required_base / required_external) found by the audits | sysmon_base, sysmon_fs_health, sysmon_integrity_master, sysmon_integrity_node, sysmon_mysqldump_health, sysmon_backup, sync, mysql_server, filesystem_apt, puppet_boot_run, hello_world_flask, firewall_secure, firewall_secure_extra, hashman_base, user_lock, linux_policies_common, linux_policies_user, letsencrypt_base, letsencrypt_certificate, nginx_base, nginx_proxy_smtp_auth_ppa, user_desktop, user_desktop_sudoer — **23 / –** | advisor | 1 h total |
| C2 | **Forge pins** with the module rules (puppet-nginx 8.4.0, puppet-letsencrypt 13.4.0 + puppet-epel, puppetlabs-mysql, puppet-openvpn 12.0.0, an ntp module, sysctl ruling) | nginx ×6, hashman_web, ssl_nginx, ssl_nginx_domain, letsencrypt ×2, mysql_server, sysmon_mysqldump_health, openvpn_server, network_vpn, firewall_addon_openvpn_server, node_base, node_base_domain_desktop — **17 / 17** | advisor (+ Salatiel for sysctl/htpasswd) | 3–5 h |
| C3 | **Baseline-sync / import** | filesystem_apt, puppet_boot_run, letsencrypt_base, user_kde_lock_screen, user_desktop, user_desktop_sudoer (advisor); node_base_desktop + import of gnome_lock_screen, firewall_ipv6_drop_policy_desktop, rsyslog_apparmor_exception (escalation) — **10 / –** | advisor / Salatiel | 2 h + ruling |
| C4 | **Master fixture state**: `extra_files` fileserver mount + throwaway PKI; Hiera fixture keys | ssl_base, ssl_nginx, ssl_nginx_domain, ssl_postfix, postfix_smtp_base, postfix_smtp_node, nginx_frontend, nginx_frontend_domain, nginx_frontend_mail, nginx_static, nginx_static_domain, openvpn_server, hashman_base, hashman_web, user_lock, sysmon_backup — **16 / 16** | Salatiel (lab master change) | 3 h |
| C5 | **Upstream-bug rulings** (authorized bug fixes) | openvpn_nm_connection (`fqdn_rand_uuid`), openvpn_server ×2 defects (+network_vpn), puppet_boot_run (oneshot), plus whether `nginx_frontend_domain:247` counts as syntax (likely yes) — **5 / 5** | Salatiel / Gustavo | ruling only |
| C6 | **Harness correctness** (exec-run detection, rc=2 on run 2, revert-first, coverage signal, timeouts, multi-fixture variants) | packages_base, openvpn_domain, every exec-bearing class (13 pending) — **protects all** | advisor-built, Salatiel-approved | 4–6 h |
| C7 | **Second Ubuntu node** (client/server pairs) | rsyslog_server/client, postfix ×3, sync, backup_rsnapshot (remote), openvpn_server/network_vpn client, nginx_frontend_mail backend, firewall behaviour probes, mount_shares (SMB server), sftp_only — **0 / ~14** | Salatiel | 3–6 h (see F) |
| C8 | **Second NIC on the node VM** (host-only) | openvpn_server, network_vpn, network_dhcp, network_static — **2 / 4** | Salatiel | 1 h |
| C9 | **Desktop node** (Kubuntu, plus GNOME for gnome_lock_screen) | user_kde_lock_screen, user_desktop, user_desktop_sudoer, mount_shares_desktop, linux_policies_common, linux_policies_user, gnome_lock_screen, openvpn_nm_connection, meaningful_desktop closure — **2 / 9** | Salatiel | 3–5 h (VMs exist) |
| C10 | **RHEL-family node + node selection** | extra_packages_el (P1); RedHat branches of packages_base, node_base, filesystem_yum, filesystem_base, filesystem_sec, ssh_secure, sysmon_base, hello_world_flask — **1 / 9** | Salatiel (VM), advisor (harness) | 4–8 h |
| C11 | **Samba DC** (plain samba-tool) / **Zentyal VM** (faithful) | openvpn_domain / user_samba — **2 / 2** | Salatiel | 3 h / 6–8 h |
| C12 | **Behaviour-check framework** (F.5) | all 31 done + every future green — **0 / 87** | advisor-built | 8–12 h + ~0.5 h per class |
| C13 | **Production information trip** (read-only on the production master) | firewall_addon_hosting (masterless?), ntp module identity, nginx_base params, sysmon check account, user_samba helper scripts, RHEL node count, sysctl/htpasswd/fqdn evidence refresh — **~8** | Salatiel | 1–2 h |
| C14 | **Retire/park decisions** | nginx_proxy_smtp_auth_ppa, node_base_desktop, node_base_domain_desktop, and the 33 zero-declaration classes reviewed against the passwd layer | CTO | ruling only |

Tally (my count from the tables above, each class counted once): of the 59 not-done classes (56 in the plan + 3 missing), **9 need new infrastructure or production information** before Phase 1 can finish. They are extra_packages_el (RHEL node), user_samba (Zentyal), openvpn_domain (DC), mount_shares_desktop (desktop baseline), openvpn_nm_connection (ruling + NetworkManager), user_sysmon (module + monitoring-server role), openvpn_server and network_vpn (second NIC for a safe bridge, plus rulings), and firewall_addon_hosting (information). **The other 50 are reachable on the existing two VMs** with C1–C6. 5 of those 50 also wait on a Salatiel/Gustavo ruling (C5) and 16 on the lab-master fixture change (C4).

### E.4 Batch Forge compatibility audit (decided 2026-09-30, never recorded as done until now)
Sources: forgeapi.puppet.com, module CHANGELOG/REFERENCE.md at exact tags, the master's installed `metadata.json`. "openvox-only" means the release declares `openvox` and not `puppet` in `requirements`. That field is informational (r10k and `puppet module` do not enforce it, medium confidence), but it marks the module as untested on Perforce Puppet.
| module | production | lab today | recommended pin | requirement | notes |
|---|---|---|---|---|---|
| puppet-nginx | 0.15.0 | — | **8.4.0** | openvox-only ≥8.19 <9 | every parameter used checked against 8.x; `nginx_frontend_domain.pp:247` coercion is ours, not the module's; double `modules-enabled` include on Debian (Phase-3 item) |
| puppet-letsencrypt | 9.2 | — | **13.4.0** + puppet-epel 6.0.0 | openvox-only | 11.0.0 changed `certonly` cert_name default to `domains[0]`, which affects `letsencrypt_certificate.pp:32` |
| puppetlabs-mysql | 10.5.0 | — | **17.3.0** | puppet ≥8 <10 | deprecated mysqltuner/monitor unused |
| puppetlabs-postgresql (company layer) | unrecorded | — | 10.7.0 | puppet ≥8 <10 | all six entry points meaningful_puppet uses still exist |
| puppet-rabbitmq / puppet-gitlab (production, outside the 87) | unrecorded | — | 15.0.0 / 11.1.0 | openvox-only | |
| puppet-openvpn | 8.3.0 (puppet <7) | — | **12.0.0** (or 11.0.1) | openvox-only | two compile hazards in our manifest (E.2) |
| sysctl | thias-sysctl 1.0.7 | — | thias-sysctl **1.0.8** (puppet <9; diff vs 1.0.7 = legacy facts only) or augeasproviders_sysctl | | blocked.txt's "no module states Puppet 8 support" is wrong |
| htpasswd | leinaddm 0.0.3 (Puppet 3 `Puppet.newtype`, verified in the tarball) | — | **citrin-htpasswd 1.0.3** candidate: a fork whose only type-file diff is the `newtype` call (puppet ≥5.5.10) | | replacement = module ruling; semantics appear identical (verify providers) |
| ntp | unread | — | puppetlabs-ntp 11.x *after* reading production's module | puppet ≥8 | node_base and node_base_domain_desktop cannot compile without it |
| puppet-network / filemapper / kmod | 0.10.1 / 3.1.0 | 2.2.1 / 4.0.0 / 4.1.0 | keep | puppet ≥7 <9 | 3.0.0 exists; 2.2.1 validated |
| puppetlabs-apt | 7.7 | 11.3.2 | keep 11.3.2 | puppet ≥8 | |
| puppetlabs-concat | — | 9.1.0 | keep | | |
| puppetlabs-docker | 3.14 | 10.4.1 | keep 10.4.1 | puppet ≥8 <9 | powershell/reboot warnings are Windows-only deps |
| saz-ssh | unrecorded | 13.1.0 | keep 13.1.0 | puppet <9 | 14.x+ openvox-only |
| saz-sudo | unrecorded | 9.0.2 (**unpinned**) | pin 9.0.2 | puppet <9 | 10.x openvox-only |
| saz-resolv_conf | unrecorded | 8.0.1 (**unpinned**) | pin 8.0.1 | openvox-only | |
| puppetlabs-stdlib, resource_api, puppetserver_gem | 4.25.1 / — | 9.7.0 / … (**unpinned**) | pin to installed | | |
| puppet-systemd | camptocamp-systemd 3.0.0 (puppet <8) | 8.2.0 | keep | puppet+openvox <9 | camptocamp is not Puppet-8 compatible; outside our manifests |
| rsyslog module | none since 0.9.8 | — | **none** | | the plan's "external rsyslog module" is a false lead |
| cron_core | built-in on Puppet 5 | vendored 1.3.0 | none | | |

**Cross-cutting finding.** The newest release of 8 of these modules is openvox-only (nginx, letsencrypt, openvpn, rabbitmq, gitlab, saz-ssh ≥14, saz-sudo ≥10, resolv_conf 8). The module roadmap therefore depends on the CTO's runtime decision. If production stays on Perforce Puppet, several pins must be held at older majors, or run on a runtime the module never tested.

---

## F. Capability options (evaluated, not adopted)

Each option was researched by a separate read-only agent with sources (Forge API, vendor docs, man pages, measured lab logs). Numbers marked *estimate* are the agent's or mine, not measurements. Laptop today: 16 threads, 30 GB RAM (21 GB available), 808 GB free disk, VirtualBox 7.2.6; VMs running: master 4 GB/2 vCPU, node 3.2 GB/2 vCPU.

### F.1 Faster revert (highest leverage per hour)
- **Measured:** from 4 restores on 2026-10-05 in the node's `VBox.log`, power-on → BIOS at +2.8 s → kernel start at **~+36 s**, then sshd. The ~33 s pre-kernel gap matches GRUB's `recordfail` fallback (`/boot/grub/grub.cfg:108-109`, `set timeout=30`) that is baked into the baseline because the snapshot was taken after an unclean boot. The cause is *inferred from timing*; confirm with one console screenshot.
- **Tier 0** (recommended): `GRUB_RECORDFAIL_TIMEOUT=0` in the node baseline, a fresh offline baseline snapshot, and `controlvm poweroff` instead of ACPI for the **node only** (safe because restore follows immediately; keep the master deny rules). Expected revert **~25–35 s instead of ~120 s**. Cost 1–2 h, no topology/cert/master change. At least 2 reverts per class (advisor + Codex; 17 reverts for 8 classes observed) → saves **~3–6 min per class**.
- **Option 1, live (saved-state) snapshot:** ~15–20 s, but the guest resumes with its clock at snapshot time (months behind; the node has no VBoxService) and a stale 12 h DHCP lease on the Wi-Fi router. Worth it only after a forced clock step and static addressing.
- **Option 4, host-only/internal network with static IPs plus a NAT adapter:** removes the dependency on the home router's DHCP and the Wi-Fi bridge (H10). Certs and `puppet.conf` are unchanged (the server name resolves via `/etc/hosts`); netplan, `/etc/hosts` and ssh config change. Escalation-worthy on robustness grounds.
- **Rejected:** KVM/libvirt for the node (VirtualBox 7.x and an active KVM guest cannot run concurrently: `VERR_VMX_IN_VMX_ROOT_MODE`); Vagrant (not packaged for Ubuntu 26.04; BSL licence); linked clones of the current node (all share certname `puppet8node`; each clone needs its own cert, node file and hostname).

### F.2 Master-side and laptop-side fast gates before touching a VM
| gate | catches | cannot catch | time per class | where |
|---|---|---|---|---|
| Baseline-drift diff (manifest + every referenced template/file vs `release-0.9.8`) | hazard 8 mechanically; would flag 7 of 47 pending now, **including `puppet_boot_run`** | — | <1 s | laptop |
| `puppet parser validate` (Puppet 8 CLI) | syntax, escapes, metaparam misuse | unknown types/functions/variables | ~1 s (measured 0.86 s on master) | laptop (openvox-agent or apt puppet 8.10) or master |
| puppet-lint with an allowlist (`legacy_facts`, `top_scope_facts`, `variable_scope`, `duplicate_params`, `unquoted_resource_title`, `parameter_order`; never `--fix`) | legacy facts (incl. the `$::osfamily` class of bug), dynamic scope (hazard 7) | function existence (stdlib-4 removals), templates' `@legacy` facts | 1–2 s | laptop (apt puppet-lint 4.3.0) |
| ERB/EPP syntax + a template legacy-fact grep (`@hostname`, `@osfamily`, `@fqdn`, `scope.lookupvar('::…')`) | broken templates; **silently empty legacy facts** (openvpn_domain, postfix_smtp_node) | runtime template data | <1 s | laptop |
| Static hazard scanner (external types vs master `puppet module list`; OUTPUT/policy-drop; `validate_*`/`is_*`; exec without guard or with a guard binary absent on the node) | hazards 1, 2, 5, 6 + proposed 9 | subtle firewall ordering | <2 s | laptop |
| **Catalog compile on the master** against the node's cached facts (`test_class.sh --compile-only`: deploy + node block + `puppet catalog compile puppet8node`), also for **composites** (node_base with Debian and RedHat facts, meaningful_desktop closure) and **default-parameter** variants | unknown types/functions, `NUMERIC_COERCION` (nginx_frontend_domain:247), duplicate declarations (filesystem_yum/firewall/sysmon_puppet_cert_status vs filesystem_base), missing ntp/nginx/openvpn modules, missing Hiera keys | apply-time failures (missing binaries, packages, services, exec exits), idempotency, Resource-API munge validation done on the agent | ~5–15 s *estimate* | master (no node needed) |
| rspec-puppet / onceover on a laptop replica | as compile, faster iteration | same as compile; plus replica drift from the master (a second source of truth, P2 risk; Hiera contains credential keys) | 10–30 s | laptop — **not recommended** |
False-negative profile: on the 121 stored agent runs, 37 failures were compile errors (Error 500) and 9 were apply errors. A compile gate would have caught the 37 without a VM run; the 9 apply failures (missing directories, `pdbedit`, `/etc/network/interfaces`) need the node. Cost: Tier A (static, laptop) 2–4 h; Tier B (compile-only on master, composites) 2–4 h.

### F.3 Additional test nodes
| option | serves | hard limits | laptop cost | setup | verdict |
|---|---|---|---|---|---|
| **Incus/LXD unprivileged system container** (rockylinux/9, almalinux/9, ubuntu/24.04) on a btrfs loop pool with a NAT bridge | RedHat branches of packages_base, node_base, filesystem_base, sysmon_base, nginx/postfix/rsyslog EL paths; cheap second Ubuntu nodes for client/server pairs; `incus exec` control channel that **survives OUTPUT-drop firewall classes** (firewall_addon_hosting-type tests) | No modprobe (only host-side `linux.kernel_modules`): xt_geoip/xtables-addons, kmod impossible. Non-network sysctls read-only (net.* namespaced keys are writable; in-container `ip_forward` semantics unverified). No ecryptfs/cifs/nfs mounts. No bridged/macvlan NIC on a Wi-Fi host. Docker-in-container fragile on 24.04. Privileged containers are host-root-equivalent. **Does not unblock extra_packages_el** (Rocky/Alma lack RHEL entitlement repos). | ~0.1–0.15 GB idle each, ~1 GB disk each | 6–10 h | Adopt narrowly as a supplement: one EL9 container + one Ubuntu container; revert 10–30 s *estimate* |
| **RHEL-family VM** | extra_packages_el, RedHat branches | Rocky/Alma **cannot** validate extra_packages_el / packages_base[RedHat] / node_base[RedHat] (CRB exec needs `subscription-manager` with entitlement). Genuine RHEL needs the free Developer Subscription (16 systems, 1 year, renewable). The existing `RHEL9` VM is genuine RHEL 9.3, but its snapshot has a Perforce Puppet 5 agent + old CA; it must be rebased on "Updated & Upgraded" and OpenVox installed (`yum.voxpupuli.org/openvox8-release-el-9.noarch.rpm`, verified HTTP 200). | 2–4 GB RAM, ~15 GB disk | 2–3 h VM + 2–4 h harness node selection | Only variant A (reuse RHEL9) is worth it, and only if Salatiel wants RHEL branches validated in Phase 1 |
| **Second Ubuntu VM** (clone of the node with new hostname/cert) | rsyslog server/client, backup/sync, OpenVPN client, postfix relay, sftp_only negative tests | per-node cert, node file, snapshot; Wi-Fi bridge MAC flakiness with 3+ guests (unverified) | 2 GB RAM, ~7 GB disk | 2–3 h + harness node selection | Defer to Phase 3; a container covers most pairs cheaper |
| **Samba AD DC VM** (Ubuntu 24.04, `samba-tool domain provision`, realm DOMAIN.LOCAL / NetBIOS DOMAIN / host `fileserver`, matching the hard-coded `krb5.conf.erb:9-10`) | openvpn_domain (join target), user_samba (pdbedit/ldbsearch/sam.ldb) | A container is insufficient (NTACL xattr needs CAP_SYS_ADMIN → privileged). `create-user.pl.erb` uses Zentyal's EBox Perl API (`:8-9,25,31-39`) and cannot run on plain Samba; set-user-samba-hash.sh.erb can. Neither template is deployed by any manifest in 0.9.8 (production places them out of band, unverified). openvpn_domain's `id user@DOMAIN` guard may re-join every run. | 2 GB RAM, ~10 GB disk | ~3 h | Build only when Salatiel rules on a stand-in `create-user.pl` fixture |
| **Zentyal 8.1 Development VM** (free ISO, Ubuntu 24.04 base, released 2026-03-10) | user_samba faithfully | young release; AppArmor and its ownership of samba/DNS may fight the agent | 4 GB RAM, ~20 GB | 6–8 h | Only if production fidelity for user_samba matters (it is used via the passwd layer, count unknown) |
| **Desktop VMs** (existing `kubuntu-desktop`, `ubuntu-desktop`, powered off; the latter is "Joined to Puppet" against an unknown master) | user_kde_lock_screen, user_desktop*, mount_shares_desktop, linux_policies*, gnome_lock_screen, openvpn_nm_connection, meaningful_desktop closure (≈20 laptops) | needs a graphical fixture user; SMB server for mount_shares | 4 GB each | 3–5 h | Phase 3 for the desktop fleet; Phase 1 needs only the Desktop-dir fixture |

**Multi-node scenarios** need the same harness change: node selection (`NODE_HOST`/`MASTER_NODE_FILE` at `test_class.sh:29-32`, VM/snapshot/alias/hostname at `revert_node.sh:22-27,162`), per-node params (`params/<node>/<class>.json`), per-node node files on the master with CODEX MANAGED markers, and server-before-client ordering. That is 3–5 h, and it is a prerequisite for every option in this table.

### F.4 Behaviour checks (Phase 3)
**Recommendation:** a custom declarative check file per class, `.codex_state/checks/<class>.yml`, run from the laptop over ssh by a thin Python runner (~300–400 lines), with optional delegate runners (goss for bulk file/service/port assertions, ssh-audit, testssl.sh targeted runs, Playwright with the host's Chrome for Hashman/nginx flows). Zero footprint on the node. Output is JSON + JUnit under `.codex_state/logs/checks/`.
Rejected: InSpec (Chef licence key since 6.x), serverspec (Ruby toolchain, no gain), Bats (no structure, hard to audit for provenance). testinfra is the fallback if the runner grows past ~500 lines; generate pytest from the same YAML, never hand-write per class.

Minimal schema:
```yaml
class: backup_rsnapshot
upstream_ref: release-0.9.8:manifests/backup_rsnapshot.pp   # every probe cites upstream lines, not the migrated file
derived_from: [ "backup_rsnapshot.pp:20-35", "templates/backup/rsnapshot.conf.erb" ]
needs: { second_node: false, internet: false, browser: false, fixtures: [params] }
preconditions: [ "required_base applied", "node reverted" ]
negative_controls:          # must FAIL on the clean baseline (PRE phase) — guards against vacuous checks
  - id: conf-absent
    cmd: "test -f /etc/rsnapshot.d/rsnapshot-{{p.title}}.conf"
    expect: { rc: 1 }
probes:                     # POST phase, after GREEN
  - id: conf-valid
    cmd: "sudo rsnapshot -c /etc/rsnapshot.d/rsnapshot-{{p.title}}.conf configtest"
    expect: { rc: 0, stdout_re: "Syntax OK" }
  - id: cron
    cmd: "sudo crontab -l -u root"
    expect: { stdout_re: "rsnapshot -c /etc/rsnapshot.d/rsnapshot-{{p.title}}.conf daily" }
  - id: one-shot-run
    cmd: "sudo rsnapshot -c /etc/rsnapshot.d/rsnapshot-{{p.title}}.conf daily && sudo ls {{p.backdir}}/daily.0"
    expect: { rc: 0 }
pass: all probes pass AND all negative_controls failed in PRE
```
Two more worked examples from the research, abbreviated:
- *ssh_secure*: `sudo sshd -t`; `sudo sshd -T` fields (port, allowgroups, passwordauthentication, permitrootlogin, kexalgorithms, ciphers, macs); a positive login with an allowed kex/cipher; a **negative** login with a disallowed cipher and as a user outside `AllowGroups`. The ruling item it surfaces: `ClientAliveCountMax 0` disables idle termination since OpenSSH 8.2 (production's 4-hour idle disconnect no longer happens on Ubuntu ≥20.04).
- *nginx_static_domain*: `nginx -t`; `curl -sk --resolve <domain>:443:<node>` status, `Location` on the http→https redirect, HSTS header, served cert subject equals the fixture; `www_root` index served; a 404 for an absent path.

Keeping checks honest (P1): the author derives probes from **upstream** code and docs (`derived_from` lines are mandatory), negative controls must fail on the clean baseline, and the reviewer re-runs the checks and spot-checks `derived_from` against `release-0.9.8`. The main risk is circularity (an author who reads the migrated manifest writes checks that mirror it); a second risk is testing the Forge module instead of the class. Cost: 14–20 h for the runner + schema + 3 pilot classes; then ~0.5 h per class *estimate*. Per-class runtime +30 s to 2 min.

### F.5 Samba DC / Zentyal — see F.3. Phase-1 value is 2 classes (user_samba, openvpn_domain), both with zero node-file declarations (passwd-layer caveat applies). This is the lowest-leverage infrastructure in the list.

### F.6 Multi-node scenarios — see F.3; Phase-3 only, except openvpn_server/network_vpn, which in Phase 1 need a second NIC (host-only adapter) so the bridge and `systemctl restart networking` never touch the node's only NIC.

### F.7 Structured metrics — see F.9 below. The research confirmed the cheaper source: the node's `/opt/puppetlabs/puppet/public/last_run_summary.yaml` (plain YAML) and `last_run_report.yaml` (`transaction_uuid`) read right after each agent run. Codex token counts are in `~/.codex/sessions/<y>/<m>/<d>/rollout-*.jsonl` (`token_count` events). **Do not enable PuppetDB/OpenVoxDB or a report processor**: they need master config changes on a VM that must never be restored, plus ~4.6 GB disk the master does not have (58% of 12 GB used). A tracked metrics file cannot ride in the migrate commit without changing the reviewer's scope check, so it needs its own commit (`P8: record metrics after <class>`) and a reviewer.md exemption.

### F.8 Division of labour: should the advisor edit directly for some categories?
Evidence from D.4 and C.1:
- For **"validated unchanged" classes** (every forward green so far: 8/8 in the engine era, 13/17 forward overall), Codex's committed change is a 1–2 line header and a tracker line. The run costs a median 275 s and ~68 k Codex tokens, of which most is re-orientation (C.1), and 17 node reverts across 8 classes. All the decisive judgement (hazard checklist, `required_base`, baseline-sync, fixture choice) was made by the advisor before Codex started (advisor notes precede the Codex start by ~50–60 s in 6 of 8 cases).
- For **syntax-work classes** (firewall_secure: 11 `action`; firewall_secure_extra: 45 `action` plus predicted Resource-API type errors on `rseconds`/`rhitcount`/`connlimit_above`; legacy facts in postfix/openvpn templates; `$localdir` dynamic scope), Codex's iterate-against-the-harness loop is the right tool. The Phase-1 rule is "behaviour preserved", and those edits need the apply/fix cycle.
- For **bookkeeping** (headers, tracker lines, order regeneration, record fixes), Codex added one 47-minute hang (stdin) and the network_static header fix, and needs `git add -f` probing every run.

Recommendation (argued from evidence, not preference): split by category, keeping P1 intact.
1. *Unchanged-validated path, no Codex*: if a class's manifest and templates equal release-0.9.8, and `puppet parser validate` plus a catalog compile pass on the master, then the advisor runs the harness and writes the header and tracker line. The reviewer still verifies independently. This saves ~5 min and ~68 k tokens per class, and removes the Codex failure modes (hang, orientation, reverts) for about half of the remaining queue. Under the current rules this is a **CLAUDE.md change (Salatiel-tier)**, because it alters the generation model of 2026-07-01, so it is proposed here, not adopted.
2. *Syntax-work path, Codex*: give it an orientation packet in the prompt instead of letting it rediscover. That packet holds the class's plan row, the 0.9.8 diff status, the hazard findings, the fixture file, the expected module versions and the exact commit recipe.
3. *Records path, a script*: `record_green.sh <class>` writes the tracker marker, regenerates the order file, runs `git add -f` on the tracked files and commits with the convention. A script cannot forget the annotation, and the reviewer checks its result.
The reviewer's independence is unaffected. It never reads who authored the change, only git, upstream and its own harness run.

### F.9 Structured run metrics
Proposed per-attempt JSON record, written by the skill to `.codex_state/runs/<class>.<attempt>.json` and tracked, because it is append-only history (P2-exempt):
```json
{"class":"puppet_backup","attempt":1,"advisor":"claude-opus-5-5","executor":"codex-cli 0.159.2 gpt-6.1-sol xhigh",
 "t_hazard_start":"…","t_revert_start":"…","revert_s":118,"t_codex_start":"…","codex_s":199,"codex_tokens":48868,
 "harness_runs":1,"agent_runs":[{"transaction_uuid":"…","status":"changed","res_total":17,"res_changed":9,"t_total":8.3}],
 "reviewer_s":95,"reviewer_verdict":"PASS","reviewer_checks":{"git":"ok","scope":"ok","faithful":"ok","records":"ok","idempotent":"ok","fixtures":"ok"},
 "outcome":"GREEN","commits":["f7717c8","123e297"],"hazards":["item4: required_base=filesystem_base"],"human_interventions":0}
```
Agent-run data can be read from the master's stored reports by `transaction_uuid` (the reports already contain `metrics.time.*` and `metrics.resources.*`; see C.4 for the filename-collision caveat). `codex exec --json` gives per-event timestamps. Cost is about 2–3 hours, mostly in the skill and one Python helper. It turns C from estimates into measurements.

---

## G. Process and tooling flaws (evidence-backed)

1. **Three hand-maintained copies of the hazard checklist** (CLAUDE.md 8 items; SKILL.md says "7-item"; runbook §5 8 bullets, different content) and **two copies of the tracker/annotation rules** (wrapper prompt + runbook §2 + CLAUDE.md "Loop invariants"). P2 ("derive, don't duplicate") is applied to data files but not to the instructions that drive the engine.
2. **The executor's authority document is unversioned and off-repo** (A.2 #8). A Codex behaviour change cannot be correlated with a runbook change.
3. **No tests for any tool.** `gen_migration_order.py` (590 lines), `status.py`, `test_class.sh` (411 lines), `revert_node.sh`, `codex_migrate_class`: zero tests, no `shellcheck`/`bats`, no sample-plan fixture. The generator's parser accepts a `title` column but the harness rejects a define without params even when the plan has a default title (`test_class.sh:271`), which killed `backup`'s first two harness runs.
4. **Harness idempotency gate is a regex over run-2 stdout** (`test_class.sh:403`): `changed|created|defined content as|Scheduling refresh`. It does **not** match `executed successfully` (an `exec` without `unless/onlyif/creates/refreshonly` that runs every time) nor `removed`/`ensure: absent` flaps, and run 2 exit code 2 ("changes applied") is accepted as success (`test_class.sh:361`). A non-idempotent exec passes GREEN. No such case has occurred yet (`executed successfully` appears in none of the 10 logs), but one is predicted for a high-use class: `packages_base` (59 node statements) declares `class { 'apt': update => { frequency => 'always' } }`, so `Exec[apt_update]` runs on every agent run and prints only `executed successfully` (E.2). 13 pending classes carry execs.
5. **The harness catalog is never isolated**: the master's `puppet8node.pp` includes `passwd_common` outside the managed block (`ssh puppet8master sudo cat .../nodes/puppet8node.pp`), so every GREEN also depends on a confidential class the engine neither reads nor controls. The master's own agent daemon is enabled and active (`systemctl is-enabled puppet` → enabled) and applies `passwd_common` to the master every 30 min.
6. **Hardcoded lab identity.** `NODE_HOST=puppet8node`, `MASTER_NODE_FILE=.../nodes/puppet8node.pp` (`test_class.sh:29-32`), VM names and snapshot name (`revert_node.sh:22-27`), repo path, and DHCP-assigned IPs in `~/.ssh/config` and the node's `/etc/hosts` (192.168.77.185/.166 from the home router; the node is `dhcp4: true`). A second node, a second OS, or a new network each require edits in 3–4 places. Both VMs bridge to Wi-Fi `wlo1`, which is the sole reason for the 45 s settle and the 120 s SSH timeout.
7. **"First action: run the harness"** (`codex_migrate_class:37`) runs before any revert; combined with Codex deciding when to revert (1–4 times per run), node state at run 1 is undefined, and the reviewer's "independent" idempotency check is runs 3–4 on the same mutated node.
8. **Unpinned Puppetfile lines** (A.2 #9) despite the pinning rule; `necessary_modules.txt` versionless; Puppetfile not in the repo.
9. **Blocked entries are append-only prose** with no fields; `status.py` extracts the category by regex (`status.py:27`). Stale leads are never refreshed (A.2 #5).
10. **`.git/info/exclude` + `git add -f`** workflow (A.2 #7) — a per-clone, undocumented, contradictory convention.
11. **The repo's own lint gate is inactive**: `pre-commit` (puppet-lint) exists but is not installed in `.git/hooks`, and `puppet-lint` is not installed on the laptop or the master. No `puppet parser validate` runs anywhere before the VM is touched.
12. **Node baseline is 4 months old and self-mutating**: snapshot `P8NODE_BASELINE_GREEN` is from 2026-06-30; `unattended-upgrades` and `apt-daily*.timer` are enabled/active in it, so each revert boots a node that may start installing updates concurrently with a harness run (apt lock contention with `Package` resources; package state drifts from the snapshot: apt lists dated 2026-10-15/18 were observed on the restored node).
13. **Things that depend on a human remembering**: pinning inside the consumer's range; `puppet generate types` + puppetserver restart after a custom-type module; `</dev/null` + timeout on ad-hoc `codex exec`; `git add -f`; regenerating the order file; appending to DESIGN_DECISIONS; not restoring the master; updating `blocked.txt` when a lead changes; recording toolchain changes. None is enforced by a tool.
14. **Design-log usability**: 481 lines, append-only, read-before-first-class by rule; current state must be reconstructed by reading all entries and resolving supersessions by hand (3 explicit supersessions, 2 implicit ones found in A.2). There is no derived "current rules" view, which is exactly what P2 would prescribe (a generated digest from the append-only source).

Proposed hazard-checklist additions (from history): (9) **exec idempotency**: every `exec` must have `unless/onlyif/creates/refreshonly` and the guard must be runnable on the node — evidence: harness regex gap (#4) and user_samba's unrunnable guards; (10) **define params fixture present**: `test_class.sh --render-only <class>` must succeed before Codex is invoked — evidence: backup's two dead harness runs; (11) **shared template/file check**: list every `template()`/`source =>` the class uses and whether another class (0.9.8 `git grep`) consumes it — evidence: user_kde_lock_screen_common's shared script (dd3e1dc) and rsyslog's `forward_simple` template; (12) **package/service side effects on the node**: classes that install packages or restart services (ssh_secure, nginx_*, mysql) must declare how the harness keeps SSH alive — evidence: ssh_secure changed sshd config on the harness's own control path (f4cca21) with no explicit guard; (13) **runtime-baseline drift**: the node's `apt` timers (#12).

---

## H. Risk register

| # | Risk | Likelihood / impact | Evidence | Current control | Gap |
|---|---|---|---|---|---|
| H1 | **Node↔master severance** by a class that drops OUTPUT or changes sshd/firewall on the control path: run 2 hangs, node must be reverted by hand | Medium / Medium (lab only) | firewall_addon_hosting blocked for exactly this (`blocked.txt:6`, candidate header); firewall_secure_extra (anti-DDoS, mangle/nat) and ssh_secure (port/acl params) are pending/done with no explicit control | Hazard item 2 (manual) | No automated pre-check (`iptables-save`-level simulation or catalog grep for `chain => 'OUTPUT'`/`policy => drop`); harness has no run timeout, so a hang blocks the loop indefinitely |
| H2 | **Master as single point of truth without snapshot**: Puppetfile pins, 11 modules, node files, `.resource_types` live only on a VM that must never be restored | Low / High | A.2 #9; snapshot 2026-06-30 "7 modules" vs 18 now | "never restore the master" rule | No export of Puppetfile/node files to the repo; no master backup; master disk 58% of 12 GB |
| H3 | **Baseline drift (node)**: 4-month-old snapshot with unattended-upgrades active; package versions at run time differ from the snapshot and between runs | High / Low–Medium | G #12; apt lists 2026-10-15/18 on restored node | Revert before each class | Snapshot refresh policy; disable apt timers in the baseline (behaviour-neutral for Phase 1) |
| H4 | **Baseline drift (code)**: production runs 0.9.10; `release-0.9.8..release-0.9.10` changes only docker_container (+2 lines, `$command`) and rsyslog_server (+64 lines, 4 templates incl. a new retention script and logrotate timer). The large mysql_server rewrite (+mariadb_server.pp, mysql_db.pp) is on the **unmerged** upstream branch `issue-122-review-mysql-support`, which is what the local upstream clone currently has checked out. 3 classes used in production are missing from the plan | Certain / Medium | `git diff --stat release-0.9.8 origin/release-0.9.10`; `git -C upstream rev-parse --abbrev-ref HEAD`; A.2 #1 | "catch-up at phase boundary" policy; reviewer diffs the tag, not HEAD | rsyslog_server will be migrated to content production no longer runs; any tool or agent that reads upstream `HEAD` instead of the tag sees a mysql_server production has never run; the 3 missing classes are not on any list |
| H5 | **False confidence from GREEN**: idempotent-but-wrong migrations pass — regex gap on exec/removal, run-2 rc=2 accepted, catalogs that are no-ops on the node (network_static writes `/etc/network/*` that netplan never reads — advisor note 2026-09-30), `passwd_common` in every catalog | High / High (this is the Phase-3 question) | G #4, #5; `network_static.advisor.log` | Reviewer diff-faithfulness + re-harness | No behaviour checks; reviewer cannot see runtime effect; see D and F |
| H6 | **Reviewer blind spots**: it diffs the manifest only (templates/files only "if genuinely needed"), re-runs the harness on a node already converged by Codex, cannot see params JSON values except by reading the same files Codex wrote, and has no persisted output | High / Medium | `reviewer.md:15-26`; metrics.csv reviewer column all "inferred" | P1 independence rule | Verdicts not stored; no check of template/file diffs vs 0.9.8; no check that the catalog actually exercised the class (resource count delta) |
| H7 | **Secrets / confidential data**: the lab master holds a `nodes/passwd/` directory (seen in `ls`, not read) and the test node applies `passwd_common`; params JSON for identity defines carry hashes (`user_sysmon.json` keys `myhash`, `user_samba.json` `mysmbhash` — values synthetic per blocked.txt, unverified); Codex logs `cat` params files into untracked logs; Hiera `common.yaml` on the master has placeholder credentials | Medium / High if the laptop or a log leaks | `ls manifests/nodes` on master; params listing | params untracked; logs untracked; `.codex_state/` excluded | No rule that forbids real hashes in params; no scrub of logs; passwd provenance on the lab master undocumented |
| H8 | **Upstream-drift of templates shared with Done classes** (baseline-sync of a shared template silently changes a migrated class) | Medium / Medium | 2026-10-01 ruling; dd3e1dc touched `files/user_kde_lock_screen/configure_lock_screen.sh` used by pending user_kde_lock_screen | escalate-if-shared rule (manual) | hazard item 11 proposed above |
| H9 | **Model/tool behaviour regression**: Codex CLI 0.145→0.159.2, model gpt-5.6-sol→gpt-6.1-sol, a "superpowers" plugin now injected, reviewer model `opus` unpinned to a version — all changed without a decision entry | Medium / Medium | A.2 #3 | none | Pin and record versions; keep a 1-class canary (e.g. re-run a done class) after any toolchain change |
| H10 | **Lab network fragility**: DHCP addresses from a home router hardcoded in ssh config and `/etc/hosts`; Wi-Fi bridge settle drives the 120 s timeouts; already broke once ("Supersedes wlan0 baseline", snapshot description) | Medium / High (whole engine stops) | `ssh -G`; node netplan `dhcp4: true`; revert_node.sh:15 | none | host-only/internal network with static IPs (F) |
| H11 | **Hang without timeout**: harness `puppet agent -t` and `codex exec` have no outer timeout; a severed node blocks the loop until a human notices | Medium / Medium | 47-min stdin hang; H1 | `</dev/null` in wrapper | `timeout` wrappers; a watchdog in the skill |
| H12 | **r10k purge of `puppet_infrastructure`** during a dependency install leaves the master without the module until the next harness deploy | Medium / Low | runbook §5; report 2026-03-31T13:27:09Z "Could not retrieve information from environment production" | prose warning | deploy module via r10k (git source) or a separate modulepath |
| H13 | **Unused-class effort**: ~30% of greens and ~57% of blocks spent on classes with no node-file usage | Certain / Medium (funding) | B.3 | none | fleet-weighted ordering (I) |

---

## I. Roadmap

Baseline for "after" numbers (C): ~6.5 min wall per "validated unchanged" class (2026-10-05 batch), Codex median 275 s / 68 k tokens, 2+ reverts per class at ~120 s each, and blockers discovered reactively, one Codex run each. 59 classes are not done (56 + 3 missing); 50 of them are reachable on the current two VMs (E.3).

### Epic 1 — Make GREEN mean what it says (do first; it protects every later green)
| # | change | leverage | cost | measure |
|---|---|---|---|---|
| 1.1 | Harness: require run-2 rc == 0 (detailed exit codes); fail on `executed successfully`/`removed`; add an outer `timeout` to each agent run and to `codex exec` | Catches the packages_base `Exec[apt_update]` false GREEN (59 node stmts) and any exec-bearing class (13 pending); ends indefinite hangs (47 min observed) | 1 h | a known-bad fixture (an unguarded exec) turns RED |
| 1.2 | Revert first: the wrapper's first action becomes revert, and the reviewer reverts before its own harness run (run 1 must create the class's resources) | Makes runs reproducible; reviewer independence becomes real | 1 h | reviewer run-1 shows creations |
| 1.3 | Coverage signal: the harness prints the catalog's resource titles for the target class and fails if 0 | Catches classes whose body was skipped | 1 h | |
| 1.4 | Reviewer v2: diff templates/files too; two-diff method; persist verdicts as JSON; check header claims mechanically against `puppet module list`; check that blocked.txt/candidates deltas name only the target | Closes blind spots D.3 #2, #4, #6 and catches filesystem_yum-type provenance errors | 2–3 h | re-review the 31 done classes: expect FAIL on filesystem_yum, docker_container, sftp_only, ssh_secure, network_dhcp (headers), sysmon_puppet_cert_status |
| 1.5 | Re-review sweep of the 31 done classes with reviewer v2; record a reconciliation list (filesystem_yum false provenance, sysmon_puppet_cert_status reimplementation, firewall default removal, rsyslog_base `$settings::ssldir`, 4 missing headers, tracker typo) | Turns "31 done" into a known-quality number | 2 h | list committed as an escalation |

### Epic 2 — Pre-VM gates (cheap failures stay cheap)
| 2.1 | `pregate.sh <class>` on the laptop: drift diff incl. templates, `parser validate`, allowlisted puppet-lint, ERB/EPP check + legacy-fact grep, static hazard scanner (items 1, 2, 5, 6, 9) | Converts 37/46 historical failure runs (compile errors) into seconds; flags puppet_boot_run and 6 other drifted classes before Codex | 2–4 h | % of Codex runs whose first harness run fails to compile → ~0 |
| 2.2 | `test_class.sh --compile-only` on the master, plus composite compiles: node_base (Debian + RedHat facts), meaningful_desktop closure, and default-param variants | Finds duplicate declarations (3 known), NUMERIC_COERCION, missing modules/Hiera keys with no node | 2–4 h | composite compile becomes a standing check after each green |

### Epic 3 — Remove the per-class overhead
| 3.1 | Tier-0 revert: GRUB recordfail fix + node hard poweroff + new baseline (also disable apt timers in the baseline, G #12) | ~120 s → ~25–35 s per revert; at ≥2 reverts per class, **~3–6 min saved per class** | 1–2 h | revert_s in metrics |
| 3.2 | Orientation packet in the Codex prompt (plan row, drift status, hazard notes, fixture path, module versions, commit recipe) + `record_green.sh` for tracker/order/commit | Cuts Codex re-orientation (60–80% of commands); removes `git add -f` probing and annotation errors | 2–3 h | Codex tokens/class (68 k baseline), exec cmds/class (29 baseline) |
| 3.3 | (Salatiel ruling) Advisor-direct path for "validated unchanged" classes (F.8) | ~5 min and ~68 k Codex tokens saved per class on roughly half the remaining queue | 1 h (CLAUDE.md/skill) | |
| 3.4 | Per-attempt metrics JSONL (F.9) | Makes every number in this report measured | 4–6 h | — |
| 3.5 | Single sources: one hazard checklist file consumed by CLAUDE.md, the skill and the runbook; runbook into the repo; Puppetfile exported to the repo on each change; a generated "current rules" digest from DESIGN_DECISIONS | Ends 3-copy drift (A.2 #2, #8, #9; G #1, #14) | 3 h | |

### Epic 4 — Prepare the queue in one advisor batch (C1–C5)
| 4.1 | Plan fixes for 23 classes (C1); Forge pins for ~17 (C2, after the runtime decision for openvox-only majors); baseline-syncs for 6 (C3 advisor tier); pin the 5 unpinned Puppetfile lines | Converts ~45 classes from "discover the blocker in a Codex run" to "ready" | 5–8 h | Codex runs per green → 1 |
| 4.2 | Escalation files for: puppet_boot_run (next class, predicted RED), import of the 3 missing classes, sysctl and htpasswd module rulings, openvpn_server upstream defects, fqdn_rand_uuid fix authorization, rsyslog_server 0.9.10 timing, node_base_desktop sync, the lab-master `extra_files` mount + Hiera fixtures (C4) | Unblocks 16 (C4) + 5 (C5) + 3 missing | 3 h writing | rulings received |
| 4.3 | Fleet-weighted ordering: add a `prod_nodes` column (derived from `fleet_class_usage.md`) as the secondary sort key after dependencies | The node_base closure (58 servers) and the nginx/ssl stack (company layer) come before unused classes | 1 h | |

### Epic 5 — Phase-3 behaviour verification
| 5.1 | Check runner + schema + 3 pilots (backup_rsnapshot, ssh_secure, nginx_static_domain) (F.4) | Starts answering "does it work" for the 31 done classes | 14–20 h | pilots run PRE and POST, with negative controls failing on baseline |
| 5.2 | Checks for the node_base closure first (11 classes, 58 servers), then the nginx/ssl stack (company layer) | Highest fleet impact per check | ~0.5 h/class | |
| 5.3 | Node selection in the harness, then an EL9 Incus container and an Ubuntu container as second nodes; second NIC on the node VM | RedHat branches, client/server pairs, safe bridge tests | 3–5 h + 6–10 h | |
| 5.4 | Optional infrastructure by ruling: RHEL9 VM (subscription), desktop VM, Samba DC/Zentyal | extra_packages_el; desktop fleet (≈20 laptops); 2 Samba classes | 3–8 h each | |

### First engine sprint (proposal) — ~25–30 h
Epic 1 (1.1–1.5), Epic 2 (2.1–2.2), Epic 3.1 + 3.2, Epic 4.1 for the node_base closure and the nginx/ssl stack, plus all Epic 4.2 escalation files.
**Expected throughput after it** (*estimate*, to be checked against the 3.4 metrics): unchanged-validated classes ~3–4 min wall (from ~6.5); syntax-work classes ~10–15 min with one Codex run each, instead of one run per reactively discovered blocker. That puts the 50 reachable classes at roughly **6–9 hours of loop time (2–3 sessions)**, gated mainly by how fast the C4/C5 rulings come back. The node_base closure (58 servers) and the company-layer nginx stack (37 servers) can be done in the first of those sessions. The improvement can be measured: revert_s, codex_s, tokens/class, Codex runs per green, and reviewer FAIL rate, from the per-attempt JSONL.

### Decisions needed, by owner
**Salatiel / HQ** (engine, lab, process, budget):
1. Approve the harness correctness changes (Epic 1) and the generation-model change for unchanged classes (3.3).
2. Lab-master changes: `extra_files` fileserver mount with throwaway PKI; Hiera fixture keys; pinning the 5 unpinned Puppetfile lines; exporting the Puppetfile and node files into the repo.
3. puppet_boot_run escalation (option a/b/c in E.0) before the next `/migrate-next`.
4. Import of `gnome_lock_screen`, `firewall_ipv6_drop_policy_desktop`, `rsyslog_apparmor_exception` (edits beyond a target class).
5. Module rulings: sysctl (thias 1.0.8 vs augeasproviders), htpasswd (citrin fork vs patch), user_samba stand-in script vs Zentyal.
6. Reconciliation of done classes found defective (filesystem_yum provenance, sysmon_puppet_cert_status, firewall, rsyslog_base/client, 4 headers).
7. Which new nodes to fund: an EL9 container (cheap), the RHEL9 VM (subscription), desktop VM, Samba DC.
8. Phase-3 entry: adopt the behaviour-check format, and re-derive the escalation bar for Phase 3 (CLAUDE.md "Phase scoping").

**CTO (Gustavo)** (production and upstream):
1. **Runtime:** OpenVox 8 now / OpenVox 9 in 2027, vs Perforce Puppet Core. Perforce's public Puppet 8 binaries stopped at 8.10 (2024-10-22). Puppet Core needs a Forge API key, and its 2026-02-26 licence counts Open Source Puppet nodes as Managed Nodes, with fees beyond 25 nodes (the fleet has 78). The choice also fixes the module majors (E.4).
2. **Upstream bugs:** `fqdn_rand_uuid` (openvpn_nm_connection); openvpn_server's `Service['openvpn']` and duplicate `openvpn-server@` service; puppet_boot_run's oneshot + `ensure => running`; `nginx_frontend_domain.pp:247` string coercion; `filesystem_sec`'s documented default-group branch that cannot compile; `ClientAliveCountMax 0` semantics in ssh_secure.
3. **Hosting nodes and 8140:** do hosting servers run agent-mode? (firewall_addon_hosting).
4. **Unused classes to drop**, from the 33 zero-declaration classes (checked against the passwd layer, which this diagnosis could not read): candidates are nginx_proxy_smtp_auth_ppa, node_base_desktop, node_base_domain_desktop, nginx_frontend_mail, nginx_static, linux_policies_*, openvpn_domain, the firewall base class (production uses firewall_secure), firewall_addon_xrdp, network_static, hello_world_flask*.
5. **Baseline target:** migrate rsyslog_server to 0.9.8 now or catch up to 0.9.10 first; whether the unmerged Issue #122 MySQL rewrite will be released before mysql_server is migrated.
6. **Production facts** for the inspection trip: the ntp module identity, the RHEL server count, the Naemon check account, where the Zentyal helper scripts come from, and nginx_base parameters as used by the company layer.


---

## Assumptions and limits of this diagnosis
- **No questions were asked**; every gap is stated as an assumption here or marked unverified in place.
- "Production node" = a `node` statement outside `deleted/` and `tests/` in `~/work/puppet-nodes`. The regex desktop node is counted once, though it stands for ≈20 laptops per the CTO document.
- The `passwd/` layer was not read (constraint 3). Usage counts for identity and secret-bearing defines are therefore lower bounds.
- Conditional includes are counted unconditionally in the fleet closure (`fleet_class_usage.md` marks them).
- Per-class timing comes from file mtimes, filename epochs and commit times. Reviewer verdicts other than network_static's FAIL are inferred from the absence of corrective commits.
- The hard-class, Forge, edit-quality and capability findings come from 25 read-only research agents. I re-verified the load-bearing claims myself: the mysql/0.9.10 drift correction, the four missing headers, `filesystem_yum` and `sysmon_puppet_cert_status` code, the 0ecf985 scope, the tracker typo and the real-NIC fixture (filename only). Statements marked *predicted* come from reading module type definitions; no catalog was compiled in this run.
- Lab probes were read-only. Two kinds wrote outside the repo: the agent reports were copied into the scratchpad, and research agents left Forge evidence files in the scratchpad. Nothing was written under `infra_populi` except `.codex_state/diagnosis/`.
- The brief's "~28 of 87" is taken to mean the git-derived done count, which is 31.
