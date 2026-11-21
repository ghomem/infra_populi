# MOCK-APPLY node fixture `hashman_lock_standin` (HQ 2026-10-27 ruling 7) for user_lock (harness title p8testuser).
# user_lock runs hashman's `pp_auth.py lock <user>` on the Puppet master (required_base hashman_base, whose database
# lives in the master's code tree). Its ruled guard (upstream_defects.md user_lock) reads the user's entry in
# hashes.pp, so the user must exist in hashman's database for the define to be idempotent. On a real master the user
# was created through hashman beforehand; here the fixture supplies ONE database entry for p8testuser (the SHA-512 hash
# of the lab's user test password p8test-user-not-a-secret, salt p8testsalt, never a real user's; a fake hash until
# 2026-11-21, when user_lock's set began exercising the refusal), and since 2026-11-21 also its Samba hash entry in
# hashes_smb.pp (base64 NT hash of the same password), which hashman's lock also invalidates; added by a seeding exec
# before user_lock's exec, only if absent
# (hashman_base declares hashes.pp itself with replace => no, so the fixture cannot declare the file).
# (2026-11-17, HQ ruling 2: the code-tree directory left this fixture; the agent package ships it.)
# Behaviour (a locked user refused by pp_auth/the web interface on a master) is NOT verified by a GREEN with it.
# Lifted by: a master-role node whose hashman database holds the user (the planned nodes.yml kind puppetserver; HQ batch-5 ruling 6; HQ 2026-11-17 ruling 2)
file { '/usr/local/sbin/p8test-seed-hashman-user':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0755',
  content => @(SEED),
    #!/bin/sh
    # p8test fixture (hashman_lock_standin): p8testuser's hashman entries, as a real master holds them for a user
    # created through hashman: the Unix hash (hashes.pp) and the Samba hash (hashes_smb.pp), both of the lab's user
    # test password. Each is added only if absent; --check exits 0 when both are there.
    db=/etc/puppetlabs/code/environments/production/manifests/01_hashman
    have_unix() { grep -q '^\$p8testuser_pwd_hash ' "$db/hashes.pp"; }
    have_smb()  { grep -q '^\$p8testuser_pwd_hash_smb ' "$db/hashes_smb.pp" 2>/dev/null; }
    if [ "$1" = --check ]; then have_unix && have_smb; exit $?; fi
    have_unix || printf '%s\n' "\$p8testuser_pwd_hash = '\$6\$p8testsalt\$9xUyvkdoWnCLXETknv6/4H3vp7SZeY8/YeLlc0ghI7hRs/fF2LUjHGXmTgj4aqG2H/bbIFwnc09v0F/xru7g6/'" >> "$db/hashes.pp"
    have_smb || printf '%s\n' "\$p8testuser_pwd_hash_smb = 'mXVUzhrn8HhNXxCcp9uQcQ=='" >> "$db/hashes_smb.pp"
    | SEED
}
exec { 'p8test seed p8testuser into the hashman database':
  command => '/usr/local/sbin/p8test-seed-hashman-user',
  unless  => '/usr/local/sbin/p8test-seed-hashman-user --check',
  require => [File['/usr/local/sbin/p8test-seed-hashman-user'], Class['puppet_infrastructure::hashman_base']],
  before  => Exec['user_lock_p8testuser'],
}
