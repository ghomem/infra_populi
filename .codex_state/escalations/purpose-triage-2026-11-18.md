# Purpose triage of the Phase 5 backlog and every known finding (HQ 2026-11-18 policy B)

**Status: done by the advisor under policy B. "Now" items are fixed in the backfill batches, each driven by a check
that fails before and passes after, and listed in rules/local_changes.md. "Phase 5" items stay normalisation.
Escalated items need an HQ or Salatiel decision.**

Target release: Ubuntu 24.04 (ruling D). A finding that only bites on another release is filed under its pass.

| # | item (source) | class | triage | why |
|---|---|---|---|---|
| 1 | apt update frequency `always` (Phase 5 #1) | packages_base, node_base | Phase 5 | the purpose is achieved; the cost is an apt update on every run |
| 2 | `notify` resources reporting every run (Phase 5 #2) | nginx_frontend_domain (+ nginx_frontend, nginx_frontend_mail, hashman_web), mariadb_server, ssl_base | Phase 5 | a log line, not behaviour |
| 3 | dead sshd options `Protocol 2`, `UsePrivilegeSeparation` (Phase 5 #3) | ssh_secure | Phase 5 | ignored by OpenSSH; no behaviour |
| 4 | postfix `compatibility_level` unset (Phase 5 #4) | postfix_smtp_node | Phase 5 | postfix 3.8 runs with compatible defaults and delivers (Phase 3 postfix-config-sane); a warning only |
| 5 | linux_policies_user temporary script rebuilt every run (Phase 5 #5) | linux_policies_user | Phase 5 | the policies are applied; the run-2 events are accepted and listed |
| 6a | release-keyed `sudo` in shares.sh / linux-policies common (Phase 5 #6) | mount_shares_desktop, linux_policies_* | Phase 5 for shares; **check in the backfill** for linux-policies | shares.sh: `|| [ "$VERIFYSUDO" = "true" ]` and the mount call always passes `true`, so 24.04 uses sudo too (templates/shares/shares.sh.erb:81, 153-157). linux-policies COMMON common:131: the caller's VERIFYSUDO is read when its set is re-judged; if 24.04 then runs without sudo where root is needed, it is a "now" fix |
| 6b | other release-keyed branches (Phase 5 #6: mariadb 18.04 client, filesystem_apt openscap keyed to 24.04, configure_lock_screen 16.04 branch) | mariadb_server, filesystem_apt, user_kde_lock_screen | Phase 5 | on 24.04 the branch taken is the right one (their checks pass) |
| 7 | hashman leaves /tmp/pp_auth.lock behind when its mail fails (2026-11-18, C2 bring-up) | hashman_base | Phase 5 | with the MTA the composition provides (postfix_smtp_node), mail does not fail; a robustness defect of the baseline |
| 8 | hashman's backend (gunicorn) listens on 0.0.0.0:8080, reachable without nginx's TLS (hashman.service.erb:7) | hashman_web | **escalated: HQ** | not a purpose failure: logins work through nginx. It is an exposure of the login form over plain HTTP wherever the node's firewall does not block 8080, and binding 127.0.0.1 has more than one reasonable design (bind, firewall rule, or both) |
| 9 | hashman imports `crypt` (removed in Python 3.13) | hashman_base, hashman_web | 26.04 pass | Ubuntu 24.04 ships 3.12 (DeprecationWarning only); on 26.04 it stops the purpose |
| 10 | a fresh mail frontend renders `proxy_smtp_auth` only from its second agent run (puppet-nginx's version fact) | nginx_base, nginx_frontend_mail | documentation (list row 4) | transient on a fresh build; steady state correct; an operator can set `nginx_version` |
| 11 | RedHat: sysmon_base lib64 link; hello_world_flask_common EPEL (redhat_branches.md) | — | resolved (ruling A2) | composition, no class change |
| 13 | rsyslog_client: lines logged while the target is unreachable are dropped (the template's legacy forward action has no queue and no resume retry; phase3 run 2, 20261118T111830Z) | rsyslog_client | Phase 5 | forwarding works while the server is up; losing lines during an outage is reliability, and a queue has more than one reasonable design |
| 14 | rsyslog_base: the service subscribes to the TLS directory resource only (rsyslog_base.pp:79), while the comment on line 73 promises a reload "whenever the TLS files change"; a renewed certificate does not restart rsyslog | rsyslog_base | **escalated: HQ** | a manifest change (subscribe to the three files), outside policy B's templates/files/scripts. Whether rsyslog keeps an old certificate until a restart needs a certificate re-issued by a CA, which a check may not do on the lab master; the master-role node's CA could (uncovered, lifted_by puppetserver) |
| 12 | stale composite failure when the default node is powered off (2026-11-18) | engine | engine fix (next tool commit) | record_green reported a "regression"; the cause was the node, not the code |

Not found: no Phase 3 finding is open (no `escalations/*.behaviour.md`). The documentation list items are operator
notes, not fixes.
