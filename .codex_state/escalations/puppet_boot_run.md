# puppet_boot_run — upstream defect fixed locally (ruling 8)

Status: RULED (provisional ruling 8 applied: drop `ensure => running`, keep `enable => true`).
No intent conflict found (below), so no HQ stop. Recorded as "upstream defect fixed
locally". The class itself migrates later through the normal loop (it is drifted: baseline-sync first).

## Baseline content (release-0.9.10 = upstream cf477c6; identical at release-0.9.8)
`manifests/puppet_boot_run.pp` service block:
```puppet
    service { 'puppet_boot_run':
        ensure   => running,
        enable   => true,
        provider => 'systemd',
        require  => [
            File['/etc/systemd/system/puppet_boot_run.service'],
            Exec['Reload systemd'],
        ],
    }
```
`templates/etc/puppet_boot_run.service.erb` (byte-identical locally):
```ini
[Unit]
Description=Run puppet agent on boot
After=network.target

[Service]
Type=oneshot
ExecStart=<%= @boot_run_script %>
StandardOutput=journal

[Install]
WantedBy=multi-user.target
```
`files/etc/puppet_boot_run.sh` (baseline, from b17f0c0 "Issue #94: Made the puppet on boot script more
robust to avoid indefinite hangs", 2026-02-18) — abridged, full text at `cf477c6:files/etc/puppet_boot_run.sh`:
```bash
LOG=/tmp/puppet_boot_run.log
echo "Puppet boot-run started at: $(date -Is)" > "$LOG"
# 1) If another puppet run is already in progress, do NOT compete. Just exit cleanly.
LOCKFILE="$(/opt/puppetlabs/bin/puppet agent --configprint agent_catalog_run_lockfile)"
if [ -f "$LOCKFILE" ]; then echo "Another puppet run appears active ... Skipping boot run." >> "$LOG"; exit 0; fi
# 2) wait up to 120 s for apt/dpkg locks   # 3) timeout 900 puppet agent -t; always exit 0
```
Local copy is drifted: the manifest predates 4ae2e35 and the script predates b17f0c0 (the local script is
the 3-line original). Both are brought to baseline by a baseline-sync (step 4.1 / C3) before migration.

## Upstream commit 4ae2e35 (the one that added `ensure => running`)
```
commit 4ae2e350ed1f982da97217b96aa5cb8cc4eb7aba
Author: Gustavo Homem
Date:   2026-01-14 14:40:50 +0100

    make sure the puppet on boot mechanism works on Ubuntu 22.04
```
Diff: exec renamed to `Reload systemd`; service gains `ensure => running`, `provider => 'systemd'`
and `require => [File[unit], Exec['Reload systemd']]` (previously `enable => true` only).

## The defect
`Type=oneshot` without `RemainAfterExit=yes` goes `inactive (dead)` as soon as ExecStart exits, so
`systemctl is-active` reports inactive after every start. With `ensure => running` Puppet therefore
starts the unit on EVERY agent run (`ensure changed 'stopped' to 'running'`): never idempotent, and the
harness's run 2 fails (predicted from the unit semantics; to be confirmed by the first gate-v2 run).
Each such start runs the script inside an agent run: it finds the agent lockfile, exits 0, but first
truncates `/tmp/puppet_boot_run.log` — so in production every agent run overwrites the boot-run log.

## Intent check (why there is no conflict)
The commit message states the goal: the boot mechanism must WORK on Ubuntu 22.04 — i.e. the unit must be
installed, reloaded and enabled so it runs at boot. The parts of the diff that serve that goal are the
ordering (`require` on the unit file and the daemon-reload, so `enable` no longer races a unit systemd has
not loaded yet) and `provider => 'systemd'`. Boot-time execution comes from `enable => true`
(`WantedBy=multi-user.target`), not from `ensure`. Nothing in the message asks for the unit to be started
during an agent run, and the later b17f0c0 script deliberately makes such a start a no-op (lockfile
check). Starting a unit whose job is to run the agent from inside an agent run serves no purpose the
message names. `RemainAfterExit=yes` (the alternative) would make the unit report active forever after
its first start, which hides a failed boot run — so dropping `ensure` is the smaller change.

## Local fix applied at migration time (not now)
Remove the single line `ensure   => running,`; keep `enable => true`, `provider => 'systemd'` and the
`require` list unchanged. Header line: "upstream defect fixed locally: ensure => running dropped on a
oneshot unit (ruling 8, escalations/puppet_boot_run.md)". Marker: this is a deliberate divergence, so the
tracker line needs HQ's marker choice at checkpoint 1 (`[from: release-0.9.10]` would be false
provenance by the 2026-07-01 rules; `[reimplemented: ...]` overstates a one-line fix).

## Record (HQ 2026-10-27 production-facts ruling 2: fixed in infra_populi only; no upstream patch, no escalation)
Upstream fix suggestion: drop `ensure => running` from `puppet_boot_run` (or add `RemainAfterExit=yes`
if a "has it run since boot" signal is wanted). Affects every node with `$run_puppet_on_boot` (node_base).
