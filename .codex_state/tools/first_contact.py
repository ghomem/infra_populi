#!/usr/bin/env python3
"""First contact with a new lab VM over its own host-only lease (HQ 2026-11-17 batch-8 ruling 9).

kubuntu's bring-up went through a 127.0.0.1:2222 NAT port forward, but Incus on the laptop already held that port:
the forward never bound, every attempt reached Incus, and the host key quoted for kubuntu was Incus's. So a new VM is
first reached at the address VirtualBox's vboxnet0 DHCP server leased to THAT VM's NIC2 MAC, never at a localhost port,
and no fingerprint taken through a forwarded port is ever quoted.

    first_contact.py <p8lab-vm> [--alias NAME] [--user USER] [--pin]

- Reads the VM's NIC2 (host-only, vboxnet0) MAC from VBoxManage and its acked lease from the vboxnet0 DHCP lease file.
- Keyscans that address and prints each host key's fingerprint, for Salatiel to compare with the VM's console
  (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) before anything trusts it.
- Prints the key-install and sudo commands for that address, with HostKeyAlias <alias> (default: the VM name).
- --pin (only after the console comparison): writes the scanned keys to ~/.ssh/known_hosts under the alias, replacing
  that alias's earlier entries, after a backup known_hosts.pre-<vm>.
- A NAT port forward on the VM is reported (FORWARD) with the command that removes it once the VM is powered off.

Exit 0 done, 1 refused (not a running p8lab-* VM, no host-only NIC2, no acked lease, nothing answered the keyscan),
2 usage. P8_VBOX_LEASES overrides the lease file and P8_KNOWN_HOSTS the known_hosts file (tests).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

LEASES = Path(os.environ.get("P8_VBOX_LEASES",
                             Path.home() / ".config/VirtualBox/HostInterfaceNetworking-vboxnet0-Dhcpd.leases"))
KNOWN_HOSTS = Path(os.environ.get("P8_KNOWN_HOSTS", Path.home() / ".ssh/known_hosts"))
HOSTONLY_NET = "192.168.56."
IDENTITY = "~/.ssh/id_ed25519_codex_puppet8"


def refuse(msg):
    print(f"FIRST_CONTACT REFUSED: {msg}", file=sys.stderr)
    sys.exit(1)


def vm_info(vm):
    proc = subprocess.run(["VBoxManage", "showvminfo", vm, "--machinereadable"], capture_output=True, text=True)
    if proc.returncode != 0:
        refuse(f"no VM named '{vm}'")
    info = {}
    for line in proc.stdout.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            info[key] = value.strip('"')
    return info


def leased_address(mac):
    """The acked vboxnet0 lease of this MAC (12 hex digits, any case), or None."""
    want = ":".join(mac.lower()[i:i + 2] for i in range(0, 12, 2))
    try:
        root = ET.parse(LEASES).getroot()
    except (OSError, ET.ParseError) as exc:
        refuse(f"cannot read the vboxnet0 DHCP leases {LEASES}: {exc}")
    for lease in root.iter("Lease"):
        if lease.get("mac", "").lower() == want and lease.get("state") == "acked":
            addr = lease.find("Address")
            if addr is not None and addr.get("value", "").startswith(HOSTONLY_NET):
                return addr.get("value")
    return None


def keyscan(address):
    proc = subprocess.run(["ssh-keyscan", "-T", "5", address], capture_output=True, text=True)
    return [line for line in proc.stdout.splitlines() if line and not line.startswith("#")]


def fingerprint(key_line):
    proc = subprocess.run(["ssh-keygen", "-lf", "-"], input=key_line + "\n", capture_output=True, text=True)
    parts = proc.stdout.split()
    return f"{parts[-1].strip('()')} {parts[1]}" if proc.returncode == 0 and len(parts) >= 2 else "unreadable"


def pin(vm, alias, keys):
    KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
    if KNOWN_HOSTS.exists():
        shutil.copy2(KNOWN_HOSTS, KNOWN_HOSTS.with_name(f"{KNOWN_HOSTS.name}.pre-{vm}"))
        subprocess.run(["ssh-keygen", "-R", alias, "-f", str(KNOWN_HOSTS)], capture_output=True)
    with KNOWN_HOSTS.open("a") as f:
        for line in keys:
            _, keytype, blob = line.split()[:3]
            f.write(f"{alias} {keytype} {blob}\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("vm")
    ap.add_argument("--alias")
    ap.add_argument("--user", default="salatiel")
    ap.add_argument("--pin", action="store_true")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"p8lab-[a-z0-9][a-z0-9-]{0,40}", args.vm):
        refuse(f"'{args.vm}' is not a p8lab-* VM")
    alias = args.alias or args.vm
    info = vm_info(args.vm)
    if info.get("VMState") != "running":
        refuse(f"'{args.vm}' is {info.get('VMState', 'unknown')}; start it (lab_vm.sh start) and let it boot first")
    if info.get("nic2") != "hostonly" or info.get("hostonlyadapter2") != "vboxnet0":
        refuse(f"'{args.vm}' has no host-only NIC2 on vboxnet0 (HQ NAT review G: lab_vm.sh modify ... --nic2 hostonly)")
    mac = info.get("macaddress2", "")
    if not re.fullmatch(r"[0-9A-Fa-f]{12}", mac):
        refuse(f"cannot read the NIC2 MAC of '{args.vm}'")
    address = leased_address(mac)
    if address is None:
        refuse(f"no acked vboxnet0 lease for '{args.vm}' (NIC2 MAC {mac}); the guest has not taken a DHCP address on "
               f"its host-only NIC yet (a static guest address is set at bring-up, after first contact)")
    for key, value in sorted(info.items()):
        if key.startswith("Forwarding("):
            name = value.split(",")[0]
            print(f"FORWARD {args.vm}: {value} — never used for contact; remove it while the VM is powered off: "
                  f"lab_vm.sh modify {args.vm} --natpf1 delete {name}")
    keys = keyscan(address)
    if not keys:
        refuse(f"nothing answered ssh-keyscan at {address} (sshd not running yet?)")
    print(f"FIRST_CONTACT {args.vm}: NIC2 MAC {mac} leased {address} by vboxnet0's DHCP server")
    for line in keys:
        print(f"HOSTKEY {fingerprint(line)}")
    print("Compare with the VM's console before trusting it: ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub")
    target = f"{args.user}@{address}"
    print("For Salatiel, after the fingerprint matches (the first asks the account's password, the second sudo's):")
    print(f"  ssh-copy-id -i {IDENTITY}.pub -o HostKeyAlias={alias} {target}")
    print(f"  ssh -t -o HostKeyAlias={alias} {target} 'echo \"{args.user} ALL=(ALL) NOPASSWD:ALL\" | "
          f"sudo tee /etc/sudoers.d/p8lab-{args.user} >/dev/null && sudo chmod 0440 /etc/sudoers.d/p8lab-{args.user} "
          f"&& sudo visudo -cf /etc/sudoers.d/p8lab-{args.user}'")
    if args.pin:
        pin(args.vm, alias, keys)
        print(f"PINNED {len(keys)} key(s) for {alias} in {KNOWN_HOSTS} (backup {KNOWN_HOSTS.name}.pre-{args.vm})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
