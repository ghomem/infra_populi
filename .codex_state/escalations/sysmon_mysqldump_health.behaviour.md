# sysmon_mysqldump_health — behaviour findings (findings 1 and 2 FIXED, local changes #18 and #20; the check set OPEN, for HQ: past the correction cap)

Production use 0 (migration_order.md). Both findings are in the baseline template
`templates/sysmon/check-mysqldump-health.sh.erb` (cf477c6), measured on the lab node with Ubuntu's MySQL 8.0.46.

## Finding 1 — a .sql file that is not a mysqldump is reported OK (policy B, one clear fix: local change #18)
- Lines 64-69: for a `.sql` file without the "MySQL dump" header, the script calls `handle_error $RC "SQL File $f is
  not a MySQLDump"`. `$RC` still holds the previous step's 0, or it is unset when the file comes first, and then the
  arguments shift and `[` errors with "too many arguments". Either way handle_error returns and the check ends
  "OK: exit code 0".
- Measured: an empty `empty.sql` beside a good dump gives OK, exit 0 (results/sysmon_mysqldump_health/20261121T113058Z-author,
  reproduced by review 20261121T113606Z). A dump written with `mysqldump --skip-comments` has no header and is also
  reported OK.
- An empty dump is exactly what a failed backup leaves, so the check reports a broken backup as healthy.
- Fix: `handle_error 1 "SQL File $f is not a MySQLDump"`, the failure the line's own message declares. This is
  minimal and changes nothing else.

## Finding 2 — a failed create drops a live database of the dump's name (for HQ: more than one reasonable design)
- Lines 46-48 and 11-24: when `CREATE DATABASE <name from the dump>` fails, handle_error first runs clear_database,
  which is `DROP DATABASE $DBNAME`, and then reports CRITICAL.
- If a database of that name already exists on the host (the live one, when the check runs on the database server
  itself), the check drops it.
- Measured 2026-11-21: p8testsrc with 3 rows existed; the check printed "CRITICAL: Create database p8testsrc", exit 2,
  and afterwards `SELECT COUNT(*) FROM p8testsrc.t` gave "Unknown database 'p8testsrc'".
- Options:
  - **A (recommended): drop only what the check created.** clear_database runs only after a successful create, for
    example with a flag set after line 47. The check still reports CRITICAL "Create database" on a host that holds a
    database of that name. This is the smallest change.
  - **B: restore into a scratch name** (a fixed prefix plus the dump's name). The check then also works on the
    database server itself. It is a larger change: dumps made with `--databases` carry their own `CREATE DATABASE`
    and `USE` lines.
  - **C: refuse when the name exists**, checking before the create. This reports UNKNOWN or CRITICAL without touching
    anything.
- The set's check `a-live-database-of-the-dump-name-is-left-intact` expects the purpose (CRITICAL and the database
  intact). It stays a finding until HQ rules.

## Status (2026-11-21)
- Finding 1 is fixed by local change #18: Phase 1 PASS 20261121T115850Z; the after-check passed in
  results/sysmon_mysqldump_health/20261121T115445Z-author and in the reviewer run.
- Finding 2 was reproduced by review 20261121T120256Z. That review passed the set on purpose: 7 outcomes, no uncovered
  rows. It awaits HQ's choice of A, B or C.

## Finding 2 resolved (2026-11-22)
HQ ruling 1 withdrew the scratch-name design and took the advisor's, with conditions: before any restore, list the
databases the dump would create or use; if any exists, do not restore, validate the file only and say so in the output;
a restore drops only databases it created in that run. Local change #20 (row in rules/local_changes.md):
- before (results/sysmon_mysqldump_health/20261122T233809Z-author): with a live p8testsrc the check printed "CRITICAL:
  Create database p8testsrc" and its error path dropped the live database (no rows afterwards);
- after (20261122T234851Z-author, on the recorded code 287a517): the live p8testsrc keeps its 3 rows and the OK line
  says the restore test was skipped because it exists; a cut dump of an existing database is CRITICAL "incomplete"
  with the rows kept; a --databases dump of an absent database is restored and nothing is left behind.
- Phase 1 review PASS (01e4f81, reviews/sysmon_mysqldump_health/20261122T235348Z).

## The check set after #20: Phase 3 review FAIL on purpose, past the correction cap (OPEN, for HQ)
Review 20261122T235949Z (c9e48a4) reproduced every check (reviewer run ALL_PASS) and found no behaviour finding. It
failed purpose: the stated purpose says any failure (create, load, drop) is CRITICAL, but this set version replaced
the old "Create database" outcome with the skip outcome, so the remaining create-failure path (template lines 71-73:
CREATE fails for a database the pre-check did not see) has no outcome row, check or uncovered row. That path is also
where #20's rule must hold with nothing created: CREATED is empty, so nothing may be dropped.

The set used its two correction rounds on 2026-11-21 (production use 0: cap two), so a third round needs HQ.

The fix I would make (one check, one outcome row): `a-failed-create-is-critical-and-drops-nothing` — REVOKE CREATE from
p8test_check, run the check once, GRANT ALL again; expect "CRITICAL: Create database p8testsrc" with exit 2 and the
count of p8test databases unchanged. Then the run, and one more Phase 3 review.

- **For HQ:** allow that round, or let the set stand with the create-failure path as an open row.
