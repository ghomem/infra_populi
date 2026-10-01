# Puppet 8 migration: release-0.9.8 manifest validated unchanged.
# Module dependencies: none (uses Puppet built-in package/file resources and lookup()).
class puppet_infrastructure::hello_world_flask_common {

  $os_family = $facts['os']['family']

  $localdir            = lookup('filesystem::localdir')

  # Packages needed for the applications to run
  package { [ 'python3-gunicorn', 'python3-flask' ]: ensure => present, }


  # Directory for the hello world like demo applications
  file { "${localdir}/hello_world_flask":
    ensure  => directory,
    mode    => '0644',
    owner   => 'root',
    group   => 'root',
  }

}
