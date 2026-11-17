"""first_contact.py (HQ 2026-11-17 batch-8 ruling 9): a new VM is first reached at the host-only address VirtualBox
leased to its own NIC2 MAC, never through a localhost port forward (Incus on the laptop holds 127.0.0.1:2222, so
kubuntu's forward never bound and the fingerprint quoted for kubuntu was Incus's)."""

import subprocess

import pytest

from conftest import TOOLS

SCRIPT = str(TOOLS / "first_contact.py")
KEY = "AAAAC3NzaC1lZDI1NTE5AAAAINoV8dBenY9M6Gdtitb91tViC4lRxDzUEirg7jPBUqXs"
LEASES = """<?xml version="1.0"?>
<Leases version="1.0">
  <Lease mac="08:00:27:45:35:05" id="01080027453505" network="0.0.0.0" state="expired">
    <Address value="192.168.56.103"/>
  </Lease>
  <Lease mac="08:00:27:e0:ed:8f" id="01080027e0ed8f" network="0.0.0.0" state="acked">
    <Address value="192.168.56.102"/>
  </Lease>
</Leases>
"""


@pytest.fixture
def fc(lab, tmp_path):
    lab.world["vms"]["p8lab-kubuntu"] = {"state": "running", "config": {
        "nic2": "hostonly", "hostonlyadapter2": "vboxnet0", "macaddress2": "080027E0ED8F",
        "Forwarding(0)": "p8tmpssh,tcp,127.0.0.1,2222,,22"}}
    (tmp_path / "leases.xml").write_text(LEASES)
    keyscan = lab.bin / "ssh-keyscan"  # answers only at the leased address
    keyscan.write_text(f'#!/usr/bin/env bash\necho "$*" >> "$(dirname "$0")/../keyscan.log"\n'
                       f'[[ "${{@: -1}}" == 192.168.56.102 ]] && echo "192.168.56.102 ssh-ed25519 {KEY}"\nexit 0\n')
    keyscan.chmod(0o755)
    known = tmp_path / "known_hosts"
    known.write_text("p8lab-kubuntu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFwrCZlLQf07kXibNSZBOREvVCCMX6L0ccEw/+zboYcp\n"
                     "p8lab-gnome ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEdqk5D1Z8tWx3Wb4MlQ1c0Kp0w4dIhq2sYb7b6m3vXq\n")
    env = {"P8_VBOX_LEASES": str(tmp_path / "leases.xml"), "P8_KNOWN_HOSTS": str(known)}

    class F:
        known_hosts = known

        def run(self, *args):
            return lab.run([SCRIPT, *args], env=env)

        def scanned(self):
            log = tmp_path / "keyscan.log"
            return log.read_text().split() if log.exists() else []
    return F()


def test_contact_goes_to_the_lease_of_the_vms_own_mac_never_a_localhost_port(fc):
    proc = fc.run("p8lab-kubuntu")
    assert proc.returncode == 0, proc.stderr
    assert "NIC2 MAC 080027E0ED8F leased 192.168.56.102" in proc.stdout
    expected = subprocess.run(["ssh-keygen", "-lf", "-"], input=f"x ssh-ed25519 {KEY}\n", capture_output=True,
                              text=True).stdout.split()[1]
    assert f"HOSTKEY ED25519 {expected}" in proc.stdout
    assert fc.scanned()[-1] == "192.168.56.102" and "127.0.0.1" not in fc.scanned()
    assert "-p " not in proc.stdout and "127.0.0.1" not in proc.stdout.split("FORWARD")[0]
    assert "ssh-copy-id -i ~/.ssh/id_ed25519_codex_puppet8.pub -o HostKeyAlias=p8lab-kubuntu salatiel@192.168.56.102" \
        in proc.stdout
    assert "visudo -cf /etc/sudoers.d/p8lab-salatiel" in proc.stdout


def test_a_port_forward_is_reported_with_its_removal_and_never_used(fc):
    proc = fc.run("p8lab-kubuntu")
    assert "FORWARD p8lab-kubuntu: p8tmpssh,tcp,127.0.0.1,2222,,22" in proc.stdout
    assert "lab_vm.sh modify p8lab-kubuntu --natpf1 delete p8tmpssh" in proc.stdout


def test_known_hosts_is_untouched_without_pin(fc):
    before = fc.known_hosts.read_text()
    fc.run("p8lab-kubuntu")
    assert fc.known_hosts.read_text() == before


