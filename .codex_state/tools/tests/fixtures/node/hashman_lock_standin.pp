# MOCK-APPLY node fixture `hashman_lock_standin` (HQ 2026-10-27 ruling 7) for user_lock (harness title p8testuser).
# user_lock runs hashman's `pp_auth.py lock <user>` on the Puppet master (required_base hashman_base, whose database
# lives in the master's code tree). Its ruled guard (upstream_defects.md user_lock) reads the user's entry in
# hashes.pp, so the user must exist in hashman's database for the define to be idempotent. On a real master the user
# was created through hashman beforehand; here the fixture supplies:
# - the master's code-tree directory (as puppetserver_code_tree);
# - ONE fake database entry for p8testuser (the fixture hash `$6$p8testsalt$...`, never a real user's), added by a
#   seeding exec before user_lock's exec, only if absent (hashman_base declares hashes.pp itself with replace => no,
#   so the fixture cannot declare the file).
# Behaviour (a locked user refused by pp_auth/the web interface on a master) is NOT verified by a GREEN with it.
# Lifted by: a master-role node whose hashman database holds the user (no nodes.yml kind yet; HQ batch-5 ruling 6; HQ's hashman stand-in ruling pending)
file { '/etc/puppetlabs/code/environments/production/manifests':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { '/usr/local/sbin/p8test-seed-hashman-user':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0755',
  content => @(SEED),
    #!/bin/sh
    # p8test fixture: one fake hashman user entry (hashman_lock_standin)
    db=/etc/puppetlabs/code/environments/production/manifests/01_hashman/hashes.pp
    grep -q '^\$p8testuser_pwd_hash' "$db" || printf '%s\n' "\$p8testuser_pwd_hash = '\$6\$p8testsalt\$p8testfixturehash'" >> "$db"
    | SEED
}
exec { 'p8test seed p8testuser into the hashman database':
  command => '/usr/local/sbin/p8test-seed-hashman-user',
  unless  => '/bin/grep -q "^\$p8testuser_pwd_hash" /etc/puppetlabs/code/environments/production/manifests/01_hashman/hashes.pp',
  require => [File['/usr/local/sbin/p8test-seed-hashman-user'], Class['puppet_infrastructure::hashman_base']],
  before  => Exec['user_lock_p8testuser'],
}
