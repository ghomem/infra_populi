# Engine self-test (ck1 ruling 2, user_base escalation): user_base's wrapped-passphrase pattern with the PROPOSED
# post-condition guard, in a p8test directory. Expected: GREEN; and after the output is deleted, one run repairs it.
file { ['/var/tmp/p8test_guard', '/var/tmp/p8test_guard/.ecryptfs']: ensure => directory, mode => '0700' }
file { '/var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase.b64':
  ensure  => 'present',
  content => 'cDh0ZXN0IGZha2Ugd3JhcHBlZCBwYXNzcGhyYXNlCg==',
  mode    => '0600',
  notify  => Exec['/var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase'],
}
exec { '/var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase':
  command => 'cat /var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase.b64 |base64 -d > /var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase',
  unless  => 'sh -c "base64 -d < /var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase.b64 | cmp -s - /var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase"',
  path    => [ '/usr/local/bin/', '/bin/', '/usr/bin/' ],
  require => File['/var/tmp/p8test_guard/.ecryptfs/wrapped-passphrase.b64'],
}
