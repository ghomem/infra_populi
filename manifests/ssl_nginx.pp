# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own; through infra_populi::ssl_base: puppetlabs-concat 9.1.0 (Service['nginx'] comes from infra_populi::nginx_base).
### Purpose ########
# class to control ssl cert and key for nginx
class infra_populi::ssl_nginx (
  String $sslprefix
)
{

  infra_populi::ssl_base { 'infra_populi::ssl_base_nginx':
    myprefix      => $sslprefix,
    myservice     => 'nginx',
    myservicename => 'nginx'
  }

}
