#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TRACKED TOOLING. This script is version-controlled because it encodes the
# clean-baseline recovery contract for the Puppet 8 test node:
# revert_node.sh restores, starts, and verifies that node. It may also start
# and verify the master, but never performs a destructive master VM action.
# Tracking this safety-critical lifecycle tool keeps that boundary and its
# host assumptions reviewable. See DESIGN_DECISIONS.md.
#
# The NODE comes from the lab node inventory (.codex_state/lab/nodes.yml via nodes.py, HQ 2026-11-16 item 2):
#   revert_node.sh [--node KIND] [--node-state]    (else P8_NODE, else the inventory default `ubuntu`)
# Its VM must be ubuntu24-puppet8-Node or a p8lab-* VM, never the master. Default node: ubuntu24-puppet8-Node,
# snapshot P8NODE_BASELINE_GREEN_v5 (v4 + paravirt provider hyperv, 2026-11-24; v4 = v3 — GRUB_RECORDFAIL_TIMEOUT=2, apt timers off, NIC2 host-only vboxnet0,
# enp0s8 192.168.56.20/24, hosts master -> 192.168.56.10 — plus NIC1 VirtualBox NAT with natdnshostresolver1 on).
# After every restore: Debian refreshes apt lists; RedHat must show a valid subscription (HQ 2026-11-16 item 5), has
# its content overrides cleared (they live on the subscription server and survive a restore) and refreshes the dnf
# metadata.
#
# Host-specific assumptions:
#   master VM     Ubuntu24-puppet8-Master  (may start; never restore/power off/reset)
#   SSH aliases   the node's alias (nodes.yml), puppet8master (host-only 192.168.56.10)
#   NIC1          VirtualBox NAT (internet and DNS through the laptop's current uplink; the engine reaches the node
#                 over host-only). lab-network-nat.md: the default route must be via 10.0.2.2 on the interface holding
#                 10.0.2.15/24, and no address may be on the home LAN 192.168.77.0/24.
#   master check  puppet8master.example.com:8140, opened from the node
# Parameterizing these via environment variables is a known future improvement.
#
# Node power-off is a HARD poweroff (ruling 5, 2026-10-26): the node is restored
# from an offline snapshot immediately afterwards, so a graceful shutdown buys
# nothing. The master is never powered off, reset or restored by this script.
# Last line on success: REVERT_METRICS {json} with phase timings (step 3.4) and apt_mirror (primary, or the fallback).
# Mirror fallback (HQ batch-14 ruling 7): only when the primary Ubuntu archive fails, for that run only, recorded in
# the run record, never written into a baseline. The node's sources file on disk is not edited: a copy naming the
# fallback mirror lives in /run (tmpfs) and is bind-mounted over it, so a shutdown or the next restore drops it.
# Host-only path (lab-network plan, HQ step review A): after every restore the revert fails unless a fresh (-S none)
# SSH to the node comes from 192.168.56.1 to its hostonly_ip, the node holds that address and it resolves
# puppet8master.example.com to 192.168.56.10.
# Every successful revert marks the node's state token (kernel boot ID + hash of the agent's
# last_run_summary) through records.py revert-mark; record_green.sh accepts a GREEN only if its harness
# run started on that token (HQ batch-3 acceptance, item 1). `revert_node.sh --node-state` prints the token and
# touches no VM.
# `revert_node.sh [--node KIND] --power-off` powers the node off and stops there: no restore, no start (2026-11-17, for
# a new VM cloned from the node, whose first boot takes the node's static host-only address). The next revert brings
# the node back.
# ---------------------------------------------------------------------------

set -euo pipefail

