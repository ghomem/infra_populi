# letsencrypt_base: authoring notes (the comments of .codex_state/checks/letsencrypt_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::letsencrypt_base (class; required_base filesystem_base).
# Fixture (params, never committed; every value fake): email p8test@p8test.example.com, dns_api_token
# p8test-not-a-secret, domains [p8test.example.com], provider digitalocean (the apt plugin package); other parameters
# at their defaults (renew 04:00, deploy 05:00, monthdays 5,10,15,20,25, automate_deployment true). etcdir is
# /opt/puppet-infrastructure/etc (lab Hiera).
# Not exercised: obtaining or renewing a certificate (needs the DNS provider's API); the hetzner/hetzner-cloud branches
# (pip provider), which the fixture does not select.
# 2026-11-20 (backfill batch 6): purpose and outcomes (HQ rulings 2 and C1). The plan's node moved to puppetserver, the
# master-role kind: production declares the class on the Puppet master (operations/puppet.pp), and its deploy script
# copies into the master's extra_files/ssl and chowns to the `puppet` user, which only a Puppet server has. The exercise
# plants what the master and certbot provide (the master's extra_files/ssl directory, hand-built in production; a
# renewed certificate under /etc/letsencrypt/live as certbot leaves it, plus one of another domain) and runs the script.
# Correction round 1, 2026-11-20 (review 20261120T113221Z): certbot-finds-the-dns-plugin's mutates now declares every
# write (its /run output, certbot's log and its work directory /var/lib/letsencrypt).
# Correction round 2, 2026-11-20 (review 20261120T113847Z): also certbot's empty renewal-hooks directories; the list
# is every path the node changed in that second of the reviewer's run (find -newermt), so nothing else is left out.
```
