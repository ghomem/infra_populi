#!/usr/bin/env bash
# Lab idle shutdown (HQ 2026-11-22 ruling 3): the lab was left up after a run and only the battery guard saved it, so
# taking the lab down at a pause no longer depends on memory. Claude Code hooks call this script:
#
#   lab_idle_down.sh arm     (the Stop hook: the advisor's turn ended) mark the turn as ended and start the watcher
#                            unless one runs; idempotent
#   lab_idle_down.sh disarm  (the UserPromptSubmit hook: a new turn starts) clear the mark; the watcher exits at its
#                            next poll
#   lab_idle_down.sh status  print `armed <pid>` or `disarmed`; exit 0 either way
#   lab_idle_down.sh watch   (internal) the watcher
#
# The watcher does not take the lab down the moment a turn ends: turns often end while a background run (a reviewer,
# a harness or phase3 run) still uses the lab, between two steps that hold the lock. It brings the lab down
# (`lab_power.sh down`) only once the turn has ended AND the lab has been idle for P8_IDLE_DOWN_S seconds (default 600):
# no lab lock holder and no lab tool process (P8_LAB_PROC_PATTERN, matched by `pgrep -f`). Any lock holder or lab
# process resets the idle clock. It exits without action when the mark is cleared or no lab VM runs. Its decisions go
# to P8_IDLE_LOG (default ~/.cache/infra_populi/idle_down.log). P8_IDLE_DIR holds the mark and the pid file,
# P8_IDLE_POLL is the poll interval (default 30 s), P8_LAB_POWER overrides lab_power.sh (tests).
set -euo pipefail

TOOLS_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
STATE_DIR="${P8_IDLE_DIR:-${HOME}/.cache/infra_populi}"
MARK="${STATE_DIR}/turn_ended"
PIDFILE="${STATE_DIR}/idle_down.pid"
LOG="${P8_IDLE_LOG:-${STATE_DIR}/idle_down.log}"
POLL="${P8_IDLE_POLL:-30}"
IDLE_S="${P8_IDLE_DOWN_S:-600}"
LAB_POWER="${P8_LAB_POWER:-${TOOLS_DIR}/lab_power.sh}"
PATTERN="${P8_LAB_PROC_PATTERN:-phase3\.py run|test_class\.sh|revert_node\.sh|record_green\.sh|review_class\.py|codex_migrate_class|lab_exec\.sh|lab_power\.sh|snapshot_master\.sh|lab_vm\.sh}"
MASTER_VM="Ubuntu24-puppet8-Master"
mkdir -p "$STATE_DIR"

watcher_pid() {
  local pid
  pid="$(cat "$PIDFILE" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null && printf '%s\n' "$pid"
}

lab_vms_running() {
  local running vms
  running="$(VBoxManage list runningvms 2>/dev/null | sed -n 's/^"\(.*\)" {.*}$/\1/p')"
  vms="$(printf '%s\n' "$MASTER_VM"; python3 "${TOOLS_DIR}/nodes.py" list 2>/dev/null | awk '{print $3}')"
  grep -qxF -f <(printf '%s\n' "$vms") <<<"$running"
}

lab_busy() {
  [[ -n "$("${TOOLS_DIR}/lab_lock.sh" holder 2>/dev/null || true)" ]] && return 0
  pgrep -f -- "$PATTERN" >/dev/null 2>&1
}

log() { echo "$(date -u +%FT%TZ) $*" >>"$LOG"; }

case "${1:-}" in
  arm)
    if ! lab_vms_running; then
      log "turn ended with no lab VM running: nothing to watch"
      rm -f "$MARK"
      exit 0
    fi
    date -u +%s >"$MARK"
    if watcher_pid >/dev/null; then
      exit 0
    fi
    # Detached, with stdio on /dev/null and every other inherited descriptor closed (it outlives the hook).
    setsid "$0" watch </dev/null >/dev/null 2>&1 8>&- 9>&- &
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      watcher_pid >/dev/null && exit 0
      command -p sleep 0.2
    done
    echo "lab_idle_down: the watcher did not start" >&2
    exit 1
    ;;
  disarm)
    rm -f "$MARK"
    ;;
  status)
    if [[ -f "$MARK" ]] && pid="$(watcher_pid)"; then echo "armed $pid"; else echo "disarmed"; fi
    ;;
  watch)
    echo "$$" >"$PIDFILE"
    trap 'rm -f "$PIDFILE"' EXIT
    idle_since="$(date +%s)"
    while [[ -f "$MARK" ]]; do
      if ! lab_vms_running; then
        log "no lab VM runs any more: nothing to do"
        rm -f "$MARK"
        exit 0
      fi
      now="$(date +%s)"
      if lab_busy; then
        idle_since="$now"
      elif ((now - idle_since >= IDLE_S)); then
        log "turn ended and the lab idle for ${IDLE_S}s (no lock holder, no lab process): lab_power.sh down"
        rm -f "$MARK"
        "$LAB_POWER" down </dev/null >>"$LOG" 2>&1 || log "lab_power.sh down failed"
        exit 0
      fi
      command -p sleep "$POLL"
    done
    log "disarmed: a new turn started"
    ;;
  *)
    echo "usage: $0 arm|disarm|status|watch" >&2
    exit 2
    ;;
esac
