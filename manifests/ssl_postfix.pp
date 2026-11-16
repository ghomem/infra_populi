# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own; through puppet_infrastructure::ssl_base: puppetlabs-concat 9.1.0 (Service['postfix'] comes from the consumer, e.g. postfix_smtp_base).
### Purpose ########
# class to control ssl cert and key for postfix
class puppet_infrastructure::ssl_postfix (
  String $sslprefix,
  Boolean $letsencrypt_certificate,
){
  puppet_infrastructure::ssl_base { 'postfix ssl config':
    myprefix                => $sslprefix,
    myservice               => 'postfix',
    myservicename           => 'postfix',
    letsencrypt_certificate => $letsencrypt_certificate,
  }
}
