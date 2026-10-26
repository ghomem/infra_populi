# Control fixture (step 1.1): the same exec with a `creates` guard is idempotent. The harness MUST
# turn this GREEN, proving the gate is not trivially red.
exec { 'p8test guarded exec':
  command => '/usr/bin/touch /var/tmp/p8test_guarded_exec',
  creates => '/var/tmp/p8test_guarded_exec',
}
