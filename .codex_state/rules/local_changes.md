# Local changes list — single source for purpose fixes (HQ 2026-11-18 policy B)
Every change this repository makes to a class's templates, files or scripts so that the class achieves its purpose on
the target OS releases (Ubuntu 24.04 for Phase 1). Each row needs:
- the behaviour check that failed before and passes after (check id, both result files);
- the minimal change;
- the reviewer verdict.

Earlier ruled changes keep their own single sources, which are not repeated here: `class_rulings.txt` holds
module-compatibility changes and ruled per-class edits, and `../upstream_defects.md` holds locally fixed upstream
defects. Escalate instead of listing when a fix changes a class interface, removes functionality, or has more than
one reasonable design. Advisor-only file.

| # | class | change (file:line) | check failing before → passing after | reviewer | date |
|---|---|---|---|---|---|
| 1 | rsyslog_base | `subscribe => File['/etc/rsyslog.d/tls']` becomes a subscribe to the directory and the three TLS files, ca.pem, `${certname}.pem` and `${certname}.key` (rsyslog_base.pp:79 at the baseline); HQ batch-10 ruling 5 | the-agent-run-restores-the-file-and-restarts-rsyslog-once: FAIL before (results/rsyslog_base/20261118T152601Z-author: the CA restored, 0 rsyslog starts); PASS after (results/rsyslog_base/20261118T153820Z-author: restored, a new PID, 1 start) | Phase 1 PASS (reviews/rsyslog_base/20261118T153709Z.json); Phase 3 PASS (checks/reviews/rsyslog_base/20261118T155303Z.json) | 2026-11-18 |
| 2 | hashman_web | the backend binds 127.0.0.1:8080 instead of 0.0.0.0:8080 (templates/hashman/hashman.service.erb:7), and the unit file notifies Service['hashman'] (hashman_web.pp:167-172) so a master already running the old unit is rebound at its next agent run; HQ batch-10 ruling 6 (nginx proxies to 127.0.0.1:8080 only, hashman_web.pp:186-188) | hashman-service-on-8080 and other-machines-reach-hashman-only-through-nginx: FAIL before (results/hashman_web/20261118T155419Z-author: 0.0.0.0:8080; 8080 open from the peer); PASS after (results/hashman_web/20261118T161404Z-author: 127.0.0.1:8080 only, 8080 refused from the peer, the page through nginx, Hashman end to end, an old unit rebound by the next agent run) | Phase 1 PASS (reviews/hashman_web/20261118T161250Z.json); Phase 3 PASS after one purpose correction (checks/reviews/hashman_web/20261118T164319Z.json) | 2026-11-18 |
| 3 | sysmon_base | `package { 'net-tools': ensure => installed, }` added (sysmon_base.pp, after the lookups): check_netstat_conns.sh and check_netstat_cip.sh run `netstat`, which Ubuntu 24.04 does not install (absent from the clean node's inventory; no class installs it), so both reported OK with every count 0 and `netstat: command not found` on stderr. The scripts are unchanged. net-tools is also the RHEL 9 package name. Rewriting the scripts with `ss` was the other design; installing the tool the scripts call is the minimal one | the-connection-checks-count-real-connections: FAIL before (results/sysmon_base/20261118T195759Z-author: `tcp listen zero established zero`, `remote IPs on 22 zero`, 1 command-not-found); PASS after (pending) | Phase 1 review pending | 2026-11-18 |
