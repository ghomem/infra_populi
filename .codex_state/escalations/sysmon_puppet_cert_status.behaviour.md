# sysmon_puppet_cert_status — behaviour finding (RULED 2026-11-22, HQ after batch 20 item 3; fixed by local change #19)

Production use 0 (migration_order.md). The class installs `files/sysmon/check_puppet_cert_health.py` (baseline cf477c6),
a Nagios check meant for the Puppet master. Line 11 runs `puppet certregen healthcheck --all --render-as yaml` and
reports the earliest certificate expiry.

## Finding — the check cannot report on OpenVox 8
- `certregen` is a Puppet face that came from a separate module (puppetlabs-certregen). Neither the baseline's code
  tree nor the lab's Puppetfile carries that module (git grep certregen at cf477c6: only the script itself).
- Measured 2026-11-21:
  - on the agent node puppet8node, with the class applied, `PATH=/opt/puppetlabs/bin:$PATH check_puppet_cert_health.py`
    prints `command 'puppet certregen healthcheck --all --render-as yaml' failed` and exits 1, and
    `puppet certregen --help` answers `Error: Unknown subcommand 'certregen'` (puppet 8.24.2);
  - on the master-role node p8lab-puppetserver (openvox-server, puppet 8.24.2), `puppet certregen --help` gives the
    same error, and `puppet module list --all` shows no certregen module.
- So on the target release the check reports exit 1 (Nagios WARNING, "command failed") on every run, and never reports
  an expiring or expired certificate. The set's check `reports-certificate-health` expects a Nagios state line and
  fails.
- Whether production's Puppet 5 master has the certregen module installed is fleet data that I have not read.

## Options
- **A: install a certregen module on the master**, if one is compatible with OpenVox 8. Not checked: the module's
  declared Puppet range needs reading on the Forge (hazard 1).
- **B (recommended): rewrite the check around `puppetserver ca list --all`**, OpenVox's CA tool, reading each
  certificate's expiry with openssl from the CA's signed directory. This keeps the same thresholds and output. It is a
  rewrite of the script's data source, so it changes the file.
- **C: read the CA's signed certificates directly with openssl** (no Puppet command). This is the smallest dependency
  surface, but it ties the check to the CA directory's layout.

Each changes the script, and they differ in approach, so this is not a policy-B fix. The run continues; the class's
behaviour state stays "finding" until HQ rules.

## Reproduced (2026-11-21)
Review 20261121T161208Z reproduced the finding. It also confirmed by hand that `puppet certregen` is an unknown
subcommand on the lab master puppet8master (openvox 8.24.2), as on the agent node and p8lab-puppetserver. The set passed
on purpose; the thresholds row stays uncovered until this is resolved.

## Ruled and fixed (2026-11-22)
HQ after batch 20, item 3: replace the missing certregen call with a direct read of the certificates' expiry dates,
keeping the thresholds and output (the escalation's option C). Local change #19. Before (20261122T213617Z): every fixture
case printed the certregen failure. After (20261122T214533Z): a 400-day certificate OK, 20 days Warning, 5 days
Critical, an expired one Critical. Phase 1 and Phase 3 reviews follow.
