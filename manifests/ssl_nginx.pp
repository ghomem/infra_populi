# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own; through puppet_infrastructure::ssl_base: puppetlabs-concat 9.1.0 (Service['nginx'] comes from puppet_infrastructure::nginx_base).
### Purpose ########
# class to control ssl cert and key for nginx
class puppet_infrastructure::ssl_nginx (
  String $sslprefix
)
{

  puppet_infrastructure::ssl_base { 'puppet_infrastructure::ssl_base_nginx':
    myprefix      => $sslprefix,
    myservice     => 'nginx',
    myservicename => 'nginx'
  }

}
