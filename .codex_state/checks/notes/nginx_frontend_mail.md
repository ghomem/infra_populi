# nginx_frontend_mail: authoring notes (the comments of .codex_state/checks/nginx_frontend_mail.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::nginx_frontend_mail (class; node ubuntu; required_base nginx_base with the
# per-target fixture my_configs {mail, stream, package_name nginx-core, nginx_version 1.24.0}). Fixture (params, never
# committed): domain p8test.example.com, frontend_sslprefix p8test, letsencrypt_certificate true, mail_backend = the
# peer's host-only address. Purpose (the class header): a mail reverse proxy, IMAPS 993, SMTPS 465 and SMTP 25, each
# authenticated by a local auth_http server that points nginx at a local stream which carries the session to the mail
# backend; plus the backend's web interface on 443 through nginx_frontend_domain.
# The peer (ubuntu2) plays the mail backend: postfix (SMTP 25; SMTPS 465 with SASL from dovecot), dovecot IMAPS 993 and
# a TLS web page on 443. Its account p8testuser has the fake password p8test-mail-not-a-secret. Relayed mail never
# leaves it (default_transport error). Node probes name no lab host: the backend reaches the node only through the
# rendered nginx configuration. Mutating checks run after the read-only ones, in file order: the peer is set up first,
# then the node's sessions go through the proxy, then the peer is asked what arrived.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1); checks unchanged.
  # 2026-11-18 authoring correction (run 1, 20261118T073212Z): the check sent to p8test@relay.invalid, which the
  # backend's own `default_transport = error:` refused at RCPT (550 "relays nothing") although nginx had passed the
  # login on (the peer logged auth=1). The backend's submissions service now accepts any recipient only from an
  # authenticated sender (permit_sasl_authenticated, reject), and the message goes to the local mailbox. The behaviour
  # is unchanged.
  # 2026-11-18 authoring correction (run 1): nginx does not relay the backend's 535; it closes the session after the
  # backend refuses the login (the peer logged "SASL PLAIN authentication failed"). The probe records any refusal,
  # and the peer check below proves the refusal was the backend's.
  # 2026-11-18 authoring correction (run 1): the SMTPS session logs as postfix/smtpd (not submissions/smtpd), and its
  # client= line with the SASL user appears only for a queued message; the evidence now reads both tokens in the
  # mailbox, the queued SMTPS message's SASL user, and the backend's own refusals of the wrong passwords.
```
