# firewall_secure_extra — behaviour findings and check set (2026-11-18)

Status: CLOSED for the backfill (2026-11-19). Round 4, the last (HQ batch-12 ruling 2), passed review
20261119T004725Z: purpose covered, reproduced, with one finding, the RST limit, as ruled (no fix). The class goes to
the approval report as it stands. Round 4 recorded the SSH rules' counters around the held connections: 8 held, and
only rule 112 dropped anything, in the author's run, the reviewer's and three hand repetitions. The one count of 7
did not recur, and with no legitimate interaction shown, the expectation stays at 8. Rule 518 is on the Phase 5
backlog (#8, HQ batch-12 ruling 1).

Earlier status (2026-11-18): OPEN, for HQ. HQ ruled the batch-11 version of this file in "HQ rulings on batch 11" (DESIGN_DECISIONS
2026-11-18). This version records what those rulings did, and the third and last correction round (ruling 3), whose
review failed. Under ruling 3 the set is escalated with the reviewer's reasons verbatim, and the run moved on.

## Production use (measured, names and counts only)
No production node statement sets node_base's `firewall_secure_extra => true` (0 of 38). No fleet file outside
`passwd/` names the class or its parameters.

## Finding 1, the blacklist: FIXED (HQ batch-11 ruling 1, local change #5)
- **The change:** rule `666 grounding naughty boys: <ip>` became `00 grounding naughty boys: <ip>` with
  `proto => 'all'`. puppetlabs-firewall 8.3.0 orders a chain's rules by a string sort of their titles, so `00 ` comes
  first. The parameter's comment (baseline :25) describes addresses "to be dropped unconditionally".
- **Phase 1:** re-migrated and recorded with `--local-change`; review PASS (reviews/firewall_secure_extra/20261118T223859Z.json).
- **On the applied node:** the drop is the INPUT chain's first rule.
- **Phase 3:** check `a-blacklisted-source-gets-nothing` passes in the author's run (results 20261118T223957Z) and in
  the reviewer's:
  - from the blacklisted address, ICMP and SSH are dropped;
  - from an unlisted address, both get in.
- **Row:** rules/local_changes.md #5.

## Finding 2, the RST limit: NO FIX (HQ batch-11 ruling 2)
- Rules 519/520 are never reached. Rule 003 accepts RSTs inside connections, and mangle rule 501 drops RSTs outside a
  connection as INVALID.
- The check `the-rst-limit-dropped-the-third` still fails, as the ruling expects (0 and 0 every run).
- It is on the Phase 5 backlog (#7) and goes into the approval report as an unreachable rule.

## The check set: escalated after the third and last correction round (HQ batch-11 ruling 3)
- **Round 3:** local change #5, the protocol wording on the rows, the ICMP-fragment check removed, and rules 518 and
  002 as uncovered rows with their measurements. Author's run: 23 of 24 pass; the RST limit fails as ruled.
- **Review 20261118T225957Z:** derived_from ok, purpose ok, reproduced FAIL. The reviewer's reasons, verbatim:

> evidence finding the-rst-limit-dropped-the-third: the node's counters for rule 519 and 520 rose by 0 and 0 after the
> peer reset 3 connections at once (expected 2 and 1): the RSTs never reach rules 519/520 (rule 003 accepts ESTABLISHED
> first) - same unreachable RST limit the set itself names in its fragment row

> evidence finding held-ssh-connections-stop-at-eight: the peer saw 7 established SSH connections (expected 8) after
> 10 connections one every 4 s held by timeout 50 nc; baseline :130/:149 (connlimit_above 8) allow up to 8, so one of
> the first 8 was not held: either a dropped or closed connection (e.g. sshd ending an unauthenticated nc session) or a
> real limit below 8; the author's run passed this check, so the two runs disagree and the check's exact-8 expectation
> is not reproducible as written

> Minor: rows 002 and 518 name lifted_by ubuntu although their reasons say no node would show the rule act;
> compile-time fail() validations (:39-52) are not rows (no node outcome).

- **The held-connection count:** it was 8 in all four author runs that reached it (runs 3-6) and in the two earlier
  reviewer runs (reviews 20261118T180137Z and 20261118T182854Z did not list it among their findings), and 7 in this
  reviewer run. Why one connection was not held is not established. A non-exact expectation (at most 8 held, and the 9th and
  10th dropped) would make the check reproducible. That would be round 4, which ruling 3 does not allow.

## New for HQ: rule 518 (TCP fragments) is unreachable, like the RST limit
- **Measured on the applied node:** the peer's TCP-fragmented SYNs (hping3 -f) reached the node's NIC (tcpdump: 8-byte
  fragments). Rule 518 counted none of them, and neither did rule 501.
- **Why:** the kernel's connection tracking reassembles fragments at a hook that runs before the mangle table
  (defragmentation priority -400, mangle -150), so rule 518 only ever sees whole packets.
- **Protective effect:** a fragmented packet is reassembled and then filtered like any other packet, which is the
  effect the drop was meant to give.
- Recommended handling, the same as the RST limit's under ruling 2: no fix, the Phase 5 backlog and the approval
  report. Not done without a ruling.

## Leads (not findings)
- **Rule 002 (127.0.0.0/8 not on lo)** counted none of 3 hand-built frames from the peer, both with route_localnet 0
  (the kernel drops that destination before INPUT) and with route_localnet set to 1 on the node. The second result is
  unexplained.
- **Rule 505 (SYN+FIN)** is shadowed by 501, which drops those packets as INVALID first.