readonly MASTER_VM="Ubuntu24-puppet8-Master"
readonly MASTER_SSH_ALIAS="puppet8master"
readonly MASTER_SERVICE_HOST="puppet8master.example.com"
readonly MASTER_SERVICE_PORT="8140"
readonly POWEROFF_TIMEOUT_SECONDS=30
readonly SSH_TIMEOUT_SECONDS=120
readonly POLL_INTERVAL_SECONDS=2
readonly APT_UPDATE_TIMEOUT_SECONDS=180
readonly ROUTE_TIMEOUT_SECONDS="${ROUTE_TIMEOUT_SECONDS:-60}"
readonly LAPTOP_HOSTONLY_IP="192.168.56.1"
readonly MASTER_HOSTONLY_IP="192.168.56.10"
readonly NAT_GATEWAY="10.0.2.2"
readonly NAT_ADDRESS="10.0.2.15/24"
readonly HOME_LAN_PREFIX="192.168.77."
# 600 s (was 300 s; 2026-11-24): a restore discards dnf's cache, and on a slow uplink BaseOS's metadata alone (173 MB)
# took 4 min 02 s by hand at 849 kB/s, and over 300 s in three reverts the same day.
readonly DNF_TIMEOUT_SECONDS=600
readonly FALLBACK_MIRROR="${P8_FALLBACK_MIRROR:-http://mirrors.edge.kernel.org/ubuntu/}"
# HQ 2026-11-10 ruling 2: ssh through the ControlMaster shim (see sshmux/ssh).
TOOLS_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PATH="${TOOLS_DIR}/sshmux:${PATH}"

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

# Two lines: the node's kernel boot ID, then the sha256 of last_run_summary.yaml (`absent` if none).
# A reboot changes the first, any agent run the second.
node_state_token() {
  ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" \
    'cat /proc/sys/kernel/random/boot_id; { sudo -n sha256sum /opt/puppetlabs/puppet/public/last_run_summary.yaml 2>/dev/null || echo absent; } | cut -d" " -f1'
}

node_kind="" state_only=0 power_off_only=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --node) node_kind="${2:-}"; [[ -n "$node_kind" ]] || fail "--node needs a kind"; shift 2 ;;
    --node-state) state_only=1; shift ;;
    --power-off) power_off_only=1; shift ;;
    *) fail "Usage: $0 [--node KIND] [--node-state | --power-off]" ;;
  esac
done
node_env="$(python3 "${TOOLS_DIR}/nodes.py" env ${node_kind:+--node "$node_kind"})" ||
  fail "No usable node in the lab inventory (kind: ${node_kind:-default}); no VM action was attempted."
eval "$node_env"
NODE_SSH_ALIAS="$NODE_ALIAS"
[[ "$NODE_VM" != "$MASTER_VM" ]] || fail "The inventory names the master VM as a node; refusing."
[[ "$NODE_VM" == "ubuntu24-puppet8-Node" || "$NODE_VM" =~ ^p8lab-[a-z0-9-]+$ ]] ||
  fail "Node VM '$NODE_VM' is neither ubuntu24-puppet8-Node nor a p8lab-* VM; refusing."
readonly NODE_KIND NODE_VM NODE_SNAPSHOT NODE_SSH_ALIAS NODE_HOSTONLY_IP NODE_HOSTNAME NODE_OS_FAMILY NODE_PARAVIRT

if [[ $state_only -eq 1 ]]; then
  node_state_token
  exit
fi

# One lab run at a time (lab_lock.sh); a harness or phase3 run that calls this revert already holds the lock.
if [[ -z "${P8_LAB_LOCKED:-}" ]]; then
  if ! lock_holder="$("${TOOLS_DIR}/lab_lock.sh" take "$$" "revert_node.sh" 2>&1)"; then
    fail "another lab run holds the lab lock (${lock_holder}); not reverting the node under it."
  fi
  trap '"${TOOLS_DIR}/lab_lock.sh" release "$$" || true' EXIT
