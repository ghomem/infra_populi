# Node fixture `hashman_user_via_hashman` for user_lock (harness title p8testuser) on the master-role node (kind
# puppetserver). It replaces the stand-in `hashman_lock_standin` (HQ after batch 20, item 6: the lift "the master-role
# node's hashman database"). user_lock locks a user that already exists in hashman's database; on a real master the
# user was created through hashman beforehand. Here hashman itself creates p8testuser, as an administrator would:
# `pp_auth.py useradd ... SILENT` (a new user starts locked, with an initial password hashman generates and prints),
# then `pp_auth.py unlock` and `unexpire`, so that the lock user_lock applies is its own (on the Unix and the Samba
# hash); the Samba hash's state before the lock goes to /root/p8test-hashman-smb-before-lock. No hash is seeded. The initial password is
# kept in /root/p8test-hashman-initial (0600) for the behaviour check that the locked user is refused although the
# password matches; it is a throwaway password of a p8test account on a lab node, never a real user's.
# Runs only if hashman's database has no entry for p8testuser yet, and before user_lock's exec.
# Lifted by: nothing needed — a test asset (rules/test_asset_fixtures.txt): the user is created by hashman itself.
file { '/usr/local/sbin/p8test-create-hashman-user':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0755',
  content => @(CREATE),
    #!/bin/sh
    # p8test fixture (hashman_user_via_hashman): create p8testuser through hashman's own CLI, then unlock it.
    # --check exits 0 when hashman's database already holds the user.
    db=/etc/puppetlabs/code/environments/production/manifests/01_hashman
    if [ "$1" = --check ]; then grep -q '^\$p8testuser_pwd_hash ' "$db/hashes.pp"; exit $?; fi
    set -e
    cd /opt/infra-populi/hashman/common
    out=$(./pp_auth.py useradd p8testuser p8testuser@example.invalid "P8test User" p8test SILENT 2>&1)
    umask 077
    printf '%s' "$out" | sed -n 's/.*created with initial password //p' | head -1 | tr -d '\n' > /root/p8test-hashman-initial
    test -s /root/p8test-hashman-initial
    ./pp_auth.py unlock p8testuser "p8test fixture" > /dev/null
    # hashman's useradd expires the new password, and an expired entry's Samba hash carries the lock prefix too: clear
    # the expiry, so that before the lock the user is neither locked nor expired (user_lock checkset round 3)
    ./pp_auth.py unexpire p8testuser > /dev/null
    if grep -q "^\$p8testuser_pwd_hash_smb = '!" "$db/hashes_smb.pp"; then echo locked; else echo valid; fi \
      > /root/p8test-hashman-smb-before-lock
    | CREATE
}
exec { 'p8test create p8testuser through hashman':
  command => '/usr/local/sbin/p8test-create-hashman-user',
  unless  => '/usr/local/sbin/p8test-create-hashman-user --check',
  require => [File['/usr/local/sbin/p8test-create-hashman-user'], Class['infra_populi::hashman_base']],
  before  => Exec['user_lock_p8testuser'],
}
