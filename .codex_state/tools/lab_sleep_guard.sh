#!/usr/bin/env bash
# Lab sleep guard (HQ batch-15 follow-up, 2026-11-19): a laptop suspend while lab VMs ran left both VMs in Guru
# Meditation on resume (VERR_VMX_INVALID_VMXON_PTR, kvm_intel loaded beside VirtualBox). The runs' own inhibitors
# (test_class.sh, phase3.py) covered only the runs, not the gaps between them. This guard blocks sleep for as long as
# any lab VM runs and releases the block when the last one stops.
#
#   lab_sleep_guard.sh ensure   start the guard unless one is alive (idempotent; the VM-starting tools call it)
#   lab_sleep_guard.sh status   print `held <pid>` or `none`; exit 0 either way
#   lab_sleep_guard.sh release  stop the guard now, if one runs (lab_power.sh down, after the last VM stopped)
#   lab_sleep_guard.sh hold     (internal) the guard itself, run under systemd-inhibit: polls the running VMs and exits
#                               when no lab VM runs, which releases the inhibitor
#
# Lab VMs: the master and every `vm` of the node inventory (nodes.py list). The guard detaches with every inherited
# descriptor closed, so it holds no caller's pipe or lock. A laptop without logind's inhibitor runs no guard (status
# says none). P8_SLEEP_GUARD_PID overrides the pid file, P8_SLEEP_GUARD_POLL the poll interval in seconds, and a
# non-empty P8_NO_SLEEP_GUARD makes `ensure` start nothing (the stub lab of the tests). The guard sleeps with the
# system's sleep (`command -p`), never a stub found on PATH: a stub that returns at once would make it spin.
set -euo pipefail

TOOLS_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PIDFILE="${P8_SLEEP_GUARD_PID:-${HOME}/.cache/infra_populi/sleep_guard.pid}"
POLL="${P8_SLEEP_GUARD_POLL:-30}"
MASTER_VM="Ubuntu24-puppet8-Master"
mkdir -p "$(dirname "$PIDFILE")"

guard_pid() {
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

case "${1:-}" in
  ensure)
    [[ -z "${P8_NO_SLEEP_GUARD:-}" ]] || exit 0
    if pid="$(guard_pid)"; then
      exit 0
    fi
    command -v systemd-inhibit >/dev/null || exit 0
    # Detached, with stdio on /dev/null and every other inherited descriptor closed.
    setsid systemd-inhibit --what=sleep --who=infra_populi-lab --why="lab VMs are running" --mode=block \
      "$0" hold </dev/null >/dev/null 2>&1 8>&- 9>&- &
    for _ in 1 2 3 4 5 6 7 8 9 10; do
      guard_pid >/dev/null && exit 0
      command -p sleep 0.2
    done
    echo "lab_sleep_guard: the guard did not start" >&2
    exit 1
    ;;
  hold)
    echo "$$" >"$PIDFILE"
    trap 'rm -f "$PIDFILE"' EXIT
    while lab_vms_running; do
      command -p sleep "$POLL"
    done
    ;;
  status)
    if pid="$(guard_pid)"; then echo "held $pid"; else echo "none"; fi
    ;;
  release)
    if pid="$(guard_pid)"; then kill "$pid" 2>/dev/null || true; rm -f "$PIDFILE"; fi
    ;;
  *)
    echo "usage: $0 ensure|status|release|hold" >&2
    exit 2
    ;;
esac
