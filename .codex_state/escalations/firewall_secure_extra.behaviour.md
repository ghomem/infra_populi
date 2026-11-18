# firewall_secure_extra — behaviour findings, and a check set escalated after two correction rounds (2026-11-18)

Status: OPEN, for HQ.
- Two behaviour findings, which stop the backfill under start rule 1.
- The check set is escalated: it did not reach PASS after two correction rounds.

The migration did not cause the findings: the baseline's own rule numbering produces them, under the ordering the
firewall module documents. They are purpose defects of the baseline. Phase 1 is not affected.

## Production use (measured, names and counts only)
- No production node statement sets node_base's `firewall_secure_extra => true` (0 of 38). node_base declares the
  class only inside `if ($firewall_secure_extra)` (node_base.pp:82), and its default is false.
- No file in the fleet repository, outside `passwd/`, names the class or any of the parameters `ip_blacklist`,
  `anti_ddos`, `ip_filter` or `country_whitelist`.
- No production node uses the class. The fleet usage table's row (58) counts the conditional declaration as
  unconditional; its own `conditional` column says so. I ordered batch 2 by that count without discounting it (see
  the batch report).

## The cause
puppetlabs-firewall orders rules by the number in their title. The README of the lab's 8.3.0 (line 206) says: "All
rules employ a numbering system in the resource's title that is used for ordering". Which version production runs is
not in the records; it is a production read. A rule with no `proto` gets the type's default, `tcp`
(lib/puppet/type/firewall.rb:283 in 8.3.0, read by the reviewer).

Rule order on the applied node (`iptables -S INPUT`):

| rule | what it does |
|---|---|
| `000 ICMP limit` | ACCEPT echo-request at 2/s |
| `000 icmp drop` | drop the rest of ICMP |
| `001`, `002` | loopback |
| `003 accept related established rules` | ACCEPT |
| `100 SSH whitelist` | ACCEPT |
| `110 SSH LIMIT_INDIVIDUAL` | jump; LIMIT_OVERALL then accepts at 20/min |
| `111 SSH ACCEPT ESTABLISHED` | ACCEPT |
| `519 limit RST tcp packets` | ACCEPT at 2/s, burst 2 |
| `520 limit RST tcp packets (default behavior)` | DROP |
| `521 sidechain redirecting by mark` | jump |
| `666 grounding naughty boys: <ip>` | `-p tcp`, DROP |

## Finding 1: the blacklist does not drop TCP from a blacklisted source
- **What the code declares:** lines 125-127 put rule 666 in INPUT for each `ip_blacklist` source. It has no
  `proto`, so it drops TCP only. The parameter comment (line 25) says "dropped unconditionally"; it is a lead, and it
  claims more than the code: ICMP is never in scope.
- **Check** `a-blacklisted-source-gets-nothing`. The SSH half is correctly derived; it failed in every run (author
  runs 1-5, reviewer runs 20261118T171524Z and later): `ssh from blacklisted in`.
- **Why:** rule 666 comes after every rule that accepts TCP (003, 100, 110-117, 521 and, without anti_ddos, 555), and
  no rule after it accepts anything. So in any configuration of the class, it drops only what the INPUT policy would
  drop anyway.

## Finding 2: the RST limit is never reached
- **Check** `the-rst-limit-dropped-the-third`. The peer resets 3 connections to the service at once (3 RSTs inside
  connections). Expected from lines 187-190: 519 accepts 2 and 520 drops 1. Every run measured 0 and 0. Reproduced
  by hand: the 3 resets closed the node's connections, and 003's counter rose.
- **Why:** an RST inside a connection is ESTABLISHED to conntrack, so rule 003 accepts it first. An RST outside any
  connection is INVALID, so mangle rule 501 drops it before INPUT (measured: 50 of 50 counted by 501, none by 519 or
  520). No RST can reach 519 or 520. An RST flood is still dropped, by 501 (`the-invalid-and-not-syn-rules-dropped-them`
  passes).

## Withdrawn: "fragmented packets are not dropped" (my derivation error)
- Run 5's check `a-fragmented-ping-gets-no-reply` sent ICMP fragments. Rule 518 (lines 184-185) has no `proto`, so it
  matches TCP fragments only (`-p tcp -f` on the node). The check tested something the code does not say.
- **Lead:** 5 TCP-fragmented SYNs sent by hand with `hping3 -f` were counted 0 by rule 518 and 0 by 501, and got no
  reply. That is unexplained, and no check has covered it yet.

## The check set (escalated after two correction rounds)
| review | verdict | what was wrong |
|---|---|---|
| 20261118T172004Z | FAIL | ICMP check flaky; a setup check cited rules its packets never reach; purpose gaps (flush script, SSH limits as rule text, RST limit) |
| 20261118T180137Z (after round 1) | FAIL | Purpose gaps: rule 503 was testable; 518 had no check; no rows for anti_ddos without ip_filter or for loopback |
| 20261118T182854Z (after round 2) | FAIL | Derivation: 666 and 518 are tcp-only by the type's default, so the blacklist-ICMP and fragmented-ICMP expectations were wrong; purpose: TCP fragments untested; the rule-002 row's lifted_by names the default node, which cannot show it |

The last review accepts every other derivation. The other 22 checks pass, including:
- the three SSH limits as connection behaviour;
- the side-chain whitelist, the connection limit and the rate limit;
- rules 501, 502 and 503 read from their counters;
- the ICMP limit;
- loopback;
- the purge, and the flush script with the rebuild that follows it.

**Proposed round 3, not done (the rule caps corrections at two):**
- the blacklist check expects only SSH dropped;
- the fragment check sends TCP fragments with `hping3 -f` and reads rule 518;
- the outcome rows say tcp where the code does;
- rule 002's `lifted_by` names a node with route_localnet=1, which the lab does not have, or the row says so.

HQ decides whether a third round runs.

## Options for the findings (more than one reasonable design, so policy B does not apply without a ruling)
- **A. Renumber.**
  - The blacklist gets a title that sorts before every accept (below 000). It keeps the default proto (TCP), or adds
    `proto => 'all'` to match the comment's "unconditionally"; that is a choice of its own.
  - The RST pair gets titles that sort before 003.
  - Local change with `--local-change`; both checks should pass after.
- **B. Move the blacklist to mangle PREROUTING**, before the marking rules (131313), beside the other anti-DDoS drops.
  The RST pair stays where it is, or is removed as redundant with 501, which would be removing functionality.
- **C. No fix.** Record both as known baseline defects in the documentation list. The findings stay, and the approval
  report asks Salatiel to accept them explicitly, since no production node uses the class.

**Recommendation: C.** No production node uses the class. A and B change firewall behaviour that a site enabling it
would notice, so they belong with a site that wants the class. If HQ prefers a fix, **A** without `proto => 'all'` is
the smallest change.

## Leads (measured by hand, not checks)
- **Rule 505 (SYN+FIN) is shadowed by 501:** 5 sent, 5 counted by 501, 0 by 505.
- **Rule 002 (127.0.0.0/8 not on lo):** 3 hand-built Ethernet frames from the peer to 127.0.0.1 through the node's
  NIC were counted 0 by rule 002. route_localnet is 0 on the node, so the kernel drops that destination before
  INPUT. The outcome (not delivered) holds, but not by the rule.
