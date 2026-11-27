#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Lab access (HQ 2026-11-20, after batch 16, item 3): every command run by hand on a lab machine goes through here.
#
#   lab_exec.sh <lab host> [remote command...]     stdin is passed through (`lab_exec.sh host 'sudo bash -s' <<'EOF'`)
#
# It takes the lab lock (lab_lock.sh) for as long as the command runs, so it refuses while another run holds the lab
# and no run starts under it. Found 2026-11-20: a command run on the node while a reviewer's run held the lab was cut by
# that run's revert. Inside an engine run that holds the lock already (P8_LAB_LOCKED=1) the command just runs.
# Lab hosts: the master's aliases (puppet8master, puppet8master-rsync), the node inventory's aliases (nodes.py list) and
# puppet8node-rsync. Exit: the remote command's status; 1 refused (the holder on stderr); 2 usage or not a lab host.
# A PreToolUse hook (hooks/lab_ssh_guard.py) refuses ssh/scp/sftp/rsync to a lab host that does not come through here.
# ---------------------------------------------------------------------------
set -euo pipefail

TOOLS="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

usage() { sed -n '4,6p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
[[ $# -ge 1 && "$1" != -* ]] || usage
HOST="$1"
shift

lab_hosts() {
  printf '%s\n' puppet8master puppet8master-rsync puppet8node-rsync
  python3 "${TOOLS}/nodes.py" list 2>/dev/null | awk '{print $4}'
  python3 "${TOOLS}/nodes.py" services 2>/dev/null | awk '{print $3}'  # the lab's services (the apt cache)
}
# matched against the captured list: `lab_hosts | grep -q` would fail under pipefail when grep stops at an early match
hosts="$(lab_hosts)"
grep -qxF -- "$HOST" <<<"$hosts" || { echo "LAB_EXEC: '${HOST}' is not a lab host ($(paste -sd' ' <<<"$hosts"))" >&2; exit 2; }

if [[ "${P8_LAB_LOCKED:-}" != 1 ]]; then
  if ! out="$("${TOOLS}/lab_lock.sh" take "$$" "lab_exec.sh ${HOST}" 2>&1)"; then
    echo "LAB_EXEC REFUSED: ${out}" >&2
    exit 1
  fi
  trap '"${TOOLS}/lab_lock.sh" release "$$" >/dev/null 2>&1 || true' EXIT
fi

rc=0
ssh -T "$HOST" "$@" || rc=$?
exit "$rc"
