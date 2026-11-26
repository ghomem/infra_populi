# puppet_commush: authoring notes (the comments of .codex_state/checks/puppet_commush.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::puppet_commush (class; no parameters; localdir from Hiera
# filesystem::localdir = /opt/puppet-infrastructure, its bin from the required base filesystem_base). Written
# 2026-11-19 (backfill batch 5). commush.sh runs as behaviour in a git clone whose origin is a local bare repository
# under /run (the https remote and its token prompt are the deployment's, not the script's logic); its answers come on
# stdin (read -e reads them when stdin is not a terminal).
# Correction round 1, 2026-11-19 (review 20261119T184905Z FAIL, purpose): every run named master, so the default branch
# was never exercised, and the clone held no untracked file. The confirmed run now passes no branch, and the clone has
# an untracked file that must stay untracked and out of origin.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1d): the https-remote row names what is missing, with its evidence.
```
