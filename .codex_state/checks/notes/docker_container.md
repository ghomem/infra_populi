# docker_container: authoring notes (the comments of .codex_state/checks/docker_container.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::docker_container (define; node ubuntu; required_external docker, the
# puppetlabs-docker module's class). Fixture (params, never committed): title docker_container (the plan's), image
# nginx, tag alpine, app_port 80, host_port 18080; no registry login, digest, volumes, env or command; network bridge.
# The container is named after the title, and puppetlabs-docker 10.4.1 runs it as systemd unit docker-<title>. Probes
# read the node's own docker and loopback.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): environment, a named volume, a command and another network
# (production uses them) are checks in the variant runs `runopts` and `nonet`; digest is an accepted gap; the registry
# login and the image-change recreation name what is missing.
# Correction round 1 of the swept set (2026-11-25, review 20261125T174809Z, purpose): (1) the image-change row was
# uncovered for a false reason: with ensure present the module pulls only when the image is missing locally, so a check
# removes the image's tag and the next agent run pulls it again and, through the subscribe, restarts the container
# (the row now says restarted: the service is refreshed, its container kept). (2) The runopts command equalled the
# image's own CMD; it now adds worker_rlimit_nofile 4096, read from the container's config and its PID 1. (3) The
# host_port fallback (production: 4 of 7 statements set app_port without host_port) is the variant `appport`; ensure,
# set on 1 statement, is a row of its own, uncovered with the module's evidence.
# 2026-11-25 authoring correction (run 20261125T175156Z-author): the agent run pulled the image again and the container
# restarted (new start time), but the app check ran at the instant of the restart and read 0; it now waits up to 15 s
# for nginx to answer, as a restarted container needs a moment before its port serves.
# Correction round 2 of the swept set (2026-11-25, review 20261125T190511Z, purpose): remove_container_on_stop false
# (line 89, against the module's default true) had no row; a check stops the service and finds the container kept,
# exited. Two statements of round 1 were wrong and are corrected: the image-change refresh recreates the container (the
# module's start script removes it before creating it), so the check now compares the container ID; and the restart
# after a kill comes from the unit puppetlabs-docker writes for the class's docker::run (Restart=on-failure by
# default), not from restart_service_on_docker_refresh, which acts only with docker_service set.
# Correction round 3 of the swept set (2026-11-25, review 20261125T194651Z, purpose): lines 59-80 split volumes into
# named volumes (created by an exec) and host paths (passed to docker::run as bind mounts); only the named kind was
# tested. The runopts fixture now also has the host path /srv/p8test-bind:/p8test-bind, and its check reads the bind
# mount and that no docker volume but p8test-vol was created.
  # 2026-11-18 authoring correction (run 1, 20261118T221532Z): nginx's welcome page names nginx in its title and its
  # heading, so the count was 2; the heading alone is counted now (here and in the restart check).
```
