# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none (wraps puppet_infrastructure::ssl_base; Service['nginx'] comes from puppet_infrastructure::nginx_base).
### Purpose ########
# defined type to control ssl cert and key for nginx
define puppet_infrastructure::ssl_nginx_domain (
  String $sslprefix,
  Boolean $letsencrypt_certificate = false,
)
{

  puppet_infrastructure::ssl_base { "ssl_${sslprefix}":
    myprefix                => $sslprefix,
    myservice               => 'nginx',
    myservicename           => 'nginx',
    letsencrypt_certificate => $letsencrypt_certificate,
  }

}
