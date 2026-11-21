# hello_world_flask — behaviour finding: a changed unit is restarted before systemd reloads it (2026-11-21)

Status: BEING FIXED under policy B (one clear minimal fix): local change #16. Reproduced by the reviewer
(checks/reviews/hello_world_flask/20261121T004402Z.json, set PASS with this finding, purpose covered).

## What happens
- The unit file notifies two refreshonly execs: `systemctl restart hello-world-flask-<title>` and
  `systemctl daemon-reload` (manifests/hello_world_flask.pp:28, 72, 84-91 at the baseline).
- Nothing orders them, so Puppet runs them in manifest order: the restart first.
- systemd keeps a unit's loaded definition until a reload, so the restart runs the stale definition.

## Evidence
Run results/hello_world_flask/20261121T003706Z-author (check the-agent-run-restores-the-unit-in-effect):
- the unit had been changed by hand to bind 127.0.0.1:8081, then reloaded and restarted;
- the next agent run restored the file (`content changed ... (corrective)`), then triggered `-restart`, then `-reload`;
- afterwards the file reads 8080, but the service still serves 8081, and 8080 refuses.

Any Puppet-driven change to the unit (a new port or address) would take effect only at a later restart.

## Fix (local change #16)
Order the daemon-reload exec before the restart exec
(`Exec["hello-world-flask-${title}-reload"] -> Exec["hello-world-flask-${title}-restart"]`). This is a relationship
only: an app-file change still notifies the restart alone.
