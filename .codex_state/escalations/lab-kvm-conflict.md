# Lab down: the laptop's production Puppet run installed Incus/KVM; both lab VMs crashed (2026-11-16 21:36:57 UTC)

**Status: LAB DOWN, batch 6 not started (stop condition). Needs Salatiel: the laptop's production configuration and
the master's recovery are both outside the engine's authority.**

## What happened
- **21:31–21:37** the laptop's own puppet-agent (production master; the laptop is a production Puppet 5 node) applied
  its catalog, including:
  - `Meaningful_puppet::Meaningful_desktop`: among other changes, `File[/etc/hosts]` content changed;
  - `Meaningful_puppet::Meaningful_virtualization`: dpkg installed qemu-system-*, ovmf and qemu-utils at 21:36:40–41,
    then `Package[incus]` ensure created and `Service[incus.socket]` refreshed at 21:36:57.
- **21:36:57.73** both lab VMs entered VirtualBox `gurumeditation`, 6 ms apart:
  `VCPU1: Guru Meditation -4004 (VERR_VMX_INVALID_VMXON_PTR)` (node VBox.log:2069; the master's log shows the same
  block). This is VirtualBox losing VT-x to another hypervisor.
- **Now:**
  - `kvm_intel` is loaded and in use (refcount 1);
  - `incus` and `incus.socket` are active;
  - `vhost_vsock` is loaded and `incusbr0` exists;
  - p8lab-rhel9 was powered off and is unaffected.

## What I did and did not do
- **Nothing on the laptop's configuration:** it is a production node; its Puppet agent and its packages are
  Salatiel's.
- **Nothing to the VMs:** the master is in `gurumeditation`, and the only exit from that state is a power-off, which
  the master rules forbid me. I can power off the node, but it would crash again while KVM holds VT-x.
- **Batch 6:** not started. extra_packages_el (unblocked and routed to rhel9 per HQ ruling 5) was at pregate; the
  hazard-5 routing change is committed (9294edb). Pregate's master batch failed with "No route to host" because the
  master was down.

## What is needed (Salatiel)
1. **Free VT-x for VirtualBox** on the laptop while the lab runs. For example:
   - stop `incus.service` and `incus.socket` and unload `kvm_intel` and `kvm`;
   - or have the production catalog not apply `Meaningful_virtualization` to this laptop;
   - or decide how VirtualBox and Incus/KVM coexist here.

   As long as the production agent stays active, its next run (every 30 min) will put it back unless the catalog
   changes.
2. **Recover the master:** power off `Ubuntu24-puppet8-Master` from `gurumeditation` (it is not running; no ACPI path
   exists from this state), then start it.
   - Its disk state is that of a crashed VM. Snapshot v5 (taken 17:44 today, before this) is the known-good state,
     and restoring it is Salatiel's call (the master rule says never restore).
   - What changed on the master after v5 (17:44):
     - the p8lab-rhel9 cert, signed at 18:16, and its node file `nodes/p8lab-rhel9.pp`;
     - the rsyslog Hiera fixture (19:26, `master_fixtures.sh hiera`, idempotent).

     A restore to v5 would need both re-done.
3. **The node:** a power-off and a revert to v4 (my tools can do this once VT-x is free).
4. **The laptop's `/etc/hosts`** was rewritten by the same run. The lab aliases use IP addresses (HostName), so lab
   SSH does not depend on it. Noted only.

## After recovery (advisor)
- Health checks: the master's puppetserver and 8140; the CA still holds the p8lab-rhel9 cert and node file (re-sign
  and re-add them if the master is restored to v5); the Hiera fixture (re-run `master_fixtures.sh hiera`).
- One revert of each node, then batch 6 resumes at extra_packages_el.

## Resolution (2026-11-16 21:50–22:00 UTC)
- **Trigger** (Salatiel): his VPN was on, so the laptop's production agent reached its master and applied the
  virtualization class.
- **Incus stopped** (Salatiel: `systemctl stop incus.service incus.socket`). `modprobe -r kvm_intel` refused (refcount
  1), but no process held `/dev/kvm` (`fuser`/`lsof` empty) and `kvm.enable_virt_at_load = N`. So VT-x is only taken
  while a KVM VM exists: Incus's first-start VM-support probe took it at 21:36:57, long enough to crash both
  VirtualBox VMs.
- **VT-x proven free:** p8lab-rhel9 started through lab_vm.sh, booted and answered SSH, then was stopped.
- **Master** (Salatiel): power-off from `gurumeditation`, start; no restore.
  - Health after boot: puppetserver active, 8140 `running`, enp0s8 .10, NIC1 NAT.
  - Nothing lost: CA certs for puppet8node and p8lab-rhel9, both node files, the Hiera fixture, `puppet module list`
    with no invalid module, root fs mounted.
- **Node:** revert to v4 SUCCESS; compile-only OK.
- **Standing caution:** with the VPN on, the laptop's production agent can start Incus again; lab work runs with the
  VPN off, or pauses.
