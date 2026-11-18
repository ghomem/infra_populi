# sysmon_base — check set escalated after two correction rounds (2026-11-18)

Status: OPEN, for HQ. Under backfill start rule 1, a set that cannot reach PASS after two correction rounds is
escalated, and the run continues.

There are no behaviour findings. Every review reproduced the author's runs, and every `derived_from` was ok. The last
author run (20261118T210322Z) passed all 20 checks.

The two local changes made in this batch are verified in both phases:
- **#3, net-tools for the connection checks:** Phase 1 PASS 20261118T201525Z.
- **#4, the Puppet check finds the lock notice in the whole output:** Phase 1 PASS 20261118T203841Z.
- **Phase 3:** the checks that drive them pass in the author's runs and in each reviewer run.

## Reviews
| review | verdict | the reviewer's reasons (purpose) |
|---|---|---|
| 20261118T204912Z | FAIL | Puppet check's CRITICAL path untested; stale package-list alarm untested; CPU and bandwidth alarm states untested |
| 20261118T210122Z (after round 1) | FAIL | elastic_query_check.py's `lifted_by: ubuntu2` is wrong (the script asks localhost:9200) and its Unknown, OK and Critical can be driven on the node; the RHEL package-count branch has no row |
| 20261118T211242Z (after round 2) | FAIL | see the verbatim reasons below |

Verbatim reasons of the last review:
> GAP: nagios-puppet.sh has a second CRITICAL branch, 'if [ $RC -gt 2 ]' (puppet agent --test exit 4 or 6, i.e.
> resources that failed during the run, the main failure a Puppet monitor exists to catch); the outcome row narrows
> 'fails otherwise' to the disabled agent (exit 1 branch) and no check reaches the -gt 2 branch, nor is it listed
> uncovered, although the lab can exercise it with a node-local mutating check (e.g. drift a managed file's mode and
> chattr +i it so the agent's fix fails, then undo). Secondary: the Elasticsearch stand-in answers every POST without
> recording it, so the outcome's 'asks localhost:9200 for matching sshd events' (URL /_search?size=10, the
> query_string and received_at range in the body) is not probed; the stand-in could record the request.

## Proposed round 3 (not run; the rule caps corrections at two)
- **The failed-resource branch:** drift a managed file's mode and `chattr +i` it, so the agent's fix fails (agent
  exit 4 or 6). Then run the Puppet check and expect CRITICAL with exit 2, and undo the attribute.
- **The Elasticsearch request:** the stand-in records each request's path and body. The check expects
  `/_search?size=10` and a query_string carrying the `-q` text.

HQ decides whether a third round runs.

## Leads (not findings)
- **The class header names Zimbra:** "monitor puppet runs, cpu, memory and zimbra". No sysmon_base code installs a
  Zimbra check; files/sysmon/check_zimbra.pl exists but is not deployed.
- **`$packagename` is dead code:** it is computed for Debian and RedHat, but no resource uses it.
- **`2>1` in nagios-puppet.sh:** it writes stderr to a file named `1` in the working directory. Under OpenVox 8 the
  agent's notices go to stdout, so the check's logic is unaffected (measured).
