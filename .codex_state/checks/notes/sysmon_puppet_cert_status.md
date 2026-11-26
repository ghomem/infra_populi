# sysmon_puppet_cert_status: authoring notes (the comments of .codex_state/checks/sysmon_puppet_cert_status.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sysmon_puppet_cert_status (class; node ubuntu; required_base filesystem_base;
# required_external apt, sudo; no parameters, fixture defaults). It installs a Nagios check, meant for the Puppet
# master, that runs `puppet certregen healthcheck --all` and reports the earliest certificate expiry (OK above 30 days,
# Warning under 30, Critical under 10 or when one has expired), plus python3-yaml and a sudo rule for naemon.
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1). Measured before writing the
# health check: `puppet certregen` is an unknown subcommand on the OpenVox 8 agent node (puppet 8.24.2) and on the lab's
# master-role node p8lab-puppetserver (openvox-server, puppet 8.24.2, no certregen module), so the check prints
# "command ... failed" with exit 1 wherever it runs; escalations/sysmon_puppet_cert_status.behaviour.md.
# 2026-11-22 (HQ after batch 20, item 3): the checks now use fixture certificates in the CA's signed directory
# (/etc/puppetlabs/puppetserver/ca/signed, as on the OpenVox master): a 400-day one, then one expiring in 20 days,
# then 5 days, then one that expired on 2025-01-02 (made with `openssl ca` and explicit dates). Before evidence on the
# baseline script (certregen); after evidence on local change #19 (the expiry read from the certificates).
# 2026-11-22 (HQ ruling 2): the moved upstream comment "This runs the command ..." removed (listed in row #19); the
# script digest updated.
```
