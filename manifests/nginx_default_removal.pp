## Class: puppet_infrastructure::nginx_default_removal
#
# Purpose:
#   Remove the distro-provided default nginx site configuration.
#
# Dependencies:
#   - Package/layout that provides /etc/nginx/sites-enabled/default (typically nginx base setup).
#
class puppet_infrastructure::nginx_default_removal {
  file { '/etc/nginx/sites-enabled/default':
    ensure => absent,
  }
}
