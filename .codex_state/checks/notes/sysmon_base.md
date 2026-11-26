# sysmon_base: authoring notes (the comments of .codex_state/checks/sysmon_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sysmon_base (class; node ubuntu; required_base filesystem_lib64 [Debian];
# no parameters). The class installs the node-side Nagios checks a monitoring server runs over NRPE or SSH. Each check
# below runs one of them on the node as the monitoring server would, with thresholds chosen to reach a known state.
# Values were measured on the node after one harness apply (2026-11-18) before writing them; the netstat scripts and
# nagios-puppet.sh did not reach their intended results there (see the outcomes table).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1b): the RedHat branch is checked in the variant run `rhel` (rhel9).
# 2026-11-23 authoring correction (sweep run 20261123T122804Z-author, variant rhel): the package-count probe piped the
# check into `head -1` and took the check's exit status from PIPESTATUS; head closed the pipe after the first line, so
# the check died of SIGPIPE (rc=141) after printing `OK -`. The probe now captures the output first and takes the
# check's own exit status.
  # Correction round 3 (2026-11-19, HQ batch-12 ruling 3; review 20261118T211242Z): the Puppet check's failed-run
  # CRITICAL branch (agent exit above 2) is exercised, and the Elasticsearch stand-in records the request it gets.
  # Sweep correction round 1 (2026-11-23, review FAIL cc10c36; the sweep's own review cycle): the RedHat package count is
  # checked against dnf's own list at a threshold it reaches (558 Important entries measured on the rhel9 node that day),
  # the RHEL install check covers every file as the Ubuntu one does, and check_os_version.sh runs on rhel9 (no lsb_release).
  # Its first run (20261123T181515Z) printed the state word of every line: the check's output carries its package list
  # over many lines (WARNING, rc=1, the count equal to dnf's, all as expected); the effect now reads the first line only.
  # Correction round 2 (2026-11-18, review 20261118T210122Z): the Elasticsearch check is exercised on the node (it
  # queries localhost:9200, so a stand-in there drives it), and the RHEL package-count branch has its own row.
  # Correction round 1 (2026-11-18, review 20261118T204912Z): every alarm path is now exercised (the Puppet check's
  # CRITICAL, the stale package list, CPU CRITICAL under load, bandwidth WARNING and CRITICAL), measured by hand on the
  # applied node first.
  # 2026-11-18 authoring correction (run 2, 20261118T201641Z): `grep -c` exits 1 when it counts 0, so the probe's last
  # line made rc 1 once netstat was present; it now ends with `|| true`.
  # 2026-11-18 authoring correction (run 3, 20261118T202120Z): the check prints its package list one name per line
  # after the status, so only its first line is compared now.
  # 2026-11-18 authoring correction (run 3, 20261118T202120Z): `grep -c` exits 1 when it counts 0; the last line now
  # ends with `|| true`.
```
