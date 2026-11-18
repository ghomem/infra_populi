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
| 2 | hashman_web | the backend binds 127.0.0.1:8080 instead of 0.0.0.0:8080 (templates/hashman/hashman.service.erb:7), and the unit file notifies Service['hashman'] (hashman_web.pp:167-172) so a master already running the old unit is rebound at its next agent run; HQ batch-10 ruling 6 (nginx proxies to 127.0.0.1:8080 only, hashman_web.pp:186-188) | hashman-service-on-8080 and other-machines-reach-hashman-only-through-nginx: FAIL before (results/hashman_web/20261118T155419Z-author: 0.0.0.0:8080; 8080 open from the peer); after: pending | pending | 2026-11-18 |