def test_pin_replaces_only_the_aliases_entries_after_a_backup(fc):
    before = fc.known_hosts.read_text()
    proc = fc.run("p8lab-kubuntu", "--pin")
    assert proc.returncode == 0 and "PINNED 1 key(s) for p8lab-kubuntu" in proc.stdout
    lines = fc.known_hosts.read_text().splitlines()
    assert f"p8lab-kubuntu ssh-ed25519 {KEY}" in lines
    assert [l for l in lines if l.startswith("p8lab-kubuntu ")] == [f"p8lab-kubuntu ssh-ed25519 {KEY}"]
    assert any(l.startswith("p8lab-gnome ") for l in lines)
    assert fc.known_hosts.with_name("known_hosts.pre-p8lab-kubuntu").read_text() == before


@pytest.mark.parametrize("change,text", [
    (lambda vm: vm.update(state="poweroff"), "is poweroff"),
    (lambda vm: vm["config"].update(nic2="nat"), "no host-only NIC2"),
    (lambda vm: vm["config"].update(macaddress2="080027453505"), "no acked vboxnet0 lease"),  # only an expired one
    (lambda vm: vm["config"].update(macaddress2="080027AAAAAA"), "no acked vboxnet0 lease"),
])
def test_refusals(fc, lab, change, text):
    change(lab.world["vms"]["p8lab-kubuntu"])
    proc = fc.run("p8lab-kubuntu")
    assert proc.returncode == 1 and "FIRST_CONTACT REFUSED" in proc.stderr and text in proc.stderr
    assert fc.scanned() == []


def test_only_p8lab_vms(fc):
    proc = fc.run("ubuntu24-puppet8-Node")
    assert proc.returncode == 1 and "is not a p8lab-* VM" in proc.stderr


def test_nothing_answering_the_keyscan_is_refused(fc, lab):
    (lab.bin / "ssh-keyscan").write_text("#!/usr/bin/env bash\nexit 0\n")
    proc = fc.run("p8lab-kubuntu")
    assert proc.returncode == 1 and "nothing answered ssh-keyscan at 192.168.56.102" in proc.stderr


# --static: a clone of a lab node keeps that node's static host-only address and keys (p8lab-dc from puppet8node)
@pytest.fixture
def clone(lab, fc):
    lab.world["vms"]["p8lab-dc"] = {"state": "running", "config": {
        "nic2": "hostonly", "hostonlyadapter2": "vboxnet0", "macaddress2": "080027ABCDEF"}}
    lab.world["vms"]["ubuntu24-puppet8-Node"]["state"] = "poweroff"
    lab.world["ssh"].insert(0, {"match": r"cat /sys/class/net/\*/address",
                                "stdout": "00:00:00:00:00:00\n08:00:27:aa:bb:cc\n08:00:27:ab:cd:ef\n"})
    return fc


def test_static_contact_proves_the_clone_by_pinned_key_and_its_own_mac(clone, lab):
    proc = clone.run("p8lab-dc", "--static", "192.168.56.20")
    assert proc.returncode == 0, proc.stderr
    assert "static 192.168.56.20 (from puppet8node, whose VM is poweroff)" in proc.stdout
    (call,) = [c for c in lab.calls("ssh") if "cat /sys/class/net/*/address" in c]
    assert "StrictHostKeyChecking=yes" in call and "HostKeyAlias=puppet8node" in call and "salatiel@192.168.56.20" in call
    assert clone.scanned() == []  # nothing is keyscanned or quoted: the key is the one pinned for the node


def test_static_contact_refuses_while_the_nodes_vm_runs(clone, lab):
    lab.world["vms"]["ubuntu24-puppet8-Node"]["state"] = "running"
    proc = clone.run("p8lab-dc", "--static", "192.168.56.20")
    assert proc.returncode == 1 and "power it off first" in proc.stderr and lab.calls("ssh") == []


def test_static_contact_refuses_another_hosts_answer(clone, lab):
    lab.world["ssh"][0]["stdout"] = "08:00:27:aa:bb:cc\n"
    proc = clone.run("p8lab-dc", "--static", "192.168.56.20")
    assert proc.returncode == 1 and "does not hold p8lab-dc's NIC2 MAC 08:00:27:ab:cd:ef" in proc.stderr


def test_static_contact_needs_a_known_node_address(clone):
    proc = clone.run("p8lab-dc", "--static", "192.168.56.99")
    assert proc.returncode == 1 and "no node of nodes.yml has that host-only address" in proc.stderr