fi

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

  local started=0
  if [[ "$state" != "running" ]]; then
    printf 'Starting master VM %q headless (current state: %s)...\n' "$MASTER_VM" "$state"
    VBoxManage startvm "$MASTER_VM" --type headless ||
      fail "Could not start master VM '$MASTER_VM' from state '$state'; no destructive master VM action was attempted."
    started=1
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
        # A master this revert started had no clock to check when the lab lock was taken (lab_lock.sh): check it now.
        if ((started)); then
          "${TOOLS_DIR}/clock_check.py" "$MASTER_SSH_ALIAS" >&2 ||
            fail "The master's clock is off the laptop's after its start (CLOCK above); not handing the lab to a run."
        fi
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

# Sleep is blocked for as long as a lab VM runs (lab_sleep_guard.sh, 2026-11-19); a laptop without logind's inhibitor
# only warns.
guard_sleep() {
  "${TOOLS_DIR}/lab_sleep_guard.sh" ensure || echo "WARNING: the lab sleep guard did not start" >&2
}

t_start="$(now_ms)"
require_master_running
guard_sleep
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
    # close the multiplexed SSH master first, so no stale control socket outlives the node
    timeout 10 ssh -O exit "$NODE_SSH_ALIAS" >/dev/null 2>&1 || true
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
if [[ $power_off_only -eq 1 ]]; then
  echo "POWERED_OFF node ${NODE_KIND} (${NODE_VM}); not restored or started (the next revert brings it back)"
  exit 0
fi

printf 'Restoring node snapshot %q...\n' "$NODE_SNAPSHOT"
VBoxManage snapshot "$NODE_VM" restore "$NODE_SNAPSHOT" ||
  fail "Could not restore snapshot '$NODE_SNAPSHOT' on node VM '$NODE_VM'."

current_snapshot="$(
  VBoxManage showvminfo "$NODE_VM" --machinereadable 2>/dev/null |
    awk -F= '$1 == "CurrentSnapshotName" { gsub(/"/, "", $2); print $2; exit }'
)"
[[ "$current_snapshot" == "$NODE_SNAPSHOT" ]] ||
  fail "After restore the current snapshot is '$current_snapshot', expected '$NODE_SNAPSHOT'."
# HQ 2026-11-24: every lab VM runs on the inventory's paravirtualization provider; under the default (kvm) one the
# guest clocks drifted beyond what ntpd corrects. A restored snapshot carries its own setting, so this is checked after
# the restore and before the boot.
provider="$(
  VBoxManage showvminfo "$NODE_VM" --machinereadable 2>/dev/null |
    awk -F= '$1 == "effparavirtprovider" { gsub(/"/, "", $2); print $2; exit }'
)"
[[ "$provider" == "$NODE_PARAVIRT" ]] ||
  fail "Node VM '$NODE_VM' at '$NODE_SNAPSHOT' runs on paravirt provider '${provider:-unknown}', not the lab's '$NODE_PARAVIRT' (nodes.yml); its clock would drift. Take a baseline with the provider set (escalations/lab-clock.md)."
t_restore="$(now_ms)"

printf 'Starting node VM %q headless...\n' "$NODE_VM"
VBoxManage startvm "$NODE_VM" --type headless ||
  fail "Could not start node VM '$NODE_VM'."
guard_sleep

wait_ssh() {
  local alias="$1" ssh_deadline=$((SECONDS + SSH_TIMEOUT_SECONDS))
  until ssh "${SSH_OPTIONS[@]}" "$alias" true >/dev/null 2>&1; do
    if ((SECONDS >= ssh_deadline)); then
      fail "Node '$alias' did not become reachable by SSH within ${SSH_TIMEOUT_SECONDS}s."
    fi

    sleep "$POLL_INTERVAL_SECONDS"
  done
}

printf 'Waiting up to %ss for SSH over the host-only network...\n' "$SSH_TIMEOUT_SECONDS"
wait_ssh "$NODE_SSH_ALIAS"
# The path, not only success: a fresh connection (-S none) must come from the laptop's host-only address.
# shellcheck disable=SC2016  # $SSH_CONNECTION is the node's
connection="$(ssh "${SSH_OPTIONS[@]}" -S none "$NODE_SSH_ALIAS" 'echo $SSH_CONNECTION')" ||
  fail "Node '$NODE_SSH_ALIAS' stopped responding during the path check."
