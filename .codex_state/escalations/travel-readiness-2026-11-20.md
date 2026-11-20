# Travel readiness (HQ 2026-11-20 item 4; Salatiel flies on the 23rd)

Status: ACCEPTED by HQ 2026-11-20, with three additions: `lab down` whenever a run stops to wait and `lab up` when
work resumes (CLAUDE.md, the skill); a battery guard (the sleep guard brings the lab down on battery below 25%, tested);
the six unused VMs stay (three are clone sources), and old snapshots and backup files stay until Salatiel decides —
nothing depends on deleting them. Was: WRITTEN 2026-11-20, for HQ review. The engine's part is done; Salatiel's part is listed below. All numbers were
measured on 2026-11-20.

## Checklist
| # | Item | State | Evidence |
|---|---|---|---|
| 1 | `lab down` and `lab up` built, with tests | done | `lab_power.sh` (91a9953), 9 tests; full suite 670 passed |
| 2 | `lab down` proven on the lab | done | 09:28:47Z: master off through ACPI, node powered off, guard released, 7.05 s |
| 3 | `lab up` proven on the lab | done | 09:29:09Z: master started, health and clock checked, node reverted, 62.27 s. Afterwards: 28 modules, none invalid (only the two known docker dependency warnings), NTP synchronised |
| 4 | Every node kind reverted once | done | REVERT_METRICS total_s: ubuntu 22.980, ubuntu2 21.827, kubuntu 22.936, gnome 18.414, dc 20.993, puppetserver 21.984, rhel9 77.790 (v1), 32.691 (v2). Each p8lab VM was stopped after its revert |
| 5 | rhel9 baseline refreshed to cut downloads | done | P8LAB_RHEL9_BASELINE_v2 (a63a3e97…, 6009ed9): v1 plus a fresh dnf cache, no agent run. One revert downloads 139,478 bytes from v2 against 325,727,007 from v1. Only rhel9 was refreshed: the Debian kinds pull about 13 MB of apt lists per revert, by design |
| 6 | A fresh master snapshot | done | P8MASTER_BASELINE_GREEN_v9 (b2195ab6…), taken by snapshot_master.sh at 09:36:35Z; the master was back with puppetserver active and 8140 running |
| 7 | Repo pushed | done | HEAD = origin/main with this file's commit |

Notes on the evidence:
- **Item 5:**
  - The 139,478 bytes hold while rhel9's repo metadata is fresh: `metadata_expire` is 86400 s. After that, dnf
    re-fetches only the repos whose metadata changed, so a revert from v2 never downloads more than one from v1.
  - The v2 snapshot description says "~09:33Z", which is not measured. The measured time is the boot at 09:32:46Z
    (`uptime -s`); the commit records that.
- **Lab state now:** the master and the ubuntu node are running, with the sleep guard held; every p8lab VM is off.

## On the road
- **Before closing the lid or shutting the laptop down:** run `.codex_state/tools/lab_power.sh down`. While any lab VM
  runs, the sleep guard blocks suspend.
- **To work again:** run `.codex_state/tools/lab_power.sh up`. It also reverts the node. Each p8lab kind is reverted
  when a run asks for it.
- **The VPN stays off for lab work.** NIC1 is NAT through whatever uplink the laptop has, so a new network needs no lab
  change.

## For Salatiel (the engine cannot do these: deleting snapshots and VMs is yours)
Disk is not tight: 751 GB free of 934 GB. Deleting is optional, and it is best done while the lab is down.
1. **Old baseline snapshots** that no tool restores any more:
   - **Master:** P8MASTER_BASELINE_GREEN, _v3, _v4, _v5, _v6 and _v7. My recommendation: keep v8 as the one fallback,
     with v9 current. The earlier chain ("Updated and Upgraded" through "Codex Setup Done") is pre-engine and yours to
     judge.
   - **ubuntu24-puppet8-Node:** P8NODE_BASELINE_GREEN_v2 and _v3. v4 is current. The pre-engine chain is yours to judge.
   - **p8lab-ubuntu2:** P8LAB_UBUNTU2_BASELINE_v1. v2 is current.
   - **p8lab-rhel9:** P8LAB_RHEL9_BASELINE_v1. My recommendation: keep it until a rhel9 class run has passed on v2.
2. **Backup files:**
   - Laptop:
     - `~/.local/bin/infra_populi_tools/test_class.sh.bak`, from Jul 26;
     - `~/.config/infra_populi/params/puppet_infrastructure::openvpn_server.json.bak.pre-dhcp-primary`;
     - `…::openvpn_server.json.bak.p8test2-local`;
     - `…::network_dhcp.json.bak.enp0s3`.

     The params files are local fixtures. Nothing in the engine reads the `.bak` copies.
   - Master:
     - `/etc/puppetlabs/code/environments/production/hiera.yaml.bak.20261027T054127`;
     - five copies of `/home/deployment/infra_populi_env/Puppetfile.bak.*`, dated 20260930 to 20261027.

     The master's root filesystem has 4.5 GB free of 12 GB.
   - Repo: `git stash@{0}`, "WIP on main: 887182d". Inspect it, then drop it.
3. **VMs the lab does not use:** Ubuntu24-test, RHEL9, Ubuntu24-puppet, Ubuntu22-puppet, ubuntu-desktop and
   kubuntu-desktop. Every p8lab VM is a full clone, so none of these is a running dependency. They are listed for your
   decision only.
4. **The KVM side of the 2026-11-19 crash** (escalations/lab-vm-crash-2026-11-19.md, option A): unload `kvm_intel` and
   `kvm` while the lab runs, if nothing on the laptop needs them. The sleep guard covers suspend, but not a resume after
   one forced by low battery.

## After HQ review
Batch 6 under the run rule, starting with user_kde_lock_screen (kubuntu).
