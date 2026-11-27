#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Lab power (HQ 2026-11-20 item 3; the lab travels with the laptop). Guarded commands, nothing else needed:
#
#   lab_power.sh down   stop any run cleanly (TERM to the lab lock's holder, wait for it to release the lock), take the
#                       lock, power off every running lab VM but the master (nodes are reverted before use), shut the
#                       master down through ACPI with a timeout (NEVER a hard power-off: on timeout it refuses and
#                       leaves the master running), release the sleep guard, release the lock
#   lab_power.sh up     refuse on battery (mains only), take the lock, start the master, wait until it is healthy (SSH, puppetserver active, 8140
#                       /status/v1/simple running, its clock within the limit), revert the node (which starts the sleep
#                       guard), release the lock
#
# Exit 0 done, 1 refused (the reason on stderr), 2 usage. Lab VMs: the master and every `vm` of the node inventory.
# ACPI_TIMEOUT_SECONDS, BOOT_TIMEOUT_SECONDS and RUN_STOP_TIMEOUT_SECONDS override the waits (tests); P8_LAB_LOCK as in
# lab_lock.sh.
# ---------------------------------------------------------------------------
set -euo pipefail

TOOLS="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
MASTER_VM="Ubuntu24-puppet8-Master"
MASTER_HOST="puppet8master"
ACPI_TIMEOUT_SECONDS="${ACPI_TIMEOUT_SECONDS:-240}"
BOOT_TIMEOUT_SECONDS="${BOOT_TIMEOUT_SECONDS:-300}"
RUN_STOP_TIMEOUT_SECONDS="${RUN_STOP_TIMEOUT_SECONDS:-120}"
POLL=5
[[ -n "${P8_LAB_POWER_POLL:-}" ]] && POLL="$P8_LAB_POWER_POLL"

MODE="${1:-}"
refuse() { echo "LAB ${MODE^^} REFUSED: $*" >&2; exit 1; }
vm_state() { VBoxManage showvminfo "$1" --machinereadable 2>/dev/null | sed -n 's/^VMState="\(.*\)"$/\1/p'; }
lab_vms() { printf '%s\n' "$MASTER_VM"; python3 "${TOOLS}/nodes.py" list 2>/dev/null | awk '{print $3}'; }
pause() { command -p sleep "$POLL"; }

take_lock() {
  local out
  out="$("${TOOLS}/lab_lock.sh" take "$$" "lab_power.sh ${MODE}" 2>&1)" || refuse "could not take the lab lock: ${out}"
  trap '"${TOOLS}/lab_lock.sh" release "$$" >/dev/null 2>&1 || true' EXIT
  export P8_LAB_LOCKED=1
}

