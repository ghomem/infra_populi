#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TRACKED TOOLING. This script is version-controlled because it encodes the
# clean-baseline recovery contract for the Puppet 8 test node:
# revert_node.sh restores, starts, and verifies that node. It may also start
# and verify the master, but never performs a destructive master VM action.
# Tracking this safety-critical lifecycle tool keeps that boundary and its
# host assumptions reviewable. See DESIGN_DECISIONS.md.
#
# NOT host-portable as-is. Host-specific assumptions:
#   node VM       ubuntu24-puppet8-Node
#   master VM     Ubuntu24-puppet8-Master  (may start; never restore/power off/reset)
#   node snapshot P8NODE_BASELINE_GREEN_v2 (offline; GRUB_RECORDFAIL_TIMEOUT=2,
#                 apt timers off, NIC2 host-only vboxnet0 — sprint step 3.1);
#                 its apt lists are refreshed after every restore (apt-get update)
#   SSH aliases   puppet8node, puppet8master
#   Wi-Fi bridge  host interface wlo1 (typically takes about 45s to settle)
#   master check  puppet8master.example.com:8140, opened from the node
# Parameterizing these via environment variables is a known future improvement.
#
# Node power-off is a HARD poweroff (ruling 5, 2026-10-26): the node is restored
# from an offline snapshot immediately afterwards, so a graceful shutdown buys
# nothing. The master is never powered off, reset or restored by this script.
# Last line on success: REVERT_METRICS {json} with phase timings (step 3.4).
# ---------------------------------------------------------------------------

set -euo pipefail

readonly NODE_VM="ubuntu24-puppet8-Node"
readonly MASTER_VM="Ubuntu24-puppet8-Master"
readonly NODE_SNAPSHOT="P8NODE_BASELINE_GREEN_v2"
readonly NODE_SSH_ALIAS="puppet8node"
readonly MASTER_SSH_ALIAS="puppet8master"
readonly MASTER_SERVICE_HOST="puppet8master.example.com"
readonly MASTER_SERVICE_PORT="8140"
readonly POWEROFF_TIMEOUT_SECONDS=30
readonly SSH_TIMEOUT_SECONDS=120
readonly POLL_INTERVAL_SECONDS=2
readonly APT_UPDATE_TIMEOUT_SECONDS=180

readonly -a SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=5
  -o ConnectionAttempts=1
  -o LogLevel=ERROR
)

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

ms_to_s() { printf '%d.%03d' "$(($1 / 1000))" "$(($1 % 1000))"; }

vm_state() {
  local vm_name="$1"
  local state

  state="$(
    VBoxManage showvminfo "$vm_name" --machinereadable 2>/dev/null |
      awk -F= '$1 == "VMState" { gsub(/"/, "", $2); print $2; exit }'
  )" || return 1

  [[ -n "$state" ]] || return 1
  printf '%s\n' "$state"
}

require_master_running() {
  local state
  local master_deadline
  local service_output
  local service_status="not reported"

  if ! state="$(vm_state "$MASTER_VM")"; then
    fail "Unable to determine the state of master VM '$MASTER_VM'; no master VM action was attempted."
  fi

  if [[ "$state" != "running" ]]; then
    printf 'Starting master VM %q headless (current state: %s)...\n' "$MASTER_VM" "$state"
    VBoxManage startvm "$MASTER_VM" --type headless ||
      fail "Could not start master VM '$MASTER_VM' from state '$state'; no destructive master VM action was attempted."
  fi

  printf 'Waiting up to %ss for master SSH and puppetserver readiness...\n' "$SSH_TIMEOUT_SECONDS"
  master_deadline=$((SECONDS + SSH_TIMEOUT_SECONDS))
  until ssh "${SSH_OPTIONS[@]}" "$MASTER_SSH_ALIAS" true >/dev/null 2>&1; do
    if ((SECONDS >= master_deadline)); then
      fail "Master '$MASTER_SSH_ALIAS' did not become reachable by SSH within ${SSH_TIMEOUT_SECONDS}s (initial VM state: '$state')."
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done

  while true; do
    service_output=""
    if service_output="$(ssh "${SSH_OPTIONS[@]}" "$MASTER_SSH_ALIAS" systemctl is-active puppetserver 2>/dev/null)"; then
      service_output="${service_output//$'\r'/}"
      service_output="${service_output//$'\n'/}"
      if [[ "$service_output" == "active" ]]; then
        return 0
      fi
    fi

    service_output="${service_output//$'\r'/}"
    service_output="${service_output//$'\n'/}"
    [[ -n "$service_output" ]] && service_status="$service_output"

    if ((SECONDS >= master_deadline)); then
      fail "Master '$MASTER_SSH_ALIAS' is reachable, but puppetserver did not report active within ${SSH_TIMEOUT_SECONDS}s (last reported state: '$service_status')."
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done
}

# Milliseconds since the epoch from bash itself (uutils `date` ignores the %3N width).
now_ms() {
  local us="${EPOCHREALTIME//[.,]/}"
  printf '%s\n' "$((us / 1000))"
}

t_start="$(now_ms)"
require_master_running
t_master="$(now_ms)"

if ! node_state="$(vm_state "$NODE_VM")"; then
  fail "Unable to determine the state of node VM '$NODE_VM'."
fi

