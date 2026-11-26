# hello_world_flask: authoring notes (the comments of .codex_state/checks/hello_world_flask.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::hello_world_flask (define; harness title hello_world_flask). It deploys a
# Flask app under <localdir>/hello_world_flask/<title> and runs it with gunicorn as the systemd service
# hello-world-flask-<title>. Fixture (params, never committed): ip_address 127.0.0.1, port 8080, welcome_msg
# "P8 test flask hello". Probes talk to the node's own addresses only.
# 2026-11-20 (backfill batch 7): purpose and outcomes (HQ rulings 2 and C1), and the restart chain as behaviour: a hand
# change to the running app is undone by the next agent run, which restarts the service (gunicorn keeps the code it loaded).
# Correction round 1, 2026-11-21 (review 20261121T003328Z, purpose): the unit-change path (a unit changed by hand to bind
# 8081, reloaded and restarted; after the agent run the service must run the configured unit on 8080; the restart exec is
# declared before the daemon-reload exec, so a restart on the stale definition would show here), and the RedHat row.
```
