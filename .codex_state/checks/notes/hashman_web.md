# hashman_web: authoring notes (the comments of .codex_state/checks/hashman_web.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::hashman_web (class; node puppetserver, the master-role node p8lab-puppetserver,
# a Puppet server whose code tree holds hashman's database; required_base hashman_base (with postfix_smtp_node, the
# local MTA hashman mails through) and nginx_base; node_fixture hashman_master_standin: placeholder files at the lab
# Hiera's example logo paths /path/to/logo.png and /path/to/logo-email.png, the site's own images).
# Fixture: class defaults (letsencrypt_certificate false) and the lab Hiera (hashman::customname 'Hashman',
# hashman::company 'My Company', hashman::address = puppet::address puppet.example.com, hashman::sslprefix
# star.example.com, served by the master's fixture PKI).
# 2026-11-18 (HQ batch-10 rulings 6 and 9): the backend binds 127.0.0.1 (local change #2), checked from the peer and
# through a drift that the next agent run corrects; the logo placeholders are a test asset, not a stand-in.
# 2026-11-18 (HQ ruling C2): Hashman end to end. The administrator adds the fixture user p8hashuser with hashman's CLI
# (SILENT: no mail to the user) and copies the role line hashman prints into a node definition of the master-role
# server, as production copies it into the node definitions. The user changes the initial password in a headless
# Chromium on the peer (ubuntu2), through nginx. Hashman writes the new record. The peer's agent run against the
# master-role server, as p8test-hashman-client, applies the user, and PAM on the peer then accepts the new password
# and refuses the initial one. The initial password goes from the node to the peer as a handed-over file. Node probes
# name no lab host; peer probes name only the class node's host-only address.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1d): the three one-off rows name what is missing, with their evidence.
# Correction round 1 of the swept set (2026-11-25, review 20261125T083339Z, purpose): two rows were uncovered for reasons
# the lab disproves. Mail: the peer plays the relay host as in postfix_smtp_node's set (submission 587, SASL account
# p8test-relay; the lab Hiera gives p8lab-puppetserver its relay keys), and a help request sent through nginx and the
# mail of a non-SILENT useradd leave the node's postfix and arrive there. Signatures: a lab-generated key pair placed
# at the paths the code reads (a test asset, as the logo placeholders, HQ batch-10 ruling 9) lets /sign and /verify run
# through nginx. These checks come last, after both agent runs.
# 2026-11-25 authoring correction (run 20261125T083822Z-author): the mail fence also rejected loopback, so hashman's
# own SMTP connection to 127.0.0.1:25 was refused (reqhelp 500, useradd failed); and the mails hashman sent during the
# /sign and /verify calls, before the pin, were deferred and kept the queue from emptying. The fence now leaves the
# loopback interface alone and the queue is flushed after the pin. Hashman sent as the baseline makes it.
  # 2026-11-18 (HQ batch-10 ruling 6, policy B): the backend binds to 127.0.0.1 (local change #2); this check expected
  # the baseline's 0.0.0.0 before.
  # 2026-11-18 purpose correction (review 20261118T162830Z): /checkpwd is tested, /sign and /verify and session expiry
  # are listed as uncovered with their reasons.
  # 2026-11-25 (correction round 1 of the swept set): no baseline class deploys the key pair (files/hashman/ssl ships
  # only a public key no manifest installs); a site provides it, so the check places a lab-generated pair where the code
  # reads it, a test asset like the logo placeholders.
```
