# ssl_base: authoring notes (the comments of .codex_state/checks/ssl_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::ssl_base (define; node ubuntu; required_external nginx). Fixture (params,
# never committed): myprefix p8test, myservice nginx, myservicename nginx; owner/group root and letsencrypt false at
# their defaults. The master's extra_files mount holds the lab's throwaway PKI (master_fixtures.sh): p8test.key and
# p8test.crt are a server key and certificate (CN p8test.invalid), and p8test.intermediate.crt is the throwaway CA's
# certificate that signed it, standing in for an intermediate. Probes read only the node.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): Let's Encrypt material and other owners (production uses both) and
# the RedHat branch are checks in the variant runs `letsencrypt`, `owners` and `rhel`; the other-service warning names
# what is missing.
  # Correction round 2 (2026-11-18, review 20261118T212404Z): the Let's Encrypt row says what nginx_frontend_mail's set
  # covers and what no set covers.
  # Correction round 1 (2026-11-18, review 20261118T211825Z): the variant row claimed other sets cover these
  # variants; none does. It is now three rows that say what is untested and what would lift it.
```
