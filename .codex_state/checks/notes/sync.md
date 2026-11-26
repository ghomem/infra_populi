# sync: authoring notes (the comments of .codex_state/checks/sync.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::sync (define; harness title `sync`, so the tag is "sync").
# Fixture (params, never committed): localdir /var/tmp/p8test-sync, remotedir /srv/p8test, localuser root (cron needs
# an account the clean node has), remoteuser p8testuser, hour 3, minute 17, hostlist "p8test.example.invalid:22
# p8test2.example.invalid:22" (two hosts since 2026-11-19, both names pinned to the peer),
# suffix -p8test, bwlimit_mbitps 10 (the conversion branch: 10 Mbit/s = 1.19 MiB/s). bindir comes from Hiera
# filesystem::bindir = /opt/puppet-infrastructure/bin (required_base filesystem_base).
# Extended 2026-11-19 (backfill batch 5, HQ batch-10 rulings 2 and C1): the script runs as behaviour against the peer
# (ubuntu2) as the remote host. The fixture host name p8test.example.invalid is pinned to the peer in the node's
# /etc/hosts (by reference, $P8_PEER_ADDR), root's public key is handed to the peer, where p8testuser serves
# /srv/p8test. The first run must mirror it into /var/tmp/p8test-sync/p8test.example.invalid-p8test, taking at least
# 4.5 s for a 6 MiB incompressible file under the 1.19 MiB/s limit; a file removed on the peer must be removed
# locally by the next run (--delete).
# Correction round 1, 2026-11-19 (review 20261119T174521Z FAIL, purpose): the class is multi-host (sync.pp:2, the
# template's loop over $HOSTS with a target directory per host), and the fixture listed one host, my choice rather than
# a lab limit. The fixture now lists two names, both pinned to the peer: each must get its own mirror, and the run
# moves 12 MiB, so the limit means at least 9 s.
# Authoring error 2026-11-19 (run 20261119T174827Z): the listing of the two mirrors followed the node's locale, which
# sorts p8test2 before p8test. (punctuation ignored); it is sorted with LC_ALL=C now. Both mirrors and the limit passed
# in that run (12.67 s for 12 MiB).
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): another port, no limit and another local user (undeterminable
# production use: the passwd/ layer) are a check in the variant run `other`; the 03:17 firing names what is missing.
# Correction round 1 of the swept set (2026-11-25, review 20261125T204119Z, purpose): the per-host port was never shown
# to be honoured (both hosts used 22, ssh's default). The fixture now lists p8test2.example.invalid:2222; the node pins
# that name to the peer's +100 alias address, where the peer refuses port 22 and an extra sshd listens on 2222, so its
# mirror can only come through the listed port.
```
