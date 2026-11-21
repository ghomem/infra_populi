# postfix_smtp_base — Phase 3 check set past its correction cap (OPEN, for HQ)

Production use 0 (migration_order.md `prod` column), so the cap is two correction rounds (HQ batch-12 ruling 3). Both
were used and the third review failed on purpose with no findings. The run continues; this set awaits a ruling.

## Reviews
| review | verdict | gap named | correction |
|---|---|---|---|
| 20261121T052303Z | FAIL (purpose) | plaintext never tried (TLS mandatory); a system account never tried | round 1: `tls-and-own-users-only` |
| 20261121T053246Z | FAIL (purpose) | no message accepted or delivered (every session reset at RCPT) | round 2: `a-submission-is-queued-and-delivered-locally`; remote relay as an uncovered row |
| 20261121T054226Z | FAIL (purpose) | relay to a non-local domain untested; the uncovered rows' evidence does not hold | none (cap reached) |

The third reviewer's reason, verbatim:

> Left out although the lab CAN exercise it: the class's main job, relaying an authenticated user's mail to a
> non-local domain. No check sends RCPT to a remote recipient (every session uses root@localhost, so relay acceptance
> under smtpd_relay_restrictions, main.cf.erb:73, is never observed) and no message leaves through postfix's smtp
> client. The uncovered row 'onward delivery to a remote domain's MX' (new in round 2) gives as evidence 'nodes.yml
> lists no mail-sink node kind', but nodes.yml has active kinds with capability second-node (ubuntu2 192.168.56.24, dc)
> and phase3.py supports a peer block with P8_PEER_ADDR for node actions: a sink on the peer reached through an
> address-literal recipient (user@[peer IP]; relayhost is empty, so the smtp transport delivers straight there, no MX
> lookup or internet needed) exercises the onward-delivery path. The evidence therefore does not show the lab lacking
> it. The same path carries smtp_header_checks (main.cf.erb:121, smtp client only), so the From-header WARN row is also
> exercisable: its second reason, the empty do_not_warn_from_addresses_regexes, is a params-fixture choice (the
> fixture was already extended for p8testuser2), not a missing lab capability. The extra_sec / Let's Encrypt row (one
> params fixture per set) is an honest limitation.

The advisor agrees: the round-2 uncovered row's evidence was wrong. The lab has a second node, and an address-literal
recipient needs no MX.

## What the set covers now (last run 20261121T053528Z-author, ALL_PASS; reviewer run reproduced it)
Banner, port and host name; the sslprefix certificate over STARTTLS; TLS mandatory (530 before STARTTLS, no AUTH
offered); dovecot passwd-file SASL and an OS account refused; the client, sender and login-map restrictions in seven
sessions; one submission queued and delivered to the local mailbox.

## Options
- **A (recommended): allow a third round** using the ubuntu2 peer as a mail sink. The peer listens on 25 and records
  what it receives. The node submits as p8testuser to `p8test@[<peer address>]`: relay accepted (250 at RCPT),
  delivered by the smtp client, and received on the peer. With a params fixture entry
  `do_not_warn_from_addresses_regexes` (for example `p8test@p8test\.example\.com`), a second message with another
  From header shows the WARN line on the node. Both uncovered rows are lifted except extra_sec / Let's Encrypt.
- **B: accept the set as it stands**, with the two rows' evidence corrected to "exercisable with a peer sink, not
  done", recorded in the approval report.
