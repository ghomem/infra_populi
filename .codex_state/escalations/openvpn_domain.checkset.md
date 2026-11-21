# openvpn_domain — Phase 3 check set past its correction cap (OPEN, for HQ)

Production use 0 (migration_order.md `prod` column), so the cap is two correction rounds (HQ batch-12 ruling 3). Both
were used and the third review failed on purpose with no findings. The run continues; this set awaits a ruling.

## Reviews
| review | verdict | gap named | correction |
|---|---|---|---|
| 20261121T042709Z | FAIL (purpose) | the Kerberos configuration (krb5.conf) without a row | round 1: `kerberos-realms-against-the-dc` |
| 20261121T050106Z | FAIL (purpose) | host resolution through WINS (nsswitch `hosts: ... wins`) without a row | round 2: `the-dc-name-resolves-through-wins` |
| 20261121T051116Z | FAIL (purpose) | `winbind use default domain = yes` untested | none (cap reached) |

The third reviewer's reason, verbatim:

> Left out, lab-exercisable and not in the outcomes table: templates/openvpn/smb.conf.erb:19 'winbind use default
> domain = yes' — its observable effect is that domain users resolve and log in by their UNQUALIFIED name
> (p8testvpnin, not P8TEST+p8testvpnin), which is the name a VPN user types (openvpn_server.pp:168-169
> username_as_common_name + pam through login). Every resolution and login probe uses a qualified form
> (p8testuser@P8TEST.example, 'P8TEST+p8testvpnin'), which works with or without that line, so the setting is untested;
> the lab can exercise it with the same peer and fixture users (e.g. id -nG p8testvpnin and pamtester login
> p8testvpnin). Outcome 1 cites smb.conf.erb wholesale but no outcome states this effect; no uncovered row lists it.

## What the set covers now (last run 20261121T050438Z-author, ALL_PASS; reviewer run reproduced it)
smb.conf member settings; the join (testjoin, the machine account on the DC); users and groups through winbind; the
pam_winbind group requirement and /etc/pam.d/openvpn byte for byte; PAM logins through `login` (member accepted, wrong
password and non-member refused, the DC accepting the non-member's password); Kerberos realms against the DC; WINS host
resolution.

## Options
- **A (recommended): allow one more round** for the unqualified name: extend `pam-logins-through-winbind` with
  `id -nG p8testvpnin` and a pamtester login as `p8testvpnin` (no domain prefix), the same peer users. One check
  changes; nothing else moves. The gap is real and is the name form a VPN user types.
- **B: accept the set as it stands** and add an `uncovered` row for the unqualified name (lifted by the round A
  would spend), recorded in the approval report.

## Observations from this set (also in the batch 8 report)
- The Kerberos default realm is `<netbios>.<tld>` as given; with a lowercase tld it differs in case from the AD
  realm and kinit without a realm fails. Whether production is affected depends on its `domain_tld` parameter.
- With the DC powered off (the runner stops the peer after a run), an SSH login to the node did not complete in
  400.1 s; with the DC started again it took 7.5 s. Winbind vs DNS not attributed.
- /etc/pam.d/openvpn (password lines only) is used by no baseline service: unreachable rule, approval report.
