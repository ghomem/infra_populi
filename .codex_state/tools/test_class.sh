#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TRACKED TOOLING. This script is version-controlled because it consumes
# tracked structured data: test_class.sh calls
# 'gen_migration_order.py --classify', which parses migration_plan.md.
# Tracking the generator and the plan but not their consumer would leave the
# interface unversioned on one side. See DESIGN_DECISIONS.md.
#
# NOT host-portable as-is. Host-specific assumptions:
#   repo path    /home/salatiel/work/infra_populi
#   SSH aliases  puppet8master, puppet8master-rsync, puppet8node
#   master paths /etc/puppetlabs/code/environments/production/...
#   params dir   ~/.config/infra_populi/params  (UNTRACKED: environment-specific
#                values, deliberately not versioned - see the tooling-tracking
#                decision in DESIGN_DECISIONS.md)
# Parameterizing these via environment variables is a known future improvement.
# ---------------------------------------------------------------------------

set -euo pipefail

# ----------------------------
# Config
# ----------------------------
LOCAL_REPO="/home/salatiel/work/infra_populi"
CLASSIFIER="${LOCAL_REPO}/.codex_state/gen_migration_order.py"

MASTER_HOST="puppet8master"
MASTER_RSYNC_HOST="puppet8master-rsync"
NODE_HOST="puppet8node"

MASTER_MODULE_DIR="/etc/puppetlabs/code/environments/production/modules/puppet_infrastructure"
MASTER_NODE_FILE="/etc/puppetlabs/code/environments/production/manifests/nodes/puppet8node.pp"

PARAMS_DIR="${HOME}/.config/infra_populi/params"

# ----------------------------
# Helpers
# ----------------------------
die() { echo "ERROR: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }

json_params_path_for_class() {
  local cls="$1"
  echo "${PARAMS_DIR}/${cls}.json"
}

classify_target() {
  local requested="$1"
  local short="${requested#puppet_infrastructure::}"
  local raw parsed rc line
  local -a records=()

  [[ -n "$short" ]] || die "Classification lookup failed for class '${requested}': empty class name"

  set +e
  raw="$(python3 "$CLASSIFIER" --classify "$short" 2>&1)"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    die "Classification lookup failed for class '${requested}': ${raw}"
  fi

  set +e
  parsed="$(python3 - "$requested" "$short" "$raw" 2>&1 <<'PY'
import json
import sys

requested, short, raw = sys.argv[1:]

def fail(message):
    print(message)
    raise SystemExit(1)

try:
    data = json.loads(raw)
except (TypeError, json.JSONDecodeError) as exc:
    fail(f"lookup returned invalid JSON: {exc}")

if not isinstance(data, dict):
    fail("lookup JSON is not an object")

name = data.get("name")
if name != short:
    fail(f"lookup returned unexpected name {name!r}")

resource_type = data.get("resource_type")
if resource_type not in {"class", "define"}:
    fail(f"resource_type is missing or invalid: {resource_type!r}")

title = data.get("title", "")
if not isinstance(title, str):
    fail(f"title is not a string: {title!r}")
if resource_type == "define" and not title:
    fail("define has an empty title")
if "\n" in title or "\r" in title:
    fail("title contains a newline")

required_base = data.get("required_base")
if not isinstance(required_base, list):
    fail(f"required_base is missing or is not a list: {required_base!r}")
for base in required_base:
    if not isinstance(base, str) or not base:
        fail(f"required_base contains an invalid class name: {base!r}")
    if "\n" in base or "\r" in base:
        fail(f"required_base contains a newline: {base!r}")

print(f"RESOURCE_TYPE={resource_type}")
print(f"TITLE={title}")
for base in required_base:
    print(f"BASE={base}")
print("END")
PY
)"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    die "Invalid classification for class '${requested}': ${parsed}"
  fi

  CLASSIFY_SHORT="$short"
  CLASSIFY_RESOURCE_TYPE=""
  CLASSIFY_TITLE=""
  CLASSIFY_REQUIRED_BASES=()
  mapfile -t records <<< "$parsed"
  for line in "${records[@]}"; do
    case "$line" in
      RESOURCE_TYPE=*) CLASSIFY_RESOURCE_TYPE="${line#RESOURCE_TYPE=}" ;;
      TITLE=*) CLASSIFY_TITLE="${line#TITLE=}" ;;
      BASE=*) CLASSIFY_REQUIRED_BASES+=("${line#BASE=}") ;;
      END) ;;
      *) die "Invalid classification for class '${requested}': unexpected parsed field" ;;
    esac
  done
}

