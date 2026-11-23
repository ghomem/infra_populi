# rsyslog_client — behaviour finding: rsyslog 8.2312 rejects a parameter of the forward_auth_log input (OPEN, for HQ: more than one reasonable fix)

Found by the sweep's variant run `options` (results/rsyslog_client/20261123T130958Z-author.json, check
`options-render-the-forwarding-rules`): with check_names, a failover target and forward_auth_log, every rendered rule is
there, but `rsyslogd -N1` does not complete its validation run. Reproduced by hand on 2026-11-23 (the harness with the
same params variant on a reverted node, then `rsyslogd -N1` and rsyslog's journal), verbatim:

    rsyslogd: error during parsing file /etc/rsyslog.d/40-forward.conf, on or before line 58: parameter 'deleteStateOnFileMove' not known -- typo in config file? [v8.2312.0 try https://www.rsyslog.com/e/2207 ]

The running rsyslogd logs the same error at its start (journalctl -u rsyslog). The node runs rsyslog 8.2312.0 (Ubuntu
24.04).

## The baseline
templates/rsyslog/forward_simple.conf.epp:65-77 renders, when forward_auth_log is true, an imfile input for
/var/log/auth.log bound to the forward_authlog_only ruleset, with `deleteStateOnFileMove="on"` (:75). rsyslog 8.2312
has no such imfile parameter.

## Effect
- rsyslog still creates the input: its imfile state file for auth.log exists after the start
  (/var/spool/rsyslog/imfile-state:393361:..., 2026-11-23). Whether the forwarded auth lines reach the server is not
  tested here: a variant run has no peer.
- rsyslog reports a configuration error at every start, and `rsyslogd -N1` (the only configuration check) fails.

## Production use
One production node statement sets forward_auth_log on rsyslog_client (diagnosis/fleet_variant_usage.md; names and
counts only, its value is not read).

## Where rsyslog knows the parameter
- Ubuntu 24.04, rsyslog 8.2312.0: not known (above).
- RHEL 9.5 (lab node rhel9), rsyslog 8.2310.0-4.el9: not known. Measured 2026-11-23: an imfile input with only this
  parameter added, checked with `rsyslogd -N1 -f`, gives the same "parameter 'deleteStateOnFileMove' not known".
- The parameter began as a Red Hat downstream patch (Red Hat bug 1909639, rsyslog 8.2102.0 in RHEL 8); AlmaLinux's el9
  packaging reintroduces it with the rebase to 8.2412.0 (commit "imfile: reintroduce deleteStateOnFileMove parameter").
  These are web sources, not measured here: later RHEL 9 point releases may know it, and the production node's release
  is not known (its node statement is read by names only).

## Options (escalated under the run rule: more than one reasonable design; the run continues)
- **A (recommended): remove `deleteStateOnFileMove="on"`** from the template. Both lab target releases reject it, so
  nothing changes there but the error. On an rsyslog that knows it, a moved auth.log would keep its state file.
- **B: render it only where rsyslog knows it**, by a fact or a parameter. This keeps the setting where it works, but
  needs a version test the class does not have today.
- **C: no change**, recorded in the approval report: the input works and only the error and `rsyslogd -N1` are affected.

The check stays as it is; it fails until A or B is made (before evidence: the run above).
Hazard 11: the template's only consumer is rsyslog_client (to be confirmed by `git grep` at the baseline when a change
is made).
