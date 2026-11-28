# p8test_ecryptfs_home: the fixture user's encrypted home, as `adduser --encrypt-home` makes it on a company laptop
# (ecryptfs-setup-private --bootstrap: /home/.ecryptfs/<user>/.ecryptfs and .Private, the home mounted over them),
# left at rest (unmounted: the user is not logged in). user_base writes the user's wrapped passphrase into it; it does
# not create it. The passphrases are the suite's throwaway ones (spec/behaviour/fixtures/throwaway/README.md).
# Lifted by: nothing needed — a test asset (rules/test_asset_fixtures.txt): the encrypted home a company laptop has
package { 'ecryptfs-utils':
  ensure => installed,
}

file { '/usr/local/sbin/p8test-encrypt-home':
  ensure  => file,
  mode    => '0700',
  content => @(EOS),
    #!/bin/sh
    # Encrypt the home of user $1 (holding only its skeleton) as adduser --encrypt-home does, then unmount it.
    set -e
    u=$1
    h=$(getent passwd "$u" | cut -d: -f6)
    skel=$(mktemp -d)
    cp -a "$h/." "$skel/"
    find "$h" -mindepth 1 -delete
    ecryptfs-setup-private --bootstrap -u "$u" -l 'p8test-user-not-a-secret' -m 'p8test-mount-not-a-secret' --nopwcheck >/dev/null
    cp -a "$skel/." "$h/"
    chown -R "$u:" "$h"
    rm -rf "$skel"
    umount "$h"
    | EOS
}

exec { 'p8test encrypt the home of p8testuser':
  command => '/usr/local/sbin/p8test-encrypt-home p8testuser',
  creates => '/home/.ecryptfs/p8testuser/.ecryptfs/Private.sig',
  require => [Package['ecryptfs-utils'], File['/usr/local/sbin/p8test-encrypt-home'], User['p8testuser']],
  before  => File['/home/.ecryptfs/p8testuser/.ecryptfs/wrapped-passphrase.b64'],
}
