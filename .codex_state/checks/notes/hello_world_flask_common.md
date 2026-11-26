# hello_world_flask_common: authoring notes (the comments of .codex_state/checks/hello_world_flask_common.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::hello_world_flask_common (class; node ubuntu; required_base filesystem_base,
# and extra_packages_el on RedHat; no parameters, fixture defaults). The shared part of the hello_world_flask demo
# applications: the gunicorn and Flask packages and the directory the applications live in. The exercise serves a
# one-route Flask app with the installed gunicorn on the node's loopback.
# 2026-11-21 (backfill batch 10): first set, with purpose and outcomes (HQ rulings 2 and C1).
  # 2026-11-21 authoring correction (run 1, 20261121T153019Z, FINDINGS): the action called a `gunicorn` command, which
  # python3-gunicorn does not ship on Ubuntu (the module only); the consumer's Debian unit runs `python3 -m gunicorn`
  # (hello-world-flask.service.erb:10), which the action now does. The behaviour is unchanged.
```
