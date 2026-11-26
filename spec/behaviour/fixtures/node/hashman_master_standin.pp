# Node fixture hashman_master_standin: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
file { ['/path', '/path/to']:
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { ['/path/to/logo.png', '/path/to/logo-email.png']:
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "p8test placeholder logo (hashman_master_standin)\n",
}
