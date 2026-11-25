#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TRACKED TOOLING (HQ 2026-11-16 item 3). Guarded VM operations for NEW lab VMs, the counterpart of
# snapshot_master.sh: it acts ONLY on VMs named p8lab-*. Raw mutating VBoxManage stays denied; the master and
# ubuntu24-puppet8-Node keep their own rules (snapshot_master.sh, revert_node.sh).
#
#   lab_vm.sh clone <source> <p8lab-name> [--snapshot <source snapshot>]
#       full clone of an existing VM into a new p8lab-* VM. The source is never modified: it must be powered off,
#       or be cloned from one of its named snapshots; its configuration and snapshot list are compared before and
#       after. Never the master as a source. The clone gets the lab's paravirt provider (nodes.yml, HQ 2026-11-24).
#   lab_vm.sh modify <p8lab-name> <modifyvm options...>   powered-off VM only; a --name must stay p8lab-*; no NAT
#                                    port forward may be added (--natpfN delete only; first contact: first_contact.py);
#                                    a paravirt provider other than the lab's is refused
#   lab_vm.sh start <p8lab-name>     headless; refused if it would leave under 4 GB free on the laptop
#                                    (MemAvailable minus the VM's memory), or unless the VM has the lab network:
#                                    NIC1 NAT with the host resolver, NIC2 host-only vboxnet0 (HQ NAT review G)
#   lab_vm.sh stop <p8lab-name> [--hard]   ACPI with a timeout (default), or a hard poweroff
#   lab_vm.sh pause <p8lab-name> <seconds>  pause a running VM for 1-3600 s, then resume it (resumed on any exit): what a
#                                    laptop suspend does to a VM, for testing a guest's clock recovery (HQ 2026-11-17)
#   lab_vm.sh snapshot <p8lab-name> take <NAME> [--description TEXT]   powered-off VM only (offline snapshots)
#   lab_vm.sh snapshot <p8lab-name> restore <NAME>                      powered-off VM only
#
# There is no delete: deleting a VM or a baseline snapshot stays Salatiel's. Exit 0 done, 1 refused (nothing
# changed), 2 usage. P8_MEMINFO overrides /proc/meminfo (tests).
# ---------------------------------------------------------------------------
set -euo pipefail

readonly MASTER_VM="Ubuntu24-puppet8-Master"
readonly MIN_FREE_MB=4096
readonly ACPI_TIMEOUT_SECONDS="${ACPI_TIMEOUT_SECONDS:-180}"
MEMINFO="${P8_MEMINFO:-/proc/meminfo}"
TOOLS_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
# HQ 2026-11-24: the lab's paravirtualization provider (nodes.yml `paravirt_provider`), set on every clone.
lab_provider() { python3 "${TOOLS_DIR}/nodes.py" provider; }