case "$node_state" in
  poweroff | aborted | saved)
    printf 'Node VM %q is not running (state: %s).\n' "$NODE_VM" "$node_state"
    ;;
  running | paused | stuck | gurumeditation)
    printf 'Hard poweroff of node VM %q (state: %s)...\n' "$NODE_VM" "$node_state"
    VBoxManage controlvm "$NODE_VM" poweroff ||
      fail "Could not power off node VM '$NODE_VM'."

    poweroff_deadline=$((SECONDS + POWEROFF_TIMEOUT_SECONDS))
    while true; do
      if ! node_state="$(vm_state "$NODE_VM")"; then
        fail "Lost the state of node VM '$NODE_VM' while waiting for poweroff."
      fi

      [[ "$node_state" == "poweroff" || "$node_state" == "aborted" ]] && break

      if ((SECONDS >= poweroff_deadline)); then
        fail "Node VM '$NODE_VM' did not reach poweroff within ${POWEROFF_TIMEOUT_SECONDS}s (state: '$node_state')."
      fi

      sleep "$POLL_INTERVAL_SECONDS"
    done
    ;;
  *)
    fail "Node VM '$NODE_VM' is in state '$node_state'; refusing to act on it."
    ;;
esac
t_off="$(now_ms)"

printf 'Restoring node snapshot %q...\n' "$NODE_SNAPSHOT"
VBoxManage snapshot "$NODE_VM" restore "$NODE_SNAPSHOT" ||
  fail "Could not restore snapshot '$NODE_SNAPSHOT' on node VM '$NODE_VM'."

current_snapshot="$(
  VBoxManage showvminfo "$NODE_VM" --machinereadable 2>/dev/null |
    awk -F= '$1 == "CurrentSnapshotName" { gsub(/"/, "", $2); print $2; exit }'
)"
[[ "$current_snapshot" == "$NODE_SNAPSHOT" ]] ||
  fail "After restore the current snapshot is '$current_snapshot', expected '$NODE_SNAPSHOT'."
t_restore="$(now_ms)"

printf 'Starting node VM %q headless...\n' "$NODE_VM"
VBoxManage startvm "$NODE_VM" --type headless ||
  fail "Could not start node VM '$NODE_VM'."

printf 'Waiting up to %ss for SSH while the wlo1 bridge settles...\n' "$SSH_TIMEOUT_SECONDS"
ssh_deadline=$((SECONDS + SSH_TIMEOUT_SECONDS))
until ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" true >/dev/null 2>&1; do
  if ((SECONDS >= ssh_deadline)); then
    fail "Node '$NODE_SSH_ALIAS' did not become reachable by SSH within ${SSH_TIMEOUT_SECONDS}s."
  fi

  sleep "$POLL_INTERVAL_SECONDS"
done
t_ssh="$(now_ms)"

if ! node_hostname="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" hostname)"; then
  fail "Node '$NODE_SSH_ALIAS' stopped responding during hostname verification."
fi
node_hostname="${node_hostname//$'\r'/}"
node_hostname="${node_hostname//$'\n'/}"
[[ "$node_hostname" == "puppet8node" ]] ||
  fail "Node hostname verification failed: expected 'puppet8node', got '$node_hostname'."

# The snapshot's apt lists are frozen at snapshot time and the apt timers are off (ruling 5), so
# superseded package versions 404 on the mirrors. Refresh synchronously, before any harness run.
printf 'Refreshing apt package lists on the node...\n'
# shellcheck disable=SC2029  # the timeout is a local constant
ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" "sudo -n timeout ${APT_UPDATE_TIMEOUT_SECONDS} apt-get -q update" >/dev/null ||
  fail "apt-get update failed on node '$NODE_SSH_ALIAS' (mirror unreachable?)."
t_apt="$(now_ms)"

require_master_running

# Client-side expansion is intended: host and port are local constants.
# shellcheck disable=SC2029
if ! ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" \
  "timeout 5 bash -c 'exec 3<>/dev/tcp/${MASTER_SERVICE_HOST}/${MASTER_SERVICE_PORT}'"; then
  fail "Node '$NODE_SSH_ALIAS' cannot open a TCP connection to ${MASTER_SERVICE_HOST}:${MASTER_SERVICE_PORT} (master SSH alias: '$MASTER_SSH_ALIAS')."
fi

t_end="$(now_ms)"

printf 'SUCCESS: node %q restored to %q; SSH, hostname, and %s:%s connectivity verified.\n' \
  "$NODE_VM" "$NODE_SNAPSHOT" "$MASTER_SERVICE_HOST" "$MASTER_SERVICE_PORT"
printf 'REVERT_METRICS {"snapshot":"%s","total_s":%s,"master_check_s":%s,"poweroff_s":%s,"restore_s":%s,"boot_to_ssh_s":%s,"apt_update_s":%s,"verify_s":%s}\n' \
  "$NODE_SNAPSHOT" \
  "$(ms_to_s $((t_end - t_start)))" "$(ms_to_s $((t_master - t_start)))" "$(ms_to_s $((t_off - t_master)))" \
  "$(ms_to_s $((t_restore - t_off)))" "$(ms_to_s $((t_ssh - t_restore)))" \
  "$(ms_to_s $((t_apt - t_ssh)))" "$(ms_to_s $((t_end - t_apt)))"