read -r conn_src _ conn_dst _ <<<"$connection"
[[ "$conn_src" == "$LAPTOP_HOSTONLY_IP" && "$conn_dst" == "$NODE_HOSTONLY_IP" ]] ||
  fail "Path check failed: SSH_CONNECTION '${connection}', expected ${LAPTOP_HOSTONLY_IP} -> ${NODE_HOSTONLY_IP}."
ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" 'ip -br addr' 2>/dev/null | grep -q " ${NODE_HOSTONLY_IP}/24" ||
  fail "The restored node does not hold ${NODE_HOSTONLY_IP}/24 on any interface (wrong snapshot?)."
# shellcheck disable=SC2029  # the host name is a local constant
resolved="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" "getent hosts ${MASTER_SERVICE_HOST}")" || resolved=""
[[ "${resolved%% *}" == "$MASTER_HOSTONLY_IP" ]] ||
  fail "The node resolves ${MASTER_SERVICE_HOST} to '${resolved%% *}', expected ${MASTER_HOSTONLY_IP}."
# HQ 2026-11-17 batch-8 ruling 4: the node's clock agrees with the laptop's (a suspend can leave a VM behind).
"${TOOLS_DIR}/clock_check.py" "$NODE_SSH_ALIAS" >/dev/null ||
  fail "The node's clock is off the laptop's (CLOCK_SKEW above); not handing it to a run."
t_ssh="$(now_ms)"

if ! node_hostname="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" hostname)"; then
  fail "Node '$NODE_SSH_ALIAS' stopped responding during hostname verification."
fi
node_hostname="${node_hostname//$'\r'/}"
node_hostname="${node_hostname//$'\n'/}"
[[ "$node_hostname" == "$NODE_HOSTNAME" ]] ||
  fail "Node hostname verification failed: expected '$NODE_HOSTNAME', got '$node_hostname'."

# One apt refresh. Sets apt_error (the failure, for messages), apt_failed_on (exit | fetch) and apt_fetch_errors.
apt_refresh() {
  local out
  # shellcheck disable=SC2029  # the timeout is a local constant
  if ! out="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" "sudo -n timeout ${APT_UPDATE_TIMEOUT_SECONDS} apt-get -q update" 2>&1)"; then
    apt_failed_on="exit" apt_fetch_errors=""
    apt_error="apt-get update failed on node '$NODE_SSH_ALIAS' (mirror unreachable?)."
    return 1
  fi
  if apt_fetch_errors="$(grep -E '^E: |Temporary failure resolving|Failed to fetch|Could not resolve|Unable to connect' <<<"$out")"; then
    apt_failed_on="fetch"
    apt_error="apt-get update reported fetch failures on node '$NODE_SSH_ALIAS' (no internet or DNS): ${apt_fetch_errors%%$'\n'*}"
    return 1
  fi
}

# Point this run's apt at the fallback mirror without touching the disk: the Ubuntu archive URIs of
# /etc/apt/sources.list.d/ubuntu.sources are rewritten into a copy in /run, bind-mounted over the file.
use_fallback_mirror() {
  local script
  # shellcheck disable=SC2016  # expanded on the node
  script='set -e
f=/etc/apt/sources.list.d/ubuntu.sources
[ -f "$f" ]
install -d -m 0755 /run/p8-fallback-mirror
sed -E "s#https?://([a-z]+\.)?(archive|security)\.ubuntu\.com/ubuntu/?#${P8_MIRROR}#g" "$f" > /run/p8-fallback-mirror/ubuntu.sources
grep -qF "$P8_MIRROR" /run/p8-fallback-mirror/ubuntu.sources
findmnt -n "$f" >/dev/null || mount --bind /run/p8-fallback-mirror/ubuntu.sources "$f"
findmnt -n "$f" >/dev/null'
  # shellcheck disable=SC2029  # the script and the mirror are local constants, quoted for the node's shell
  ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" \
    "sudo -n env P8_MIRROR=$(printf '%q' "$FALLBACK_MIRROR") bash -c $(printf '%q' "$script")" >/dev/null 2>&1
}

