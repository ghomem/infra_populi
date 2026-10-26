# Known-bad gate fixture (step 1.1): an exec with no unless/onlyif/creates/refreshonly runs on every
# agent run and reports only "executed successfully". The harness MUST turn this RED.
exec { 'p8test unguarded exec':
  command => '/bin/true',
}
