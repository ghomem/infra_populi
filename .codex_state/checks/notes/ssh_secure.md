# ssh_secure: authoring notes (the comments of .codex_state/checks/ssh_secure.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::ssh_secure (class; fixture params since 2026-11-19: client_alive_interval
# 10, every other parameter at its default, so the idle-session timeout can be seen in seconds instead of 4 hours).
# Lab Hiera fixture (master_fixtures.sh, 2026-11-19): puppet8node::ssh::othergroups 'p8testgroup', so AllowGroups is
# "sudo naemon p8testgroup ssh_in". Correction round 1 (2026-11-19, review 20261119T020808Z): root joins ssh_in for the
# probe so PermitRootLogin, not AllowGroups, is what refuses it (sshd logs ROOT LOGIN REFUSED); the Hiera group's
# login is a check.
# The node is Ubuntu 24.04 (osfamily Debian): $ssh_service = ssh, $admin_group = sudo. (Until 2026-11-19 the lab master
# had no othergroups key and AllowGroups was "sudo naemon  ssh_in"; the fixture above replaced that.)
# Effective configuration is read with `sshd -T` (what sshd will enforce, after Includes and defaults); negotiation
# checks connect from the node to itself (127.0.0.1) and stop at algorithm negotiation or authentication — no login.
# 2026-11-19, local change #8 (HQ batch-14 ruling 3): sshd's own idle timeouts (ChannelTimeout session=, Unused-
# ConnectionTimeout) are set from client_alive_interval on OpenSSH 9.2+; the idle check's expectation is unchanged
# (ended), its wording and the idle outcome name the new mechanism, and RHEL 9 is a row of its own (not enforced).
# Correction the same day (run 20261119T164515Z: still-connected): my value `session=` matched no channel type; on
# OpenSSH 9.6 they are session:command, session:shell and session:subsystem:... (sshd_config(5) on the node, whose
# example is `session:*=5m`). With `session:*=10s`, measured on the applied node: an idle command session ended after
# 11 s, an idle interactive shell after 10 s, and a session printing every 5 s ran its 21 s. The real timeout also cut
# the lab's own silent SSH session to the node (exit 255), so the params fixture moved from 10 to 30 s (room for the
# harness's agent runs), and the idle check runs its test session detached, 60 s silent, with the probe printing while
# it waits; it now also checks the session ended within 30 to 45 s, not merely at some point.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): the RedHat branch and the older sshd's idle behaviour are checks in
# the variant run `rhel` (rhel9); the Protocol 2 row names what is missing.
# 2026-11-23 authoring correction (sweep run 20261123T123442Z-author): the idle session ended, measured 29 s, under the
# window's 30 s floor. The window's floor does not allow for whole-second clocks: sshd keeps a channel's last use and
# checks its deadline in whole seconds (OpenSSH's monotime() returns time_t), so it may end the session up to 1 s before
# 30 s of real idle time, and the probe's start and end (`date +%s`) are whole seconds too; together the measured value
# is at least 29. The floor is now 29 s; it still tells an idle timeout from a session refused or cut at once.
# 2026-11-23 second authoring correction (sweep re-run 20261123T142843Z-author): with the 29 s floor the session ended,
# measured 28 s, so whole seconds did not explain it. The probe timed the session by the wall clock, and on this uplink
# the clean node's timesyncd steps that clock by about a second at each 32 s poll (measured 2026-11-23: offset
# -1.145530 s, jitter 427.644 ms, delay 196.258 ms to ntp.ubuntu.com); a backward step shortens a wall-clock interval.
# Both idle probes (Ubuntu and the rhel variant) now time the session by the monotonic clock (/proc/uptime, one decimal)
# and record the wall-clock seconds beside it; the 29 s floor stays for sshd's whole-second deadline.
# Correction round 1 of the swept set (2026-11-25, review 20261125T125545Z, purpose): the parameter variants other
# than client_alive_interval were in no row. node_base_domain_desktop sets password_authentication true on ssh_secure,
# so that is a check in the variant run `password` (a password login, right and wrong); production sets none of the
# others (not on ssh_secure, and node_base, which forwards them, gets none either), so they are an accepted-gap row. The moduli row says what is checked: the class's
# file installed with its content and mode.
# 2026-11-25 authoring correction (run 20261125T125931Z-author): the askpass helpers sat in /run, which Ubuntu mounts
# noexec, so ssh could not run them ("exec ... Permission denied") and neither login sent a password; they now live in
# /root/p8test-ssh. sshd's PasswordAuthentication was yes, as the baseline makes it.
# Outcomes table added 2026-11-19 (backfill batch 3, HQ batch-10 ruling 2), with login behaviour and the idle-session
# timeout as checks (the set read the configuration only); the fixture moved to params for the timeout.
  # 2026-11-19 authoring corrections (run 20261119T015853Z): the key's base64 holds + and /, which an extended regex
  # reads as operators, so the key is now matched literally (grep -F); and ssh read the rest of the probe's own script
  # from its standard input (the runner feeds scripts to bash -s), so the lines after it never ran; every ssh in the
  # set now runs with -n.
```
