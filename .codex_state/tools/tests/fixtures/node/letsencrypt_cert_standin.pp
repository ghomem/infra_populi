# MOCK-APPLY node fixture `letsencrypt_cert_standin` (HQ 2026-10-27 ruling 7) for letsencrypt_certificate (fixture
# domain p8test.example.com). The define's letsencrypt::certonly runs `certbot certonly` against Let's Encrypt with a
# DNS provider's API token, which the lab cannot have. puppet-letsencrypt guards that exec with
# letsencrypt-domain-validation, which accepts an existing live certificate whose SANs equal the requested domains.
# The fixture creates one: a self-signed THROWAWAY certificate for p8test.example.com at
# /etc/letsencrypt/live/p8test.example.com/cert.pem, ordered after Class['letsencrypt'] and before the certonly exec.
# Behaviour (obtaining or renewing a certificate) is NOT verified by a GREEN with this fixture.
exec { 'p8test stand-in certificate for p8test.example.com':
  command => '/bin/sh -c "install -d -m 0755 /etc/letsencrypt/live/p8test.example.com && openssl req -x509 -newkey rsa:2048 -nodes -days 90 -subj /CN=p8test.example.com -addext subjectAltName=DNS:p8test.example.com -keyout /etc/letsencrypt/live/p8test.example.com/privkey.pem -out /etc/letsencrypt/live/p8test.example.com/cert.pem"',
  creates => '/etc/letsencrypt/live/p8test.example.com/cert.pem',
  require => Class['letsencrypt'],
  before  => Exec['letsencrypt certonly p8test.example.com'],
}
