#!/usr/bin/env bash
# One lab run at a time (2026-11-16, batch 4). Every engine run that writes the master's node file or acts on the
# node (test_class.sh in every mode but --render-only, revert_node.sh, phase3.py run) holds this lock; a second one
# refuses at once instead of rewriting the master's node file or reverting the node under the first. Found when an
# advisor compile-only for the next class rewrote the node file in the middle of a reviewer's harness apply.
#
#   lab_lock.sh take <owner-pid> <description...>   exit 0 = held by <owner-pid>; 1 = held by another live process
#                                                    (its line on stderr). A holder that is no longer alive is replaced.
#   lab_lock.sh release <owner-pid>                  drops the lock if <owner-pid> holds it
#   lab_lock.sh holder                               prints the live holder's line, if any
#
# The lock is a holder line ("<pid> <UTC> <description>") in a file, read and written under a short flock on a
# separate mutex: no file descriptor stays open in the holder, so long-lived children (an ssh ControlMaster, a VBoxSVC
# started by VBoxManage) cannot keep the lock alive after the run. Callers export P8_LAB_LOCKED=1 so their children
# (the revert inside a --revert-first harness, the harness inside a phase3 run) do not try to take it again.
# P8_LAB_LOCK overrides the lock path (tests).
set -euo pipefail

LOCK="${P8_LAB_LOCK:-${HOME}/.cache/infra_populi/lab.lock}"
mkdir -p "$(dirname "$LOCK")"

holder_pid() { [[ -s "$LOCK" ]] && cut -d' ' -f1 "$LOCK" || true; }
alive() { local pid; pid="$(holder_pid)"; [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; }

case "${1:-}" in
  take)
    [[ $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || { echo "usage: $0 take <owner-pid> <description...>" >&2; exit 2; }
    pid="$2"; shift 2
    exec 8>"${LOCK}.mutex"
    flock -x 8
    if alive && [[ "$(holder_pid)" != "$pid" ]]; then
      cat "$LOCK" >&2
      exit 1
    fi
    printf '%s %s %s\n' "$pid" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >"$LOCK"
    ;;
  release)
    [[ $# -eq 2 ]] || { echo "usage: $0 release <owner-pid>" >&2; exit 2; }
    exec 8>"${LOCK}.mutex"
    flock -x 8
    if [[ "$(holder_pid)" == "$2" ]]; then rm -f "$LOCK"; fi
    ;;
  holder)
    if alive; then cat "$LOCK"; fi
    ;;
  *)
    sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 2
    ;;
esac
