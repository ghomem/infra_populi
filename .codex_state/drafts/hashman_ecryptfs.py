"""Draft (HQ 2026-11-27 item 4, "use the same fixture for hashman_base's ecryptfs row if it fits"): the administrator
stores a user's ecryptfs data with the CLI (setecryptfs), the client applies printinfo's encrypted-home declaration
(user_desktop, ignorekey true) and gets the wrapped passphrase, which opens the user's encrypted home there.

The same throwaway material as user_base's ecryptfs variant: the wrapped passphrase and Private.sig of
spec/behaviour/fixtures/throwaway, and an encrypted home made with the same two passphrases. The client must be a
desktop (user_desktop declares user_kde_lock_screen, which runs KDE's tools as the user), so the peer moves from
ubuntu2 to kubuntu; it gets the encrypted home in its setup, before the clean phase, as a laptop has it before Puppet
manages the user (printinfo's declaration carries nothing that makes one)."""
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".codex_state" / "tools"))
import behaviour_move as bm  # noqa: E402

P = REPO / "spec" / "behaviour" / "checks" / "hashman_base.yml"
E = "/home/.ecryptfs/p8testuser/.ecryptfs"
NODEDEF = "/etc/puppetlabs/code/environments/production/manifests/nodes/p8test-hashman-client.pp"
IFACE = "templates/hashman/libhashman/interface.py.erb"
REFS = [
    {"path": "templates/hashman/pp_auth.py.erb", "lines": "370", "text": "if case('setecryptfs'):"},
    {"path": "templates/hashman/pp_auth.py.erb", "lines": "380", "text": "rc = setecryptfs( username, ppsigs, ppwrapped )"},
    {"path": "templates/hashman/libhashman/dbutils.py.erb", "lines": "419",
     "text": "rc2 = setent( username, idx2, ppwrapped, DBFILE_PPWRAPPED )"},
    {"path": IFACE, "lines": "363", "text": "str_base    = '  puppet_infrastructure::user_desktop        { \\''"},
    {"path": IFACE, "lines": "369", "text": "str_extra += 'ignorekey => true' + ', '"},
    {"path": IFACE, "lines": "371", "text": "str_extra += 'myppwrapped => $::' + username + SUFFIX_PPWRAPPED + ', '"},
]
CLIENT_REFS = REFS[3:] + [
    {"path": "manifests/user_base.pp", "lines": "119", "text": 'file { "${ecryptdir}/wrapped-passphrase.b64":'},
    {"path": "manifests/user_base.pp", "lines": "129",
     "text": 'command => "cat ${ecryptdir}/wrapped-passphrase.b64 |base64 -d > ${ecryptdir}/wrapped-passphrase",'},
]
SETUP = """set -e
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -q ecryptfs-utils pamtester > /dev/null  # pamtester: the base checks' PAM probe (ubuntu2 has it)
# p8testuser with an encrypted home, as `adduser --encrypt-home` makes it (the throwaway passphrases of
# spec/behaviour/fixtures/throwaway, as node fixture p8test_ecryptfs_home uses them), at rest
useradd -m -s /bin/bash p8testuser
skel=$(mktemp -d)
cp -a /home/p8testuser/. "$skel/"
find /home/p8testuser -mindepth 1 -delete
ecryptfs-setup-private --bootstrap -u p8testuser -l 'p8test-user-not-a-secret' -m 'p8test-mount-not-a-secret' --nopwcheck > /dev/null
cp -a "$skel/." /home/p8testuser/
chown -R p8testuser: /home/p8testuser
rm -rf "$skel"
umount /home/p8testuser
"""
ADMIN_ADD = """$c useradd p8testuser p8testuser@example.invalid "P8test Encrypted" p8test SILENT > /dev/null 2>&1
$c setecryptfs p8testuser '{{FIXTURE_B64:p8test-throwaway-private-sig}}' '{{FIXTURE_B64:p8test-throwaway-wrapped-passphrase}}' > /dev/null 2>&1
"""
OLD_NODEDEF = """{ echo "node 'p8test-hashman-client' {"; for u in p8hashuser p8hashlocked p8hashexpired; do $c printinfo $u 2>/dev/null | grep -E '^  infra_populi::user +[{]'; done; echo "}"; }"""
NEW_NODEDEF = """{ echo "node 'p8test-hashman-client' {"; for u in p8hashuser p8hashlocked p8hashexpired; do $c printinfo $u 2>/dev/null | grep -E '^  infra_populi::user +[{]'; done; $c printinfo p8testuser 2>/dev/null | grep -E '^  infra_populi::user_desktop +[{]'; echo "}"; }"""
MOUNT = ("install -d -m 0700 /run/p8test-ecr\n"
         f"printf '%s' 'p8test-user-not-a-secret' | ecryptfs-unwrap-passphrase {E}/wrapped-passphrase - "
         "> /run/p8test-ecr.pp 2>/dev/null\n"
         "keyctl session - sh -c 'keyctl link @u @s; ecryptfs-add-passphrase --fnek - < /run/p8test-ecr.pp "
         f">/dev/null; s=$(head -1 {E}/Private.sig); f=$(tail -1 {E}/Private.sig); "
         "mount -i -t ecryptfs -o ro,ecryptfs_sig=$s,ecryptfs_fnek_sig=$f,ecryptfs_cipher=aes,ecryptfs_key_bytes=16 "
         "/home/.ecryptfs/p8testuser/.Private /run/p8test-ecr && { test -s /run/p8test-ecr/.profile && "
         "echo home-readable; umount /run/p8test-ecr; }' > /run/p8test-ecr.out 2>/dev/null\n"
         "rm -f /run/p8test-ecr.pp\n")