declare -a EXPANDED_CLASSES=()
declare -A EXPANSION_STATE=()

expand_one_class() {
  local requested="$1"
  local short="${requested#puppet_infrastructure::}"
  local cls="puppet_infrastructure::${short}"
  local state="${EXPANSION_STATE[$cls]-}"
  local base
  local -a required_bases=()

  [[ "$state" == "2" ]] && return
  [[ "$state" != "1" ]] || die "Circular required_base dependency while expanding class '${cls}'"

  classify_target "$cls"
  required_bases=("${CLASSIFY_REQUIRED_BASES[@]}")
  EXPANSION_STATE["$cls"]="1"

  for base in "${required_bases[@]}"; do
    expand_one_class "$base"
  done

  EXPANSION_STATE["$cls"]="2"
  EXPANDED_CLASSES+=("$cls")
}

expand_target_classes() {
  local target
  EXPANDED_CLASSES=()
  EXPANSION_STATE=()
  for target in "$@"; do
    expand_one_class "$target"
  done
}

render_manifest_lines_for_classes() {
  local classes=("$@")
  local cls pfile resource_type title
  for cls in "${classes[@]}"; do
    classify_target "$cls"
    resource_type="$CLASSIFY_RESOURCE_TYPE"
    title="$CLASSIFY_TITLE"
    pfile="$(json_params_path_for_class "$cls")"
    if [[ -f "$pfile" ]]; then
      python3 - "$cls" "$pfile" "$resource_type" "$title" <<'PY'
import json, sys
cls = sys.argv[1]
path = sys.argv[2]
resource_type = sys.argv[3]
title = sys.argv[4]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

def puppet_literal(v):
    if v is None: return "undef"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, str):
        s = v.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{s}'"
    if isinstance(v, list):
        return "[" + ", ".join(puppet_literal(x) for x in v) + "]"
    if isinstance(v, dict):
        items = []
        for k, vv in v.items():
            items.append(f"{puppet_literal(str(k))} => {puppet_literal(vv)}")
        return "{" + ", ".join(items) + "}"
    raise TypeError(type(v))

if resource_type == "class":
    print(f"class {{ '{cls}':")
else:
    print(f"{cls} {{ {puppet_literal(title)}:")
for k, v in data.items():
    print(f"  {k} => {puppet_literal(v)},")
print("}")
PY
    elif [[ "$resource_type" == "define" ]]; then
      die "Cannot render define '${cls}': required params file not found at ${pfile}"
    else
      echo "include ${cls}"
    fi
  done
}

render_managed_block() {
  expand_target_classes "$@"
  echo "# BEGIN CODEX MANAGED (do not edit by hand)"
  render_manifest_lines_for_classes "${EXPANDED_CLASSES[@]}"
  echo "# END CODEX MANAGED"
}

deploy_repo_to_master() {
  [[ -d "$LOCAL_REPO" ]] || die "Local repo not found: $LOCAL_REPO"
  echo "==> Deploying local repo to master module dir (root-owned via staging)"

  local stage_dir="/var/tmp/infra_populi_stage/puppet_infrastructure"
  # 1) rsync to a writable staging location
  rsync -a --delete \
    --no-owner --no-group --no-perms --no-acls --no-xattrs \
    --exclude=.git/ --exclude=.github/ --exclude=.vscode/ --exclude=.idea/ --exclude=.codex_state/ \
    -e "ssh -T" \
    "${LOCAL_REPO}/" \
    "${MASTER_RSYNC_HOST}:${stage_dir}/"

  # 2) atomically replace the module dir as root
  ssh -T "$MASTER_HOST" "sudo -n rm -rf \"$MASTER_MODULE_DIR\" && sudo -n mkdir -p \"$(dirname "$MASTER_MODULE_DIR")\" && sudo -n mv \"$stage_dir\" \"$MASTER_MODULE_DIR\" && sudo -n chown -R root:root \"$MASTER_MODULE_DIR\"" 

}

