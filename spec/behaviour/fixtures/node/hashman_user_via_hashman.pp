# Node fixture hashman_user_via_hashman: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
file { '/usr/local/sbin/p8test-create-hashman-user':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0755',
  content => @(CREATE),
    db=/etc/puppetlabs/code/environments/production/manifests/01_hashman
    if [ "$1" = --check ]; then grep -q '^\$p8testuser_pwd_hash ' "$db/hashes.pp"; exit $?; fi
    set -e
    cd {{LOCALDIR}}/hashman/common
    out=$(./pp_auth.py useradd p8testuser p8testuser@example.invalid "P8test User" p8test SILENT 2>&1)
    umask 077
    printf '%s' "$out" | sed -n 's/.*created with initial password //p' | head -1 | tr -d '\n' > /root/p8test-hashman-initial
    test -s /root/p8test-hashman-initial
    ./pp_auth.py unlock p8testuser "p8test fixture" > /dev/null
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
