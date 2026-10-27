# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none.
class puppet_infrastructure::nginx_default_removal {
  # This removes the default config file from the package
  file { '/etc/nginx/sites-enabled/default':
    ensure => absent,
  }
}
