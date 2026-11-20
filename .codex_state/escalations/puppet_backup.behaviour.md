# puppet_backup — behaviour finding: the backup directory is never created, and the script reports success anyway (2026-11-20)

Status: CLOSED 2026-11-20. HQ (after batch 16, item 1) ruled both parts: the backup define declares the directory (local change #14) and the script fails loudly (#15); puppet_backup Phase 3 PASS 20261120T225825Z with no findings; sysmon_backup's masking removed; cutover item 7 checks production. Was: OPEN, for HQ. Found in backfill batch 6; reproduced by the reviewer (checks/reviews/puppet_backup/20261120T122809Z.json, set PASS with this finding, purpose covered). Escalated for this
class under HQ batch-12 ruling 5: the fix has more than one reasonable design. The run continues.

## What the class does
- `puppet_backup` declares `puppet_infrastructure::backup { 'puppet': backdir => lookup('puppet::backdir'), ... }`
  (manifests/puppet_backup.pp:13 at the baseline).
- The lab Hiera's `puppet::backdir` is `%{hiera('filesystem::backdir')}/puppet`, which is
  `/opt/puppet-infrastructure/backup/puppet`.
- **Nothing declares that directory:**
  - filesystem_base declares only its parent, `/opt/puppet-infrastructure/backup` (manifests/filesystem_base.pp:13-24);
  - the backup define declares only the script and the cron entry (manifests/backup.pp:14-28);
  - puppet_backup declares only the define.
- The script writes `tar ... -f $BACKDIR/$FILEPREFIX-<date>.tar.gz` (templates/backup/backup.sh.erb:31). It has no
  `set -e`, and its last command is the ownership `if` on an empty TARGETUSER (:41-43), whose status is 0, so it
  exits 0 whatever tar did.

## Evidence
1. **Phase 3 run results/puppet_backup/20261120T122402Z-author:** `the-backup-directory-exists` reads `absent` after
   the GREEN apply. The runner then skips the three exercises.
2. **The script run by hand on that node, as cron would at 23:00:**
   - tar fails: `tar (child): /opt/puppet-infrastructure/backup/puppet/puppet.example.com-2026-Nov-20-12h26m.tar.gz:
     Cannot open: No such file or directory`;
   - the script still exits **0**;
   - no archive exists.
3. **The reviewer reproduced it** on a fresh node (checks/reviews/puppet_backup/20261120T122809Z.json): `absent` after a GREEN apply.

On a node where nobody created the directory by hand, the nightly backup of /etc/puppetlabs has therefore never run,
and cron sees success. Whether production's master has the directory is unknown: it would have been made outside the
code, and production is not read.

## Same defect elsewhere
- **sysmon_backup** has the same pattern: `sysmon::backdir` is `%{filesystem::backdir}/sysmon`, and nothing declares
  it.
- Its earlier check set (unjudged) creates the directory in its own action ("neither the class nor filesystem_base
  creates them"). That masks the defect; I'll correct the set when sysmon_backup's turn comes in the backfill.

## Options
- **A. Declare the directory in each wrapper class** (`file { $mybackdir: ensure => directory }` in puppet_backup and
  sysmon_backup). Minimal, local to the two classes. A node declaring the directory elsewhere would get a duplicate
  declaration.
- **B. Declare it in the backup define** (`file { $backdir: ensure => directory }`). Covers every consumer at once.
  Two backups sharing one backdir would collide (none do in the repo).
- **C. Create it in the script** (`mkdir -p "$BACKDIR"` in backup.sh.erb). It needs no resource. Ownership and mode
  are then the script's (root, umask).
- **D. Also make the script fail when tar fails** (`set -e`, or checking tar's status). This is independent of A–C:
  it turns any future silent failure into a cron error.

**Recommendation:** A for both classes, and D as a separate local change if HQ wants failures to show. A is a
one-resource change in each class, gives a declared owner and mode, and touches no shared file.
