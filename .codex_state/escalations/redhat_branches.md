# RedHat branches of done classes on p8lab-rhel9 (HQ batch-8 ruling 6; 2026-11-18)

**Status: 14 of the 16 done classes with OS-specific branches PASS a reviewer verdict on rhel9
(reviews/<class>/nodes/rhel9/). Two fail on the baseline's own RedHat behaviour. These are findings for HQ, not
migration defects: the reviewer found the migrated code faithful, and neither failure comes from the migration.**

## The pass
- **Method:**
  1. A revert-first harness triage of the 16 classes on rhel9 (advisor).
  2. Engine and records fixes where the cause was the lab or the records.
  3. A reviewer verdict per node (`<class> --node rhel9`, new this pass) for every GREEN class.
- **PASS (14):** filesystem_base, ssh_secure, ssl_base, rsyslog_base, filesystem_sec, user_sudoer, caching_nameserver,
  packages_base, node_base, postfix_smtp_node, nginx_base (the ruled single modules-enabled include holds on RedHat:
  one include, nginx -t ok, nginx-1.20.1 active), nginx_static_domain, nginx_frontend_domain, nginx_frontend.
- **Fixed along the way (not findings):**
  - The harness no longer declares the Debian-only `apt` external on RedHat. It had failed the 4 nginx classes.
  - The lab Hiera now has postfix_smtp_node's hostname-keyed relay keys for p8lab-rhel9.
  - packages_base/node_base list `Exec[dnf-makecache]` as an expected run-2 event. The RedHat branch runs it on every
    agent run by design, the counterpart of `Exec[apt_update]`. Plan and headers updated.
  - filesystem_base's header said release-0.9.8; corrected (the rhel9 reviewer noticed).

## Finding 1: sysmon_base (filesystem_lib64) cannot apply on a fresh RHEL 9 node
- **Evidence:** the harness on rhel9 (fresh node), run 1:
  - `Package[nagios-plugins-all]` (packages_base, RedHat branch: `$nagios_package_name = 'nagios-plugins-all'`)
    created `/usr/lib64/nagios/` as a real directory (it holds plugins/).
  - Then `File[/usr/lib64/nagios/]` (filesystem_lib64.pp:11-15, `ensure => link, target => /usr/lib/nagios`) failed:
    `change from 'directory' to 'link' failed: Could not remove existing file`. sysmon_base's plugin files under
    /usr/lib64/nagios/plugins were skipped (failed dependency).
- **Baseline:**
  - filesystem_lib64's purpose comment says "a ubuntu only filesystem compatibility measure related to nagios plugins
    invocation".
  - Yet sysmon_base declares it on RedHat too, where the distribution's package owns that path as a directory.
- **On production:** a long-lived RHEL node may never hit this. If the link predates the package, rpm would install
  through it. But any freshly built RHEL node fails here.
- **Options:**
  1. Leave it (baseline behaviour); document it for RHEL node builds.
  2. A ruled fix: declare filesystem_lib64 only on Debian. This changes behaviour on RedHat, so it is HQ's.
  3. Order filesystem_lib64 before packages_base on RedHat. Still a behaviour change, and it would bend the
     distribution's own directory into a link.
- **Recommendation:** 2, as an upstream defect, or 1 if HQ prefers no RedHat change in Phase 1.

## Finding 2: hello_world_flask_common needs EPEL, which nothing in its closure declares
- **Evidence:** the harness on rhel9, run 1: `dnf -y install python3-gunicorn`: "No match for argument:
  python3-gunicorn". python3-flask fails the same way. Only BaseOS and AppStream are enabled, as on a stock
  registered RHEL 9.
- **Baseline:** `package { [ 'python3-gunicorn', 'python3-flask' ]: }` (hello_world_flask_common.pp:10). On RHEL both
  come from EPEL. extra_packages_el installs EPEL, but hello_world_flask_common neither declares nor requires it.
- **Options:**
  1. A plan-only fix: on RedHat nodes the class needs extra_packages_el as required_base. That needs a per-OS
     required_base, which the plan cannot express yet: a small engine change, then re-review on rhel9.
  2. Document "RedHat nodes using it must declare extra_packages_el" and test it on rhel9 with a node-specific
     required_base.
  3. A ruled code change: require Class['puppet_infrastructure::extra_packages_el'] on RedHat. This changes behaviour.
- **Recommendation:** 1 (it changes no code; the dependency is real on RedHat). 0 production node statements declare
  hello_world_flask_common (fleet_class_usage.md).

## Resolution (HQ 2026-11-18 ruling A2): 16 of 16 PASS on rhel9
- **The ruling:** no class changes. The plan's required_base becomes node-kind-aware, as production composes these
  classes under node_base. Its condition was to stop and show HQ the line if a class's own code forced the dependency
  regardless of OS. Neither class does:
  - sysmon_base's `/usr/lib64/nagios/plugins/check_cpu.py` and `check_mem.pl` require only
    `Class['puppet_infrastructure::packages_base']`.
  - hello_world_flask_common declares its two packages and names no repository.
- **Built (ffda52e):** required_base entries take an OS-family qualifier, `<class> [Debian]` / `<class> [RedHat]`. The
  harness, the reviewer, pregate and orientation resolve them for the target node's family.
  - sysmon_base: `filesystem_base, packages_base, filesystem_lib64 [Debian]`;
  - hello_world_flask_common and hello_world_flask (which includes it): `filesystem_base, extra_packages_el [RedHat]`.
- **Evidence:**
  - revert-first harness GREEN on rhel9 for both classes (2026-11-18);
  - reviewer verdicts per node PASS: `reviews/sysmon_base/nodes/rhel9/20261118T080256Z.json` and
    `reviews/hello_world_flask_common/nodes/rhel9/20261118T080631Z.json`.

  On Ubuntu nothing changes: the qualified entries resolve to the same lists as before (Debian keeps
  filesystem_lib64; extra_packages_el is RedHat-only).
- **Also corrected:** hello_world_flask_common's header named release-0.9.8. It was fixed with `record_green.sh --fix`
  and re-reviewed.
