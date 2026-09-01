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
#   node snapshot P8NODE_BASELINE_GREEN
#   SSH aliases   puppet8node, puppet8master
#   Wi-Fi bridge  host interface wlo1 (typically takes about 45s to settle)
#   master check  puppet8master.example.com:8140, opened from the node
# Parameterizing these via environment variables is a known future improvement.
# ---------------------------------------------------------------------------

set -euo pipefail

readonly NODE_VM="ubuntu24-puppet8-Node"
readonly MASTER_VM="Ubuntu24-puppet8-Master"
readonly NODE_SNAPSHOT="P8NODE_BASELINE_GREEN"
readonly NODE_SSH_ALIAS="puppet8node"
readonly MASTER_SSH_ALIAS="puppet8master"
readonly MASTER_SERVICE_HOST="puppet8master.example.com"
readonly MASTER_SERVICE_PORT="8140"
readonly POWEROFF_TIMEOUT_SECONDS=90
readonly SSH_TIMEOUT_SECONDS=120
readonly POLL_INTERVAL_SECONDS=2

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

require_master_running

if ! node_state="$(vm_state "$NODE_VM")"; then
  fail "Unable to determine the state of node VM '$NODE_VM'."
fi

if [[ "$node_state" != "poweroff" ]]; then
  if [[ "$node_state" != "running" ]]; then
    fail "Node VM '$NODE_VM' is in state '$node_state'; refusing to force it off."
  fi

  printf 'Requesting graceful ACPI poweroff of node VM %q...\n' "$NODE_VM"
  VBoxManage controlvm "$NODE_VM" acpipowerbutton ||
    fail "Could not request ACPI poweroff for node VM '$NODE_VM'."

  poweroff_deadline=$((SECONDS + POWEROFF_TIMEOUT_SECONDS))
  while true; do
    if ! node_state="$(vm_state "$NODE_VM")"; then
      fail "Lost the state of node VM '$NODE_VM' while waiting for graceful poweroff."
    fi

    [[ "$node_state" == "poweroff" ]] && break

    if ((SECONDS >= poweroff_deadline)); then
      fail "Node VM '$NODE_VM' did not power off gracefully within ${POWEROFF_TIMEOUT_SECONDS}s; no hard poweroff was attempted."
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done
else
  printf 'Node VM %q is already powered off.\n' "$NODE_VM"
fi

printf 'Restoring node snapshot %q...\n' "$NODE_SNAPSHOT"
VBoxManage snapshot "$NODE_VM" restore "$NODE_SNAPSHOT" ||
  fail "Could not restore snapshot '$NODE_SNAPSHOT' on node VM '$NODE_VM'."

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

if ! node_hostname="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" hostname)"; then
  fail "Node '$NODE_SSH_ALIAS' stopped responding during hostname verification."
fi
node_hostname="${node_hostname//$'\r'/}"
node_hostname="${node_hostname//$'\n'/}"
[[ "$node_hostname" == "puppet8node" ]] ||
  fail "Node hostname verification failed: expected 'puppet8node', got '$node_hostname'."

require_master_running

if ! ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" \
  "timeout 5 bash -c 'exec 3<>/dev/tcp/${MASTER_SERVICE_HOST}/${MASTER_SERVICE_PORT}'"; then
  fail "Node '$NODE_SSH_ALIAS' cannot open a TCP connection to ${MASTER_SERVICE_HOST}:${MASTER_SERVICE_PORT} (master SSH alias: '$MASTER_SSH_ALIAS')."
fi

printf 'SUCCESS: node %q restored to %q; SSH, hostname, and %s:%s connectivity verified.\n' \
  "$NODE_VM" "$NODE_SNAPSHOT" "$MASTER_SERVICE_HOST" "$MASTER_SERVICE_PORT"