NEW_CHECKS = [
    {"id": "a-client-gets-the-encrypted-home-data",
     "what": "after its agent run, the client has p8testuser's wrapped passphrase as the administrator stored it "
             "(setecryptfs), base64 in the user's ecryptfs directory and decoded beside it, and no authorized key "
             "(printinfo's encrypted-home form sets ignorekey)",
     "control": "negative", "host": "peer",
     "mutates": "none beyond reading the files (declared mutating so it runs after the peer's agent run)",
     "derived_from": CLIENT_REFS,
     "probe": "true\n",
     "effect": f"printf '%s' '{{{{FIXTURE_B64:p8test-throwaway-wrapped-passphrase}}}}' | cmp -s - {E}/wrapped-passphrase.b64"
               " && echo b64-is-the-stored-value\n"
               f"base64 -d < {E}/wrapped-passphrase.b64 | cmp -s - {E}/wrapped-passphrase && echo decoded-beside-it\n"
               "test -e /home/p8testuser/.ssh/authorized_keys || echo no-authorized-key\n",
     "expect": {"rc": 0, "stdout": "\\Ab64-is-the-stored-value\\ndecoded-beside-it\\nno-authorized-key\\n\\Z"}},
    {"id": "the-stored-passphrase-opens-the-client-home",
     "what": "the mount passphrase unwrapped from what the client got, with the user's login password, opens the user's "
             "encrypted home on the client (mounted read-only elsewhere for the check, then unmounted)",
     "control": "negative", "host": "peer",
     "mutates": "adds the passphrase to a throwaway session keyring and mounts the encrypted home on /run/p8test-ecr "
                "for the check, then unmounts it",
     "derived_from": CLIENT_REFS,
     "timeout": 60,
     "probe": MOUNT,
     "effect": "cat /run/p8test-ecr.out 2>/dev/null\ngrep -c ' /run/p8test-ecr ' /proc/mounts || true\n",
     "expect": {"rc": 0, "stdout": "\\Ahome-readable\\n0\\n\\Z"}},
]


def main():
    d = yaml.safe_load(P.read_text())
    peer = d["peer"]
    peer["kind"] = "kubuntu"
    peer["why"] = (peer["why"] + "; a desktop, since printinfo's encrypted-home form is user_desktop, which runs KDE's "
                   "tools as the user (HQ 2026-11-27 item 4)")
    peer["setup"] = SETUP
    admin = next(c for c in d["checks"] if c["id"] == "admin-sets-a-key-and-revokes-users")
    assert admin["probe"].count(OLD_NODEDEF) == 1
    admin["probe"] = admin["probe"].replace(OLD_NODEDEF, NEW_NODEDEF).replace(
        "$c userdel p8hashdel > /dev/null 2>&1\n", "$c userdel p8hashdel > /dev/null 2>&1\n" + ADMIN_ADD)
    assert ADMIN_ADD in admin["probe"]
    admin["what"] += ("; it also adds p8testuser and stores the user's ecryptfs data (setecryptfs), and gives the client "
                      "the user's encrypted-home line")
    admin["mutates"] += ("; useradd (SILENT) p8testuser and setecryptfs p8testuser with the suite's throwaway Private.sig "
                         "and wrapped passphrase; the node definition also gets p8testuser's user_desktop line")
    admin["effect"] += ("grep -cxF \"\\$p8testuser_ppwrapped = '{{FIXTURE_B64:p8test-throwaway-wrapped-passphrase}}'\" "
                        "$d/ppwrapped.pp\n"
                        f"p8_count '^  infra_populi::user_desktop +[{{].*ignorekey .. true' {NODEDEF}\n")
    assert admin["expect"]["stdout"].endswith("\\n3\\n\\Z")
    admin["expect"]["stdout"] = admin["expect"]["stdout"][:-2] + "1\\n1\\n\\Z"
    admin["derived_from"] += REFS[:3]
    d["checks"] += NEW_CHECKS
    for o in d["outcomes"]:
        if o["outcome"].startswith("encrypted home data (setecryptfs)"):
            o.pop("uncovered", None)
            o["checks"] = ["admin-sets-a-key-and-revokes-users"] + [c["id"] for c in NEW_CHECKS]
            o["from"] = ("templates/hashman/pp_auth.py.erb:370-381; templates/hashman/libhashman/interface.py.erb:362-372; "
                         "manifests/user_base.pp:104-135")
    apply = d.pop("apply")
    d["apply"] = apply
    P.write_text(bm.dump(d))


if __name__ == "__main__":
    main()
