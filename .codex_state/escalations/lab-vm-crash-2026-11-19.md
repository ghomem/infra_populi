# Lab VMs crashed on a laptop resume (2026-11-19 20:38Z)

Status: OPEN, for Salatiel. Lab runs are on hold. Recovering a VM in this state needs a power-off, which for the master
is Salatiel's alone (CLAUDE.md: the master is never hard-powered off by the engine; raw mutating VBoxManage is denied).

## Evidence (read-only, 2026-11-19 21:31Z)
- **State:** both VMs, Ubuntu24-puppet8-Master and ubuntu24-puppet8-Node, are in VirtualBox state `gurumeditation`
  since 2026-11-19T20:38:08Z (VBoxManage showvminfo).
- **The master's VBox.log:** "Changing the VM state from 'RUNNING' to 'GURU_MEDITATION'", then
  "VCPU1: Guru Meditation -4004 (VERR_VMX_INVALID_VMXON_PTR)".
- **The laptop suspended just before:**
  - its journal shows a suspend entered at 20:35:48 (local time is UTC: "System returned from sleep operation
    'suspend'");
  - both VMs failed at the same second, 20:38:08, on resume;
  - the laptop itself did not reboot (up since 2026-10-04).
- **KVM is loaded beside VirtualBox:** `lsmod` lists kvm_intel and kvm next to vboxdrv. No qemu, libvirt or other
  hypervisor process is running. VERR_VMX_INVALID_VMXON_PTR is VirtualBox finding the CPU's VMX state not its own,
  which a resume with KVM loaded can cause. That is inferred from the error and the timing, not reproduced.
- **No lab run was active.** The suspend fell while the tool test suite ran on the laptop. The phase3 runner's sleep
  inhibitor (2026-11-17) covers only lab runs, not the gaps between them.

## What was in flight
- Nothing on the VMs.
- Committed and pushed:
  - HQ batch-15 rulings 2 (the review gate for local changes) and 3 (the validator rule);
  - their records.
- **Not started:** rulings 5 (ifupdown for network_dhcp/static) and 6 (named IPv4-only without a global IPv6
  address). Both need the lab.

## To resume (Salatiel)
1. Power the two VMs off (VirtualBox GUI, or `VBoxManage controlvm <vm> poweroff`). Raw mutating VBoxManage is
   human-only here.
2. Then the engine's `revert_node.sh` starts a stopped master (start only) and restores the node. Or start the master
   by hand.
3. Then `snapshot_master.sh` is not needed; the master boots from its disk as it was.

## To prevent it (Salatiel's machine, options)
- **A.** Unload KVM while the lab is in use (`sudo modprobe -r kvm_intel kvm`), if nothing on the laptop needs it.
- **B.** Inhibit suspend for as long as lab VMs run, not only during runs. That would be an engine change: a lab-wide
  inhibitor started with the master.
- **C.** Disable suspend on lid close or idle while working on the lab.

Recommended: A if KVM is unused, else B.
