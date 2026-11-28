"""Draft (HQ 2026-11-27 item 4): user_base's ecryptfs variant on a desktop node. The node fixture p8test_ecryptfs_home
makes p8testuser's private directory with throwaway passphrases; the class writes the suite's throwaway wrapped
passphrase over it, as on a company laptop with an encrypted home."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setedit import add_variant  # noqa: E402

E = "/home/.ecryptfs/p8testuser/.ecryptfs"
REF = "manifests/user_base.pp"
DIR = {"path": REF, "lines": "17", "text": '$ecryptdir = "/home/.ecryptfs/${myusername}/.ecryptfs"'}
IF = {"path": REF, "lines": "108", "text": "if( $ppsigs != '' ) and ( $ppwrapped != '' ) {"}
FILE = {"path": REF, "lines": "119", "text": 'file { "${ecryptdir}/wrapped-passphrase.b64":'}
CONTENT = {"path": REF, "lines": "121", "text": "content => $ppwrapped,"}
MODE = {"path": REF, "lines": "122-124", "text": "mode    => '0600',"}
EXEC = {"path": REF, "lines": "129",
        "text": 'command => "cat ${ecryptdir}/wrapped-passphrase.b64 |base64 -d > ${ecryptdir}/wrapped-passphrase",'}
UNWRAP = f"printf '%s' \"$1\" | ecryptfs-unwrap-passphrase {E}/wrapped-passphrase - 2>/dev/null"

checks = [
    {"id": "ecryptfs-the-wrapped-passphrase-is-pushed",
     "control": "negative",
     "what": "the given wrapped passphrase is written, base64 as given, to the user's ecryptfs directory (private, the "
             "user's), and decoded beside it",
     "derived_from": [DIR, IF, FILE, CONTENT, MODE, EXEC],
     "probe": f"stat -c '%U %a %n' {E}/wrapped-passphrase.b64 {E}/wrapped-passphrase\n"
              f"printf '%s' '{{{{FIXTURE_B64:p8test-throwaway-wrapped-passphrase}}}}' | cmp -s - {E}/wrapped-passphrase.b64"
              " && echo b64-is-the-given-value\n"
              f"base64 -d < {E}/wrapped-passphrase.b64 | cmp -s - {E}/wrapped-passphrase && echo decoded-beside-it\n",
     "expect": {"rc": 0, "stdout": "\\Ap8testuser 600 /home/\\.ecryptfs/p8testuser/\\.ecryptfs/wrapped-passphrase\\.b64\\n"
                "p8testuser [0-7]+ /home/\\.ecryptfs/p8testuser/\\.ecryptfs/wrapped-passphrase\\n"
                "b64-is-the-given-value\\ndecoded-beside-it\\n\\Z"}},
    {"id": "ecryptfs-the-login-password-unwraps-the-mount-passphrase",
     "control": "negative",
     "what": "the pushed wrapped passphrase opens with the user's login password and yields the mount passphrase whose "
             "signature the private directory carries, so the user's encrypted home unlocks at login",
     "derived_from": [IF, EXEC],
     "probe": "set -- 'p8test-user-not-a-secret'\n" + UNWRAP + "\n"
              f"printf '%s' '{{{{FIXTURE_B64:p8test-throwaway-private-sig}}}}' | base64 -d | cmp -s - {E}/Private.sig"
              " && echo the-directory-carries-its-signature\n",
     "expect": {"rc": 0, "stdout": "\\Ap8test-mount-not-a-secret\\nthe-directory-carries-its-signature\\n\\Z"},
     "mismatch": {"varies": "the password: a wrong login password must not unwrap the mount passphrase",
                  "probe": "set -- 'p8test-wrong-not-a-secret'\n" + UNWRAP + "\n"
                           f"printf '%s' '{{{{FIXTURE_B64:p8test-throwaway-private-sig}}}}' | base64 -d | cmp -s - "
                           f"{E}/Private.sig && echo the-directory-carries-its-signature\n"}},
    {"id": "ecryptfs-the-pushed-passphrase-opens-the-home",
     "control": "negative",
     "what": "the mount passphrase unwrapped from the pushed file with the login password opens the user's encrypted "
             "home (mounted read-only elsewhere for the check, then unmounted): the files of the home are readable",
     "mutates": "adds the passphrase to a throwaway session keyring and mounts the encrypted home on /run/p8test-ecr "
                "for the check, then unmounts it",
     "derived_from": [DIR, IF, EXEC],
     "timeout": 60,
     "probe": "install -d -m 0700 /run/p8test-ecr\n"
              f"printf '%s' 'p8test-user-not-a-secret' | ecryptfs-unwrap-passphrase {E}/wrapped-passphrase - "
              "> /run/p8test-ecr.pp 2>/dev/null\n"
              "keyctl session - sh -c 'keyctl link @u @s; ecryptfs-add-passphrase --fnek - < /run/p8test-ecr.pp "
              f">/dev/null; s=$(head -1 {E}/Private.sig); f=$(tail -1 {E}/Private.sig); "
              "mount -i -t ecryptfs -o ro,ecryptfs_sig=$s,ecryptfs_fnek_sig=$f,ecryptfs_cipher=aes,ecryptfs_key_bytes=16 "
              "/home/.ecryptfs/p8testuser/.Private /run/p8test-ecr && { test -s /run/p8test-ecr/.profile && "
              "echo home-readable; umount /run/p8test-ecr; }' > /run/p8test-ecr.out 2>/dev/null\n"
              "rm -f /run/p8test-ecr.pp\n",
     "effect": "cat /run/p8test-ecr.out 2>/dev/null\ngrep -c ' /run/p8test-ecr ' /proc/mounts || true\n",
     "expect": {"rc": 0, "stdout": "\\Ahome-readable\\n0\\n\\Z"}},
    {"id": "ecryptfs-the-wrapped-passphrase-is-damaged-out-of-band",
     "control": "negative",
     "what": "the decoded wrapped passphrase is overwritten out of band (the .b64 file stays as pushed)",
     "mutates": f"overwrites {E}/wrapped-passphrase with other bytes",
     "derived_from": [EXEC],
     "probe": f"printf 'p8test-damaged' > {E}/wrapped-passphrase\n",
     "effect": f"test -s {E}/wrapped-passphrase.b64 || exit 1\n"
               f"base64 -d < {E}/wrapped-passphrase.b64 | cmp -s - {E}/wrapped-passphrase && echo same || echo differs\n",
     "expect": {"rc": 0, "stdout": "\\Adiffers\\n\\Z"}},
    {"id": "ecryptfs-the-agent-run-repairs-it",
     "control": "negative",
     "what": "the next agent run decodes the pushed value again (the ruled guard runs the exec when the decoded file "
             "differs), so the user can still unlock the home",
     "mutates": "none beyond reading the files (declared mutating so it runs after the node's agent run)",
     "derived_from": [EXEC],
     "probe": "true\n",
     "effect": f"base64 -d < {E}/wrapped-passphrase.b64 | cmp -s - {E}/wrapped-passphrase && echo same || echo differs\n"
               "set -- 'p8test-user-not-a-secret'\n" + UNWRAP + "\n",
     "expect": {"rc": 0, "stdout": "\\Asame\\np8test-mount-not-a-secret\\n\\Z"}},
]
variant = {"name": "ecryptfs", "node": "kubuntu", "params": "ecryptfs", "node_fixture": "p8test_ecryptfs_home",
           "why": "company laptops use encrypted homes (HQ 2026-11-27 item 4): the user's ecryptfs private directory, made "
                  "by the node fixture as ecryptfs-setup-private makes it, gets the given wrapped passphrase"}
if __name__ == "__main__":
    add_variant("user_base", variant, checks,
                cover={"the ecryptfs branch": [c["id"] for c in checks]})
    # the repair is judged after an agent run that follows the damage
    import yaml  # noqa: E402
    import behaviour_move as bm  # noqa: E402
    path = Path(__file__).resolve().parents[2] / "spec" / "behaviour" / "checks" / "user_base.yml"
    data = yaml.safe_load(path.read_text())
    after = data["node_agent"]["after"]
    after = after if isinstance(after, list) else [after]
    data["node_agent"]["after"] = after + ["ecryptfs-the-wrapped-passphrase-is-damaged-out-of-band"]
    path.write_text(bm.dump(data))