refuse() { echo "LAB_VM REFUSED: $*" >&2; exit 1; }
usage() { sed -n '5,24p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

lab_name() { [[ "$1" =~ ^p8lab-[a-z0-9][a-z0-9-]{0,40}$ ]]; }
vm_exists() { VBoxManage showvminfo "$1" --machinereadable >/dev/null 2>&1; }
vm_state() { VBoxManage showvminfo "$1" --machinereadable | sed -n 's/^VMState="\(.*\)"$/\1/p'; }
vm_memory_mb() { VBoxManage showvminfo "$1" --machinereadable | sed -n 's/^memory=\([0-9]*\)$/\1/p'; }
snapshot_names() { VBoxManage snapshot "$1" list --machinereadable 2>/dev/null | sed -n 's/^SnapshotName[-0-9]*="\(.*\)"$/\1/p'; }
has_snapshot() { snapshot_names "$1" | grep -qxF "$2"; }
# The source's identity for the never-modified check: its configuration (minus run-time state) and snapshots.
fingerprint() {
  { VBoxManage showvminfo "$1" --machinereadable | grep -vE '^(VMState|VMStateChangeTime|GuestOSType|SessionName|SessionPid)=' || true
    snapshot_names "$1"; } | sha256sum | cut -d' ' -f1
}
target() {
  lab_name "$1" || refuse "'$1' is not a p8lab-* VM; lab_vm.sh acts on p8lab-* VMs only"
  vm_exists "$1" || refuse "no VM named '$1'"
}
# HQ NAT review G: every lab VM runs on the lab network, NIC1 VirtualBox NAT with the host resolver
# (natdnshostresolver1 on) and NIC2 host-only on vboxnet0. showvminfo does not print the host-resolver flag, so it is
# read from the VM's .vbox file: the current machine's adapter 0, not a snapshot's. Prints what is wrong.
lab_network_problem() {
  local info cfg
  info="$(VBoxManage showvminfo "$1" --machinereadable)"
  grep -qx 'nic1="nat"' <<<"$info" || { echo "NIC1 is not NAT"; return 0; }
  { grep -qx 'nic2="hostonly"' <<<"$info" && grep -qx 'hostonlyadapter2="vboxnet0"' <<<"$info"; } ||
    { echo "NIC2 is not host-only on vboxnet0"; return 0; }
  cfg="$(sed -n 's/^CfgFile="\(.*\)"$/\1/p' <<<"$info")"
  python3 - "$cfg" <<'PY' 2>/dev/null || echo "NIC1 NAT does not use the host resolver (natdnshostresolver1 on), or ${cfg:-the .vbox file} is unreadable"
import sys
import xml.etree.ElementTree as ET
dns = ET.parse(sys.argv[1]).getroot().find("./{*}Machine/{*}Hardware/{*}Network/{*}Adapter[@slot='0']/{*}NAT/{*}DNS")
sys.exit(0 if dns is not None and dns.get("use-host-resolver") == "true" else 1)
PY
}
powered_off() { [[ "$(vm_state "$1")" == "poweroff" || "$(vm_state "$1")" == "aborted" ]]; }

[[ $# -ge 1 ]] || usage
verb="$1"; shift
case "$verb" in
  clone)
    [[ $# -eq 2 || ( $# -eq 4 && "$3" == "--snapshot" ) ]] || usage
    src="$1" name="$2" snap="${4:-}"
    lab_name "$name" || refuse "the clone must be named p8lab-* (got '$name')"
    [[ "$src" != "$MASTER_VM" ]] || refuse "the master is never a clone source"
    vm_exists "$src" || refuse "no source VM named '$src'"
    ! vm_exists "$name" || refuse "a VM named '$name' already exists"
    if [[ -n "$snap" ]]; then
      has_snapshot "$src" "$snap" || refuse "source '$src' has no snapshot '$snap'"
    else
      powered_off "$src" || refuse "source '$src' is $(vm_state "$src"): clone a powered-off source or one of its snapshots (--snapshot), so the source is never modified"
    fi
    before="$(fingerprint "$src")"
    VBoxManage clonevm "$src" ${snap:+--snapshot "$snap"} --name "$name" --mode machine --register ||
      refuse "VBoxManage clonevm failed"
    after="$(fingerprint "$src")"
    [[ "$before" == "$after" ]] || { echo "LAB_VM ERROR: the source '$src' changed during the clone (configuration or snapshots); stop and report" >&2; exit 3; }
    provider="$(lab_provider)" || refuse "cloned ${name}, but the inventory names no paravirt provider; set it before any start"
    VBoxManage modifyvm "$name" --paravirtprovider "$provider" ||
      refuse "cloned ${name}, but could not set paravirt provider ${provider}; set it before any start"
    echo "LAB_VM cloned ${src}${snap:+ (snapshot ${snap})} -> ${name}; source unchanged; paravirt provider ${provider}"
    ;;
  modify)
    [[ $# -ge 2 ]] || usage
    name="$1"; shift
    target "$name"
    powered_off "$name" || refuse "'$name' is $(vm_state "$name"); modify a powered-off VM only"
    args=("$@")
    for i in "${!args[@]}"; do
      if [[ "${args[$i]}" == "--name" ]]; then
        lab_name "${args[$((i + 1))]:-}" || refuse "--name must stay p8lab-* (got '${args[$((i + 1))]:-}')"
      fi
      # HQ 2026-11-17 batch-8 ruling 9: no NAT port forwards (a localhost port can be someone else's: Incus holds 2222).
      # First contact goes over the VM's host-only lease (first_contact.py); removing a forward stays allowed.
      if [[ "${args[$i]}" =~ ^--natpf[0-9]+$ && "${args[$((i + 1))]:-}" != "delete" ]]; then
        refuse "no NAT port forwards on lab VMs (${args[$i]} ${args[$((i + 1))]:-}); reach a new VM with first_contact.py"
      fi
      # HQ 2026-11-24: every lab VM stays on the lab's paravirt provider (the clock drifted under the default one).
      if [[ "${args[$i]}" == "--paravirtprovider" || "${args[$i]}" == "--paravirt-provider" ]] &&
        [[ "${args[$((i + 1))]:-}" != "$(lab_provider)" ]]; then
        refuse "paravirt provider '${args[$((i + 1))]:-}' is not the lab's '$(lab_provider)' (nodes.yml)"
      fi
    done
    VBoxManage modifyvm "$name" "$@" || refuse "VBoxManage modifyvm failed"
    echo "LAB_VM modified ${name}: $*"
    ;;
  start)
    [[ $# -eq 1 ]] || usage
    name="$1"
    target "$name"
    [[ "$(vm_state "$name")" != "running" ]] || { echo "LAB_VM ${name} already running"; exit 0; }
    problem="$(lab_network_problem "$name")"
    [[ -z "$problem" ]] || refuse "'$name' does not have the lab network: ${problem}. Set it with: lab_vm.sh modify ${name} --nic1 nat --natdnshostresolver1 on --nic2 hostonly --hostonlyadapter2 vboxnet0"
    avail_kb="$(awk '/^MemAvailable:/ {print $2}' "$MEMINFO")"
    [[ "$avail_kb" =~ ^[0-9]+$ ]] || refuse "cannot read MemAvailable from ${MEMINFO}"
    vm_mb="$(vm_memory_mb "$name")"
    [[ "$vm_mb" =~ ^[0-9]+$ ]] || refuse "cannot read the memory of '$name'"
    left_mb=$((avail_kb / 1024 - vm_mb))
    ((left_mb >= MIN_FREE_MB)) ||
      refuse "starting '$name' (${vm_mb} MB) would leave ${left_mb} MB free on the laptop; the floor is ${MIN_FREE_MB} MB"
    VBoxManage startvm "$name" --type headless || refuse "VBoxManage startvm failed"
    # Sleep is blocked for as long as a lab VM runs (2026-11-19); without logind's inhibitor this only warns.
    "$(dirname "$(readlink -f "$0")")/lab_sleep_guard.sh" ensure || echo "WARNING: the lab sleep guard did not start" >&2
    echo "LAB_VM started ${name} (${left_mb} MB left free)"
    ;;
  stop)
    [[ $# -ge 1 && $# -le 2 ]] || usage
    name="$1" hard="${2:-}"
    [[ -z "$hard" || "$hard" == "--hard" ]] || usage
    target "$name"
    ! powered_off "$name" || { echo "LAB_VM ${name} already powered off"; exit 0; }
    if [[ "$hard" == "--hard" ]]; then
      VBoxManage controlvm "$name" poweroff || refuse "VBoxManage controlvm poweroff failed"
    else
      VBoxManage controlvm "$name" acpipowerbutton || refuse "VBoxManage controlvm acpipowerbutton failed"
      waited=0
      until powered_off "$name"; do
        ((waited < ACPI_TIMEOUT_SECONDS)) || refuse "'$name' did not power off within ${ACPI_TIMEOUT_SECONDS}s (use --hard)"
        sleep 3; waited=$((waited + 3))
      done
    fi
    echo "LAB_VM stopped ${name}"
    ;;
  pause)
    [[ $# -eq 2 && "$2" =~ ^[0-9]+$ ]] || usage
    name="$1" seconds="$2"
    target "$name"
    ((seconds >= 1 && seconds <= 3600)) || refuse "pause between 1 and 3600 seconds (got ${seconds})"
    [[ "$(vm_state "$name")" == "running" ]] || refuse "'$name' is $(vm_state "$name"); pause a running VM only"
    VBoxManage controlvm "$name" pause || refuse "VBoxManage controlvm pause failed"
    trap 'VBoxManage controlvm "$name" resume' EXIT
    sleep "$seconds"
    trap - EXIT
    VBoxManage controlvm "$name" resume || { echo "LAB_VM ERROR: '$name' did not resume; resume it by hand" >&2; exit 3; }
    echo "LAB_VM paused ${name} for ${seconds}s and resumed it"
    ;;
  snapshot)
    [[ $# -ge 3 ]] || usage
    name="$1" action="$2" snap="$3"; shift 3
    target "$name"
    [[ "$snap" =~ ^[A-Za-z0-9_.-]+$ ]] || refuse "snapshot name '$snap' must match [A-Za-z0-9_.-]+"
    powered_off "$name" || refuse "'$name' is $(vm_state "$name"); snapshots are taken and restored offline only"
    case "$action" in
      take)
        ! has_snapshot "$name" "$snap" || refuse "'$name' already has a snapshot '$snap'"
        [[ $# -eq 0 || ( $# -eq 2 && "$1" == "--description" ) ]] || usage
        VBoxManage snapshot "$name" take "$snap" ${2:+--description "$2"} || refuse "VBoxManage snapshot take failed"
        echo "LAB_VM snapshot ${name}: took ${snap}"
        ;;
      restore)
        [[ $# -eq 0 ]] || usage
        has_snapshot "$name" "$snap" || refuse "'$name' has no snapshot '$snap'"
        VBoxManage snapshot "$name" restore "$snap" || refuse "VBoxManage snapshot restore failed"
        echo "LAB_VM snapshot ${name}: restored ${snap}"
        ;;
      *) refuse "snapshot action '$action' is not allowed (take|restore; deleting a snapshot stays Salatiel's)" ;;
    esac
    ;;
  delete | unregister | unregistervm)
    refuse "deleting a VM stays Salatiel's"
    ;;
  *) usage ;;
esac