update_node_codemgr_block() {
  local tmpfile remote_block
  tmpfile="$(mktemp)"
  trap '[[ -n "${tmpfile-}" ]] && rm -f "$tmpfile"' RETURN

  echo "==> Building managed block"
  render_managed_block "$@" > "$tmpfile"

  remote_block="/tmp/codex_block_$$.txt"

  echo "==> Uploading block to master: $remote_block"
  scp -q "$tmpfile" "${MASTER_HOST}:$remote_block"

  echo "==> Updating CODEX block in ${MASTER_NODE_FILE} on master"
  ssh -T "$MASTER_HOST" "sudo -n bash -s -- '$MASTER_NODE_FILE' '$remote_block'" <<'REMOTE'
set -euo pipefail
NODE_FILE="$1"
BLOCK_FILE="$2"

test -f "$NODE_FILE" || { echo "Node file not found: $NODE_FILE" >&2; exit 1; }
test -f "$BLOCK_FILE" || { echo "Block file not found: $BLOCK_FILE" >&2; exit 1; }

grep -q "^[[:space:]]*# BEGIN CODEX MANAGED" "$NODE_FILE" || { echo "Missing BEGIN marker in $NODE_FILE" >&2; exit 1; }
grep -q "^[[:space:]]*# END CODEX MANAGED" "$NODE_FILE" || { echo "Missing END marker in $NODE_FILE" >&2; exit 1; }

awk -v blockfile="$BLOCK_FILE" '
  BEGIN {
    inblock=0
    while ((getline line < blockfile) > 0) { block[++n]=line }
    close(blockfile)
  }
  {
    if ($0 ~ /^[[:space:]]*# BEGIN CODEX MANAGED/) {
      for (i=1;i<=n;i++) print block[i]
      inblock=1
      next
    }
    if ($0 ~ /^[[:space:]]*# END CODEX MANAGED/ && inblock==1) {
      inblock=0
      next
    }
    if (inblock==0) print
  }
' "$NODE_FILE" > "${NODE_FILE}.tmp"

mv "${NODE_FILE}.tmp" "$NODE_FILE"
rm -f "$BLOCK_FILE"
REMOTE
}

run_agent_once() {
  # Puppet exit codes: 0 = no changes, 2 = changes applied, others = failure
  local out rc
  set +e
  out="$(ssh "$NODE_HOST" "sudo /opt/puppetlabs/bin/puppet agent -t" 2>&1)"
  rc=$?
  set -e
  echo "$out"
  if [[ $rc -eq 0 || $rc -eq 2 ]]; then
    return 0
  fi
  return $rc
}


main() {
  need_cmd python3

  [[ $# -ge 1 ]] || die "Usage: $0 [--render-only] <class1> [class2 ...]"

  if [[ "$1" == "--render-only" ]]; then
    shift
    [[ $# -ge 1 ]] || die "Usage: $0 --render-only <class1> [class2 ...]"
    render_managed_block "$@"
    exit 0
  fi

  need_cmd rsync
  need_cmd ssh
  need_cmd scp

  local classes=("$@")

  mkdir -p "$PARAMS_DIR"

  deploy_repo_to_master
  update_node_codemgr_block "${classes[@]}"

  echo "==> Running puppet agent (need 2 successful runs; fail if 2nd run applies changes)"
  local out1 out2

  out1="$(run_agent_once)" || { echo "$out1"; die "Agent run 1 failed"; }
  echo "$out1"

  out2="$(run_agent_once)" || { echo "$out2"; die "Agent run 2 failed"; }
  echo "$out2"

  # Practical idempotency: fail only if 2nd run shows "changes applied"
  if echo "$out2" | grep -E "Notice: .*changed|Notice: .*created|Notice: .*defined content as|Info: .*Scheduling refresh of" >/dev/null 2>&1; then
    die "Run 2 still applied changes (not idempotent yet). Fix and re-run."
  fi

  echo "GREEN: 2 successful runs (practical idempotency)."
}

main "$@"
