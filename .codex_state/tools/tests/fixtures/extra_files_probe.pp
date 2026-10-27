# Engine self-test (step 4.1d): the node can fetch from the lab master's [extra_files] mount (master_fixtures.sh).
file { '/var/tmp/p8test_extra_files_probe.crt':
  ensure => file,
  mode   => '0644',
  source => 'puppet:///extra_files/ssl/p8test.crt',
}
