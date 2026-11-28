# Throwaway test material

Everything here is test material made for this suite and published with it. None of it protects anything: it exists
so a check can exercise a behaviour that needs a secret's other half (a login with a pushed key, an encrypted home
unwrapped with a passphrase). Never reuse it anywhere else.

- `p8test-throwaway-rsa` / `.pub`: an SSH RSA keypair (the classes push keys as ssh-rsa) (comment `p8test-throwaway-NOT-A-SECRET`). Params fixtures push
  the public half; a check writes the private half on the test node and logs in with it.
- `p8test-throwaway-wrapped-passphrase`: an ecryptfs wrapped passphrase, made with `ecryptfs-wrap-passphrase`: the
  mount passphrase `p8test-mount-not-a-secret` wrapped with the login password `p8test-user-not-a-secret`.
- `p8test-throwaway-private-sig`: the `Private.sig` of a home encrypted with that mount passphrase (its two key
  signatures, content and file names), as hashman stores it for a user (ppsigs).
  The node fixture `p8test_ecryptfs_home` encrypts the fixture user's home with the same two passphrases, so the
  wrapped passphrase a params fixture pushes opens it.

A set or params fixture names a file here as `{{FIXTURE_B64:<file name>}}` (its content, base64-encoded). The suite's
check (pre-commit) refuses private key material anywhere else under spec/behaviour.