# The snapshot's apt lists are frozen at snapshot time and the apt timers are off (ruling 5), so
# superseded package versions 404 on the mirrors. Refresh synchronously, before any harness run.
# Internet must be real, not assumed (2026-11-16): a missing DHCPv4 lease on NIC1 left the node IPv6-only with no
# default route, and apt-get update still exited 0 on its fetch failures, so the revert reported SUCCESS.
route_deadline=$((SECONDS + ROUTE_TIMEOUT_SECONDS))
until default_route="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" 'ip -4 route show default' 2>/dev/null | grep -m1 '^default ')"; do
  ((SECONDS < route_deadline)) ||
    fail "The node has no IPv4 default route after ${ROUTE_TIMEOUT_SECONDS}s (no DHCPv4 lease on NIC1?): no internet for apt."
  sleep "$POLL_INTERVAL_SECONDS"
done
# NIC1 is VirtualBox NAT (lab-network-nat.md step 5): internet never through the home LAN.
read -r _ _ route_via _ route_dev _ <<<"$default_route"
[[ "$route_via" == "$NAT_GATEWAY" && -n "$route_dev" ]] ||
  fail "The node's default route is '${default_route}', expected via ${NAT_GATEWAY} (NIC1 NAT; wrong snapshot or NIC1 not NAT?)."
node_addrs="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" 'ip -4 -br addr' 2>/dev/null)" ||
  fail "Node '$NODE_SSH_ALIAS' stopped responding during the NAT check."
awk -v dev="$route_dev" -v want="$NAT_ADDRESS" '$1 == dev { for (i = 3; i <= NF; i++) if ($i == want) ok = 1 } END { exit !ok }' <<<"$node_addrs" ||
  fail "The node's default-route interface ${route_dev} does not hold ${NAT_ADDRESS} (NIC1 not NAT?)."
if grep -qF " ${HOME_LAN_PREFIX}" <<<"$node_addrs"; then
  fail "The node holds an address on the home LAN (${HOME_LAN_PREFIX}x): NIC1 must be NAT."
fi
apt_mirror=""  # RedHat nodes have no apt mirror: null in REVERT_METRICS
if [[ "$NODE_OS_FAMILY" == "RedHat" ]]; then
  # A RHEL node must be registered after every restore (HQ 2026-11-16 item 5): no valid subscription, no packages.
  ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" 'sudo -n subscription-manager identity' >/dev/null 2>&1 ||
    fail "The restored RHEL node '$NODE_SSH_ALIAS' is not registered (subscription-manager identity failed)."
  # Content overrides (an enabled repository) live on the subscription server, not in the snapshot: one made after
  # the baseline was enabled again right after a restore (p8lab-rhel9 bring-up, 2026-11-16). Clear them after every
  # restore (HQ 2026-11-16 item 5) and assert none remain.
  ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" 'sudo -n subscription-manager repo-override --remove-all' >/dev/null 2>&1 ||
    fail "Could not clear the content overrides (enabled repositories) of RHEL node '$NODE_SSH_ALIAS'."
  overrides="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" 'sudo -n subscription-manager repo-override --list' 2>&1)" || overrides=""
  grep -q 'does not have any content overrides' <<<"$overrides" ||
    fail "RHEL node '$NODE_SSH_ALIAS' still has content overrides after clearing: ${overrides%%$'\n'*}"
  printf 'Refreshing dnf metadata on the node...\n'
  # shellcheck disable=SC2029  # the timeout is a local constant
  ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" "sudo -n timeout ${DNF_TIMEOUT_SECONDS} dnf -q makecache" >/dev/null 2>&1 ||
    fail "dnf makecache failed on node '$NODE_SSH_ALIAS' (no internet, DNS or repositories)."
