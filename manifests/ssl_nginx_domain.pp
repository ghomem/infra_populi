# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none (wraps infra_populi::ssl_base; Service['nginx'] comes from infra_populi::nginx_base).
### Purpose ########
# defined type to control ssl cert and key for nginx
define infra_populi::ssl_nginx_domain (
  String $sslprefix,
  Boolean $letsencrypt_certificate = false,
)
{

  infra_populi::ssl_base { "ssl_${sslprefix}":
    myprefix                => $sslprefix,
    myservice               => 'nginx',
    myservicename           => 'nginx',
    letsencrypt_certificate => $letsencrypt_certificate,
  }

}
