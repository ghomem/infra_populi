# Escalation: ssl_base — local manifest predates the declared baseline (baseline drift)

Date: 2026-10-01. Same systemic issue and options as `.codex_state/escalations/rsyslog_server.md`;
one ruling resolves both. Raised pre-Codex (Codex not invoked).

## Evidence
- `manifests/ssl_base.pp` is byte-identical to upstream `2388bd7` (2025-02-20, "issue #63: final change").
- release-0.9.8 adds 4 later commits (726fd99, a4a93ca, 8448c17, 5d6b012, 2025-11-07..11):
  - new params `String $owner = 'root'`, `String $group = 'root'` applied to the resulting files
    (defaults reproduce current behaviour);
  - notify resource fixed: local title is SINGLE-quoted, so `${myservice}` is never interpolated, and it
    lacks `${myprefix}`, so two ssl_base instances notifying services would collide on a duplicate
    title. 0.9.8 double-quotes it and includes the prefix ("make notify unique").
- Templates/files: none involved.

## Note for the ruling
Unlike rsyslog_server, syncing ssl_base to 0.9.8 is behaviour-neutral at default params apart from
the notify message/title fix. If option A is adopted it is the lowest-risk first sync.