else
  printf 'Refreshing apt package lists on the node...\n'
  apt_mirror="primary"
  if ! apt_refresh; then
    primary_error="$apt_error"
    # Fall back only when the primary Ubuntu archive is what failed: an exit status (a timeout says nothing about
    # which source hung) or a fetch failure naming an archive.ubuntu.com or security.ubuntu.com host. A failure that
    # names only other sources (the OpenVox repository) is not the archive's, and the mirror would not fix it.
    if [[ "$apt_failed_on" == "fetch" ]] && ! grep -qE '([a-z]+\.)?(archive|security)\.ubuntu\.com' <<<"$apt_fetch_errors"; then
      fail "$primary_error"
    fi
    printf 'The primary archive failed (%s); this run only, retrying on the fallback mirror %s (HQ batch-14 ruling 7)...\n' \
      "${primary_error%%$'\n'*}" "$FALLBACK_MIRROR"
    use_fallback_mirror ||
      fail "The primary archive failed (${primary_error}), and node '$NODE_SSH_ALIAS' could not be switched to the fallback mirror ${FALLBACK_MIRROR} for this run."
    apt_refresh ||
      fail "The primary archive failed (${primary_error}), and so did the fallback mirror ${FALLBACK_MIRROR} (${apt_error})."
    apt_mirror="fallback ${FALLBACK_MIRROR}"
  fi
fi
t_apt="$(now_ms)"

require_master_running

# Client-side expansion is intended: host and port are local constants.
# shellcheck disable=SC2029
if ! ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" \
  "timeout 5 bash -c 'exec 3<>/dev/tcp/${MASTER_SERVICE_HOST}/${MASTER_SERVICE_PORT}'"; then
  fail "Node '$NODE_SSH_ALIAS' cannot open a TCP connection to ${MASTER_SERVICE_HOST}:${MASTER_SERVICE_PORT} (master SSH alias: '$MASTER_SSH_ALIAS')."
fi

t_end="$(now_ms)"

# Bytes received on NIC1 since this restore's boot: the boot and the package refresh (HQ NAT review F: the data for a
# package-cache decision). Metrics only: an unreadable counter is null, never a failure.
# shellcheck disable=SC2029  # route_dev was read from the node above
nic1_rx="$(ssh "${SSH_OPTIONS[@]}" "$NODE_SSH_ALIAS" "cat /sys/class/net/${route_dev}/statistics/rx_bytes" 2>/dev/null)" || nic1_rx=""
[[ "$nic1_rx" =~ ^[0-9]+$ ]] || nic1_rx="null"

node_state_token | python3 "${TOOLS_DIR}/records.py" revert-mark "$NODE_SNAPSHOT" --node "$NODE_KIND" ||
  fail "Could not read or record the node's state token after the revert."

printf 'SUCCESS: node %q restored to %q; host-only path, SSH, hostname, and %s:%s connectivity verified.\n' \
  "$NODE_VM" "$NODE_SNAPSHOT" "$MASTER_SERVICE_HOST" "$MASTER_SERVICE_PORT"
printf 'REVERT_METRICS {"node":"%s","snapshot":"%s","total_s":%s,"master_check_s":%s,"poweroff_s":%s,"restore_s":%s,"boot_to_ssh_s":%s,"apt_update_s":%s,"verify_s":%s,"nic1_rx_bytes":%s,"apt_mirror":%s}\n' \
  "$NODE_KIND" "$NODE_SNAPSHOT" \
  "$(ms_to_s $((t_end - t_start)))" "$(ms_to_s $((t_master - t_start)))" "$(ms_to_s $((t_off - t_master)))" \
  "$(ms_to_s $((t_restore - t_off)))" "$(ms_to_s $((t_ssh - t_restore)))" \
  "$(ms_to_s $((t_apt - t_ssh)))" "$(ms_to_s $((t_end - t_apt)))" "$nic1_rx" \
  "$([[ -n "$apt_mirror" ]] && printf '"%s"' "$apt_mirror" || printf 'null')"