case "$MODE" in
  down)
    # 1. stop any run cleanly: the lock's live holder gets TERM (the engine's runs release the lock on exit)
    holder="$("${TOOLS}/lab_lock.sh" holder 2>/dev/null || true)"
    if [[ -n "$holder" ]]; then
      pid="${holder%% *}"
      echo "Stopping the run that holds the lab lock: ${holder}"
      kill -TERM "$pid" 2>/dev/null || true
      deadline=$((SECONDS + RUN_STOP_TIMEOUT_SECONDS))
      while kill -0 "$pid" 2>/dev/null; do
        ((SECONDS < deadline)) || refuse "the run ${pid} did not stop within ${RUN_STOP_TIMEOUT_SECONDS}s; nothing powered off"
        pause
      done
    fi
    # 2. hold the lab so nothing starts meanwhile (a master's clock is irrelevant for shutting down)
    P8_CLOCK_HOSTS="" take_lock
    # 3. every running lab VM but the master: powered off (each is reverted before use)
    stopped=0
    while read -r vm; do
      [[ -n "$vm" && "$vm" != "$MASTER_VM" ]] || continue
      if [[ "$(vm_state "$vm")" == running ]]; then
        VBoxManage controlvm "$vm" poweroff >/dev/null || refuse "could not power off ${vm}"
        stopped=$((stopped + 1))
      fi
    done < <(lab_vms)
    # 4. the master: ACPI with a timeout, never a hard power-off
    master="$(vm_state "$MASTER_VM")"
    if [[ "$master" == running ]]; then
      VBoxManage controlvm "$MASTER_VM" acpipowerbutton || refuse "ACPI power button failed on the master"
      deadline=$((SECONDS + ACPI_TIMEOUT_SECONDS))
      while [[ "$(vm_state "$MASTER_VM")" != poweroff ]]; do
        ((SECONDS < deadline)) ||
          refuse "the master did not power off within ${ACPI_TIMEOUT_SECONDS}s after ACPI; NOT forcing it (left '$(vm_state "$MASTER_VM")'); ${stopped} other VM(s) powered off"
        pause
      done
      master="poweroff (ACPI)"
    fi
    # 5. no lab VM runs any more: the sleep guard goes
    "${TOOLS}/lab_sleep_guard.sh" release
    echo "LAB DOWN: master ${master}; ${stopped} other VM(s) powered off; sleep guard released"
    ;;
  up)
    # HQ review of the behaviour suite (2026-11-27) ruling 4: the lab runs on mains only
    if why="$("${TOOLS}/lab_sleep_guard.sh" on-battery)"; then
      refuse "the laptop is on battery (${why}); the lab runs on mains only"
    fi
    take_lock
    # HQ 2026-11-24: the master runs on the lab's paravirt provider too (nodes.yml); under the default one its clock
    # drifted beyond what timesyncd corrects. Its setting is Salatiel's (raw VBoxManage), so a mismatch only refuses.
    provider="$(python3 "${TOOLS}/nodes.py" provider)" || refuse "the inventory names no paravirt provider"
    master_provider="$(VBoxManage showvminfo "$MASTER_VM" --machinereadable 2>/dev/null | sed -n 's/^effparavirtprovider="\(.*\)"$/\1/p')"
    [[ "$master_provider" == "$provider" ]] ||
      refuse "the master runs on paravirt provider '${master_provider:-unknown}', not the lab's '${provider}' (nodes.yml); Salatiel sets it while it is powered off (escalations/lab-clock.md)"
    if [[ "$(vm_state "$MASTER_VM")" != running ]]; then
      echo "Starting the master headless..."
      VBoxManage startvm "$MASTER_VM" --type headless >/dev/null || refuse "could not start the master"
    fi
    deadline=$((SECONDS + BOOT_TIMEOUT_SECONDS))
    until timeout 10 ssh -o ConnectTimeout=5 -T "$MASTER_HOST" true </dev/null 2>/dev/null; do
      ((SECONDS < deadline)) || refuse "the master is not reachable over SSH after ${BOOT_TIMEOUT_SECONDS}s"
      pause
    done
    status=""
    deadline=$((SECONDS + BOOT_TIMEOUT_SECONDS))
    while true; do
      # whitespace-normalised, as snapshot_master.sh: the status endpoint prints no trailing newline
      status="$(timeout 15 ssh -T "$MASTER_HOST" 'systemctl is-active puppetserver; curl -sk https://localhost:8140/status/v1/simple' </dev/null 2>/dev/null | tr -s '\r\n' '  ' | sed 's/^ *//; s/ *$//')" || true
      [[ "$status" == "active running" ]] && break
      ((SECONDS < deadline)) || refuse "the master is up but not healthy after ${BOOT_TIMEOUT_SECONDS}s: '${status}'"
      pause
    done
    "${TOOLS}/clock_check.py" "$MASTER_HOST" >&2 || refuse "the master's clock is off the laptop's (CLOCK above)"
    "${TOOLS}/revert_node.sh" || refuse "the node revert failed (above); the master is up"
    echo "LAB UP: master healthy (puppetserver active, 8140 running, clock checked); node reverted"
    ;;
  *)
    sed -n '4,12p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 2
    ;;
esac
