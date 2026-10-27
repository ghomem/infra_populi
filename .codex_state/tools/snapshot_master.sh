#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TRACKED TOOLING (HQ VM-operations ruling, 2026-10-27). TAKE-ONLY offline snapshot of the lab master.
#
#   snapshot_master.sh <NAME> [--dry-run]
#
# Refuses (nothing touched) when: NAME is malformed or already exists; a harness / Codex / reviewer / composite
# run is in progress; the master is not running; the repo's Puppetfile export differs from the master's.
# Then: builds the description from git HEAD, the pinned baseline, the Puppetfile sha256 and the
# `puppet module list` sha256; shuts the master down via ACPI (timeout; NEVER a hard poweroff — on timeout it
# refuses and leaves the master running); takes the snapshot offline; starts the master headless; verifies
# SSH, puppetserver active and 8140 `status/v1/simple` = running; appends name + UUID to
# .codex_state/lab/master_snapshots.jsonl (commit it separately).
# It never restores, deletes or edits a snapshot and never touches the node.
# ---------------------------------------------------------------------------
set -euo pipefail

TOOLS="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO="$(git -C "$TOOLS" rev-parse --show-toplevel)"
MASTER_VM="Ubuntu24-puppet8-Master"
MASTER_HOST="puppet8master"
ACPI_TIMEOUT_SECONDS="${ACPI_TIMEOUT_SECONDS:-240}"
BOOT_TIMEOUT_SECONDS="${BOOT_TIMEOUT_SECONDS:-300}"
RECORD="${P8_SNAPSHOT_RECORD:-$REPO/.codex_state/lab/master_snapshots.jsonl}"
# Engine runs that must not see the master go away (process command lines).
BUSY_RE='test_class\.sh|codex_migrate_class|codex exec|review_class\.py check|composite_compile\.py|record_green\.sh|revert_node\.sh'

refuse() { echo "SNAPSHOT REFUSED: $*" >&2; exit 1; }
vm_state() { VBoxManage showvminfo "$MASTER_VM" --machinereadable | sed -n 's/^VMState="\(.*\)"$/\1/p'; }

[[ $# -ge 1 ]] || { sed -n '4,16p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
NAME="$1"; DRY=0
[[ "${2:-}" == "--dry-run" ]] && DRY=1
[[ "$NAME" =~ ^P8MASTER_[A-Za-z0-9_]+$ ]] || refuse "name '${NAME}' must match P8MASTER_[A-Za-z0-9_]+"

# 1. nothing of the engine is running
busy="$(pgrep -af "$BUSY_RE" | grep -v "snapshot_master" || true)"
[[ -z "$busy" ]] || refuse "an engine run is in progress: ${busy%%$'\n'*}"

# 2. master running; name unused
[[ "$(vm_state)" == running ]] || refuse "master VM is '$(vm_state)', expected running (this tool only snapshots a running, healthy master)"
if VBoxManage snapshot "$MASTER_VM" list --machinereadable 2>/dev/null | grep -qx "SnapshotName[-0-9]*=\"${NAME}\""; then
  refuse "a master snapshot named ${NAME} already exists"
fi

# 3. description inputs (before the master goes down)
PUPPETFILE_CMD="${P8_PUPPETFILE_CMD:-python3 $TOOLS/export_puppetfile.py --verify}"
$PUPPETFILE_CMD >/dev/null || refuse "the master Puppetfile differs from .codex_state/lab/Puppetfile (export it first)"
head="$(git -C "$REPO" rev-parse --short HEAD)"
[[ -z "$(git -C "$REPO" status --porcelain)" ]] || refuse "worktree not clean (the snapshot must describe a committed state)"
base="$(python3 "$TOOLS/baseline.py" label)"
pf_sha="$(sha256sum "$REPO/.codex_state/lab/Puppetfile" | cut -c1-12)"
mods="$(timeout 120 ssh -T "$MASTER_HOST" 'sudo -n /opt/puppetlabs/bin/puppet module list --environment production 2>&1' | sed 's/\x1b\[[0-9;]*m//g' | sort)" ||
  refuse "could not read the master's module list"
mods_sha="$(printf '%s\n' "$mods" | sha256sum | cut -c1-12)"
nmods="$(grep -c '── ' <<<"$mods" || true)"
desc="infra_populi lab master; repo ${head}; baseline ${base}; Puppetfile sha256 ${pf_sha}; module list sha256 ${mods_sha} (${nmods} modules); taken offline by snapshot_master.sh $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "DESCRIPTION: ${desc}"
[[ $DRY -eq 0 ]] || { echo "DRY RUN: no shutdown, no snapshot"; exit 0; }

# 4. offline via ACPI only
VBoxManage controlvm "$MASTER_VM" acpipowerbutton
waited=0
while [[ "$(vm_state)" != poweroff ]]; do
  if (( waited >= ACPI_TIMEOUT_SECONDS )); then
    refuse "master did not power off within ${ACPI_TIMEOUT_SECONDS}s after ACPI; NOT forcing it — left as '$(vm_state)', no snapshot taken"
  fi
  sleep 5; waited=$((waited + 5))
done
echo "==> master powered off via ACPI after ${waited}s"

# 5. take, then bring the master back no matter what
take_rc=0
VBoxManage snapshot "$MASTER_VM" take "$NAME" --description "$desc" || take_rc=$?
VBoxManage startvm "$MASTER_VM" --type headless >/dev/null
[[ $take_rc -eq 0 ]] || refuse "VBoxManage snapshot take failed (rc ${take_rc}); master restarted"

# 6. verify the master is back
waited=0
until timeout 10 ssh -o ConnectTimeout=5 -T "$MASTER_HOST" true 2>/dev/null; do
  (( waited < BOOT_TIMEOUT_SECONDS )) || refuse "snapshot ${NAME} taken, but the master is not reachable over SSH after ${BOOT_TIMEOUT_SECONDS}s"
  sleep 5; waited=$((waited + 5))
done
status=""
for _ in $(seq 1 60); do
  status="$(timeout 15 ssh -T "$MASTER_HOST" 'systemctl is-active puppetserver; curl -sk https://localhost:8140/status/v1/simple' 2>/dev/null | tr '\n' ' ')" || true
  [[ "$status" == "active running " ]] && break
  sleep 5
done
[[ "$status" == "active running " ]] || refuse "snapshot ${NAME} taken, but puppetserver/8140 not healthy: '${status}'"

# 7. record name + UUID
uuid="$(VBoxManage snapshot "$MASTER_VM" showvminfo "$NAME" --machinereadable 2>/dev/null | sed -n 's/^CurrentSnapshotUUID="\(.*\)"$/\1/p;s/^SnapshotUUID="\(.*\)"$/\1/p' | head -1)"
[[ -n "$uuid" ]] || uuid="$(VBoxManage snapshot "$MASTER_VM" list --machinereadable | grep -A1 -x "SnapshotName[-0-9]*=\"${NAME}\"" | sed -n 's/^SnapshotUUID[-0-9]*="\(.*\)"$/\1/p')"
mkdir -p "$(dirname "$RECORD")"
python3 -c 'import json,sys; print(json.dumps(dict(zip(["name","uuid","description","taken_at"], sys.argv[1:]))))' \
  "$NAME" "$uuid" "$desc" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >>"$RECORD"
echo "SNAPSHOT ${NAME} ${uuid}; master back: puppetserver active, 8140 running; recorded in ${RECORD#"$REPO"/}"
