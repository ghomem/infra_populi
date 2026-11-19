# ssh_secure — behaviour finding: the idle-session timeout no longer acts (2026-11-19)

**Status: CLOSED 2026-11-19.** Fixed by local change #8 (ChannelTimeout session:*= and UnusedConnectionTimeout from client_alive_interval on OpenSSH 9.2+): Phase 1 PASS 20261119T170145Z, Phase 3 PASS 20261119T170844Z. RHEL 9: not enforced, approval_conditions.md #3.

**HQ ruling (batch 14, 2026-11-19):** restore the idle disconnect with sshd's own idle-timeout settings where OpenSSH has them (9.2 and later, so Ubuntu 24.04), set from the class's existing timeout value; where it lacks them (RHEL 9) record it as not enforced, no shell workaround. If the analysis finds a reason this does not work, hold the class and show HQ. The text below is the escalation as sent.

Status: OPEN, for HQ. The reviewer reproduced it (checks/reviews/ssh_secure/20261119T022504Z.json, set PASS with this
finding, purpose covered after one correction). Escalated for this class under HQ batch-12 ruling 5: a finding whose fix has more than one
reasonable design. The run continues with the next class.

## What the class means to do
- `ClientAliveInterval => $client_alive_interval` (default 14400) with `ClientAliveCountMax => '0'` (ssh_secure.pp:5,
  75-76).
- Under OpenSSH before 8.2, a count of 0 ended a session once it had been idle for the interval: a 4-hour idle
  timeout by default.

## What happens on the target release
- **The node:** OpenSSH 9.6p1, Ubuntu 24.04 (`sshd -V`).
- **The node's sshd_config(5), on ClientAliveCountMax:** "Setting a zero ClientAliveCountMax disables connection
  termination."
- **Check `an-idle-session-is-ended-after-the-interval`:** the fixture sets `client_alive_interval` to 10. A session
  that sends nothing for 30 s should end after 10 s. It stayed: `still-connected` (results/ssh_secure/
  20261119T020139Z-author). sshd -T shows clientalivecountmax 0 and clientaliveinterval 10, as the class sets them.
- **So** with the class's settings, idle SSH sessions are never ended on Ubuntu 24.04 (or on any release with
  OpenSSH 8.2 or later, Ubuntu 20.04 onward).

## Options (more than one reasonable design, so policy B needs a ruling)
- **A. `ChannelTimeout session=<interval>`** (OpenSSH 9.2+). It closes session channels with no traffic for the
  interval, the closest equivalent of the old idle timeout. It needs OpenSSH 9.2 or later.
- **B. `UnusedConnectionTimeout`** (OpenSSH 9.2+). It ends connections with no open channels; on its own it does not
  end an idle interactive shell.
- **C. A nonzero `ClientAliveCountMax` (e.g. 3).** It ends only unresponsive clients; a live but idle client answers
  the probes and stays. It is not an idle timeout.
- **D. A shell `TMOUT` (profile.d).** It ends idle interactive shells only, outside sshd.
- **E. No fix:** record that the idle timeout is not enforced on current OpenSSH, and accept it in the approval report.

**Recommendation: A** with the same interval. It keeps the class's intent (sessions idle for the interval end) on the
target release.

## Not affected
Everything else in the set passes:
- the algorithms;
- AllowGroups as login behaviour: a key login in ssh_in works, a key login outside the allowed groups is refused;
- password and root logins refused;
- host keys and the moduli file.
