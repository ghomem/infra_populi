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
#   SSH aliases  puppet8master, puppet8master-rsync, the node's alias (nodes.yml; default puppet8node)
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
# The node comes from the lab inventory (.codex_state/lab/nodes.yml, HQ 2026-11-16 item 2): --node KIND, else the
# plan row's `node`, else the default. select_node sets NODE_HOST and MASTER_NODE_FILE (nodes/<certname>.pp).
NODES_TOOL="${LOCAL_REPO}/.codex_state/tools/nodes.py"
NODE_KIND_REQUEST=""
NODE_HOST=""
NODE_KIND=""
NODE_CERTNAME=""
NODE_OS_FAMILY=""

# The module's name, single source (metadata.json, module_name.py); OLD_MODULE is the name the baseline carries.
MODULE="$(python3 "${LOCAL_REPO}/.codex_state/tools/module_name.py")" || { echo "ERROR: no module name" >&2; exit 1; }
PREFIX="${MODULE}::"
OLD_MODULE="puppet_infrastructure"
MASTER_MODULE_DIR="/etc/puppetlabs/code/environments/production/modules/${MODULE}"
MASTER_NODES_DIR="/etc/puppetlabs/code/environments/production/manifests/nodes"
MASTER_NODE_FILE=""

PARAMS_DIR="${HOME}/.config/infra_populi/params"
FIXTURE_DIR="${LOCAL_REPO}/.codex_state/tools/tests/fixtures"
REVERT_TOOL="${LOCAL_REPO}/.codex_state/tools/revert_node.sh"
COMPILE_DIR="${LOCAL_REPO}/.codex_state/tools/compile"
RECORDS_TOOL="${LOCAL_REPO}/.codex_state/tools/records.py"
# HQ 2026-11-10 ruling 2: every ssh/rsync of the harness goes through a ControlMaster shim (one ESTABLISHED
# connection; firewall_secure rate-limits NEW SSH connections). scp keeps its own ssh path.
PATH="${LOCAL_REPO}/.codex_state/tools/sshmux:${PATH}"
METRICS_TOOL="${LOCAL_REPO}/.codex_state/tools/metrics.py"
LAB_LOCK_TOOL="${LOCAL_REPO}/.codex_state/tools/lab_lock.sh"

# GREEN v2 (ruling 2 / step 1.1): every agent run has an outer timeout; run 2 must exit 0.
AGENT_TIMEOUT_SECONDS="${AGENT_TIMEOUT_SECONDS:-600}"
# "defined '<attr>' as" is how Resource API types (e.g. puppetlabs-firewall 8) report a creation.
RUN2_FORBIDDEN_RE="Notice: .*changed|Notice: .*created|Notice: .*defined content as|Notice: .*defined '[^']+' as|Notice: .*executed successfully|Notice: .*removed|Info: .*Scheduling refresh of"

# ----------------------------
# Helpers
# ----------------------------
die() { HARNESS_REASON="$*"; echo "ERROR: $*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing command: $1"; }

json_params_path_for_class() {
  # A base class applied FOR a target may carry a per-target fixture (params/for/<target>/<class>.json: how production
  # configures that base on such nodes, e.g. nginx_base's mail flag for nginx_frontend_mail, 2026-11-17); then a node
  # kind's own fixture (params/<kind>/<class>.json); else the shared one (params/<class>.json).
  local cls="$1" target
  for target in "${PARAMS_TARGETS[@]}"; do
    target="${PREFIX}${target#"$PREFIX"}"  # the command line may give the short name
    if [[ "$target" != "$cls" && -f "${PARAMS_DIR}/for/${target}/${cls}.json" ]]; then
      echo "${PARAMS_DIR}/for/${target}/${cls}.json"
      return
    fi
  done
  # HQ 2026-11-23 ruling 1a: a Phase 3 variant run's own params fixture for the target class (P8_PARAMS_VARIANT).
  local first="${PREFIX}${PARAMS_TARGETS[0]#"$PREFIX"}"
  if [[ -n "${P8_PARAMS_VARIANT:-}" && "$cls" == "$first" ]]; then
    [[ -f "${PARAMS_DIR}/variants/${P8_PARAMS_VARIANT}/${cls}.json" ]] ||
      die "params variant ${P8_PARAMS_VARIANT}: ${PARAMS_DIR}/variants/${P8_PARAMS_VARIANT}/${cls}.json is missing"
    echo "${PARAMS_DIR}/variants/${P8_PARAMS_VARIANT}/${cls}.json"
    return
  fi
  if [[ -n "$NODE_KIND" && -f "${PARAMS_DIR}/${NODE_KIND}/${cls}.json" ]]; then
    echo "${PARAMS_DIR}/${NODE_KIND}/${cls}.json"
  else
    echo "${PARAMS_DIR}/${cls}.json"
  fi
}

select_node() {
  # select_node <target>...: the lab node these targets are tested on. All targets must name the same node.
  local env first="" cls kind
  if [[ -n "$NODE_KIND_REQUEST" ]]; then
    env="$(python3 "$NODES_TOOL" env --node "$NODE_KIND_REQUEST")" || die "No usable lab node '${NODE_KIND_REQUEST}' (nodes.yml)."
  else
    if [[ $# -ge 1 && "$1" != fixture:* ]]; then first="${1#"$PREFIX"}"; fi
    env="$(python3 "$NODES_TOOL" env ${first:+--class "$first"})" || die "No usable lab node for ${first:-the default} (nodes.yml)."
    for cls in "$@"; do
      [[ "$cls" != fixture:* ]] || continue
      kind="$(python3 "$NODES_TOOL" get --class "${cls#"$PREFIX"}" kind)" || die "No usable lab node for ${cls}."
      [[ "$kind" == "$(sed -n 's/^NODE_KIND=//p' <<<"$env")" ]] ||
        die "The targets are tested on different lab nodes (${cls} on ${kind}); run them separately."
    done
  fi
  eval "$env"
  NODE_HOST="$NODE_ALIAS"
  MASTER_NODE_FILE="${MASTER_NODES_DIR}/${NODE_CERTNAME}.pp"
  echo "==> Lab node: ${NODE_KIND} (${NODE_HOST}, certname ${NODE_CERTNAME}, ${NODE_OS_FAMILY})"
}

classify_target() {
  local requested="$1"
  local short="${requested#"$PREFIX"}"
  local raw parsed rc line
  local -a records=()

  [[ -n "$short" ]] || die "Classification lookup failed for class '${requested}': empty class name"

  local family
  family="$(target_os_family)"
  set +e
  # HQ 2026-11-18 ruling A2: required_base entries qualified [Debian]/[RedHat] follow the target node's OS family.
  raw="$(python3 "$CLASSIFIER" --classify "$short" ${family:+--os-family "$family"} 2>&1)"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    die "Classification lookup failed for class '${requested}': ${raw}"
  fi

  set +e
  parsed="$(python3 - "$requested" "$short" "$raw" 2>&1 <<'PY'
import json
import re
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

required_external = data.get("required_external")
if not isinstance(required_external, list):
    fail(f"required_external is missing or is not a list: {required_external!r}")
for external in required_external:
    if not isinstance(external, str) or not external:
        fail(f"required_external contains an invalid class name: {external!r}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(?:::[a-z][a-z0-9_]*)*", external):
        fail(f"required_external contains an invalid class name: {external!r}")

owner_validated = data.get("owner_validated")
if not isinstance(owner_validated, str):
    fail(f"owner_validated is missing or is not a string: {owner_validated!r}")
if owner_validated and not re.fullmatch(r"[A-Za-z0-9_]+", owner_validated):
    fail(f"owner_validated contains an invalid class short-name: {owner_validated!r}")

print(f"RESOURCE_TYPE={resource_type}")
print(f"TITLE={title}")
for base in required_base:
    print(f"BASE={base}")
for external in required_external:
    print(f"EXTERNAL={external}")
node_fixture = data.get("node_fixture", "")
if not isinstance(node_fixture, str) or (node_fixture and not re.fullmatch(r"[a-z0-9_]+", node_fixture)):
    fail(f"node_fixture is invalid: {node_fixture!r}")

print(f"OWNER_VALIDATED={owner_validated}")
print(f"NODE_FIXTURE={node_fixture}")
expected = data.get("expected_run2_events", [])
if not isinstance(expected, list) or any(not isinstance(e, str) or not re.fullmatch(r"[A-Z][A-Za-z0-9_:]*\[[^\]\[\n]+\]", e) for e in expected):
    fail(f"expected_run2_events is invalid: {expected!r}")
for e in expected:
    print(f"EXPECTED_RUN2={e}")
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
  CLASSIFY_REQUIRED_EXTERNALS=()
  CLASSIFY_OWNER_VALIDATED=""
  CLASSIFY_NODE_FIXTURE=""
  CLASSIFY_EXPECTED_RUN2=()
  mapfile -t records <<< "$parsed"
  for line in "${records[@]}"; do
    case "$line" in
      RESOURCE_TYPE=*) CLASSIFY_RESOURCE_TYPE="${line#RESOURCE_TYPE=}" ;;
      TITLE=*) CLASSIFY_TITLE="${line#TITLE=}" ;;
      BASE=*) CLASSIFY_REQUIRED_BASES+=("${line#BASE=}") ;;
      EXTERNAL=*) CLASSIFY_REQUIRED_EXTERNALS+=("${line#EXTERNAL=}") ;;
      OWNER_VALIDATED=*) CLASSIFY_OWNER_VALIDATED="${line#OWNER_VALIDATED=}" ;;
      NODE_FIXTURE=*) CLASSIFY_NODE_FIXTURE="${line#NODE_FIXTURE=}" ;;
      EXPECTED_RUN2=*) CLASSIFY_EXPECTED_RUN2+=("${line#EXPECTED_RUN2=}") ;;
      END) ;;
      *) die "Invalid classification for class '${requested}': unexpected parsed field" ;;
    esac
  done
}

guard_owner_validated_targets() {
  local requested owner
  for requested in "$@"; do
    classify_target "$requested"
    owner="$CLASSIFY_OWNER_VALIDATED"
    if [[ -n "$owner" ]]; then
      die "Target '${PREFIX}${CLASSIFY_SHORT}' is owner_validated by '${PREFIX}${owner}'; it must be validated via that owner's migration."
    fi
  done
}

declare -a EXPANDED_CLASSES=()
declare -a EXPANDED_CLASS_KINDS=()
declare -A EXPANSION_STATE=()

expand_one_class() {
  local requested="$1"
  local kind="${2:-internal}"
  local short cls state_key state base external
  local -a required_bases=()
  local -a required_externals=()

  if [[ "$kind" == "external" ]]; then
    cls="$requested"
  else
    short="${requested#"$PREFIX"}"
    cls="${PREFIX}${short}"
  fi
  state_key="${kind}:${cls}"
  state="${EXPANSION_STATE[$state_key]-}"

  [[ "$state" == "2" ]] && return
  [[ "$state" != "1" ]] || die "Circular required_base dependency while expanding class '${cls}'"

  if [[ "$kind" != "external" && "${NO_EXPAND:-0}" != "1" ]]; then
    classify_target "$cls"
    required_bases=("${CLASSIFY_REQUIRED_BASES[@]}")
    required_externals=("${CLASSIFY_REQUIRED_EXTERNALS[@]}")
  fi
  EXPANSION_STATE["$state_key"]="1"

  for base in "${required_bases[@]}"; do
    expand_one_class "$base" internal
  done
  for external in "${required_externals[@]}"; do
    # A Debian-only external (puppetlabs-apt fails on any other OS family) is not declared on a RedHat target
    # (2026-11-18, the rhel9 pass: nginx_base's `apt` is for its Ubuntu-only Exec['apt_update']).
    if [[ " ${DEBIAN_ONLY_EXTERNALS[*]} " == *" ${external} "* && "$(target_os_family)" == "RedHat" ]]; then
      echo "==> required_external ${external} not declared: Debian-only, the target is RedHat" >&2
      continue
    fi
    expand_one_class "$external" external
  done

  EXPANSION_STATE["$state_key"]="2"
  EXPANDED_CLASSES+=("$cls")
  EXPANDED_CLASS_KINDS+=("$kind")
}

declare -a PARAMS_TARGETS=()
readonly -a DEBIAN_ONLY_EXTERNALS=(apt)
declare -a COMPILE_DIGEST_PATHS=()  # compile-only --file-digest: File titles whose rendered content is hashed
COMPILE_FACTS_FAMILY=""  # compile-only: the OS family of the facts the compile uses (redhat/native rewrite)

target_os_family() { echo "${COMPILE_FACTS_FAMILY:-$NODE_OS_FAMILY}"; }

expand_target_classes() {
  local target
  PARAMS_TARGETS=("$@")
  EXPANDED_CLASSES=()
  EXPANDED_CLASS_KINDS=()
  EXPANSION_STATE=()
  for target in "$@"; do
    expand_one_class "$target" internal
  done
}

render_manifest_lines_for_classes() {
  local classes=("$@")
  local index cls kind pfile resource_type title
  for index in "${!classes[@]}"; do
    cls="${classes[$index]}"
    kind="${EXPANDED_CLASS_KINDS[$index]}"
    if [[ "$kind" == "external" ]]; then
      echo "include ${cls}"
      continue
    fi
    classify_target "$cls"
    resource_type="$CLASSIFY_RESOURCE_TYPE"
    title="$CLASSIFY_TITLE"
    pfile="$(json_params_path_for_class "$cls")"
    if [[ "${COMPILE_DEFAULTS:-0}" == "1" ]]; then
      # Default-parameter variant (step 2.2): ignore the params fixture.
      if [[ "$resource_type" == "define" ]]; then
        echo "${cls} { '${title}': }"
      else
        echo "include ${cls}"
      fi
    elif [[ -f "$pfile" ]]; then
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
    elif [[ "$resource_type" == "define" && "${COMPILE_ONLY:-0}" == "1" ]]; then
      # Compile-only: render the define with its plan title; a mandatory parameter then shows up
      # as a compile error instead of aborting the render.
      echo "${cls} { '${title}': }"
    elif [[ "$resource_type" == "define" ]]; then
      die "Cannot render define '${cls}': required params file not found at ${pfile}"
    else
      echo "include ${cls}"
    fi
  done
}

render_managed_block() {
  if [[ -n "${FIXTURE_NAME:-}" ]]; then
    render_fixture_block "$FIXTURE_NAME"
    return
  fi
  expand_target_classes "$@"
  echo "# BEGIN CODEX MANAGED (do not edit by hand)"
  render_node_fixtures "$@"
  render_manifest_lines_for_classes "${EXPANDED_CLASSES[@]}"
  echo "# END CODEX MANAGED"
}

render_node_fixtures() {
  # HQ 2026-10-27 ruling 7: a target's plan `node_fixture` (synthetic paths/users/commands of a service the lab node
  # does not run) is applied with it. MOCK-APPLY: the GREEN proves syntax + idempotency, not behaviour.
  local target path
  local -A seen=()
  for target in "$@"; do
    classify_target "$target"
    [[ -n "$CLASSIFY_NODE_FIXTURE" && -z "${seen[$CLASSIFY_NODE_FIXTURE]-}" ]] || continue
    seen[$CLASSIFY_NODE_FIXTURE]=1
    path="${FIXTURE_DIR}/node/${CLASSIFY_NODE_FIXTURE}.pp"
    [[ -f "$path" ]] || die "Node fixture not found: ${path}"
    echo "# MOCK-APPLY node fixture: ${CLASSIFY_NODE_FIXTURE}"
    cat "$path"
  done
  # HQ 2026-11-27 item 4: a Phase 3 variant's own node fixture (state the class needs before it applies), after the plan's
  if [[ -n "${P8_NODE_FIXTURE_VARIANT:-}" ]]; then
    [[ "$P8_NODE_FIXTURE_VARIANT" =~ ^[a-z0-9_]+$ ]] || die "Invalid variant node fixture: '${P8_NODE_FIXTURE_VARIANT}'"
    path="${FIXTURE_DIR}/node/${P8_NODE_FIXTURE_VARIANT}.pp"
    [[ -f "$path" ]] || die "Node fixture not found: ${path}"
    echo "# MOCK-APPLY node fixture: ${P8_NODE_FIXTURE_VARIANT}"
    cat "$path"
  fi
}

# The remote command prefix that removes the module's directory under its old name once the module is renamed (empty
# while the names agree).
old_module_cleanup() {
  [[ "$MODULE" != "$OLD_MODULE" ]] || return 0
  printf 'sudo -n rm -rf "%s/%s" && ' "$(dirname "$MASTER_MODULE_DIR")" "$OLD_MODULE"
}

deploy_repo_to_master() {
  [[ -d "$LOCAL_REPO" ]] || die "Local repo not found: $LOCAL_REPO"
  echo "==> Deploying local repo to master module dir (root-owned via staging)"

  local stage_dir="/var/tmp/infra_populi_stage/${MODULE}"
  # 1) rsync to a writable staging location
  rsync -a --delete \
    --no-owner --no-group --no-perms --no-acls --no-xattrs \
    --exclude=.git/ --exclude=.github/ --exclude=.vscode/ --exclude=.idea/ --exclude=.codex_state/ \
    -e "ssh -T" \
    "${LOCAL_REPO}/" \
    "${MASTER_RSYNC_HOST}:${stage_dir}/"

  # 2) atomically replace the module dir as root
  # after the rename, the module's old directory goes with the deploy (one module under one name in the environment)
  ssh -T "$MASTER_HOST" "$(old_module_cleanup)sudo -n rm -rf \"$MASTER_MODULE_DIR\" && sudo -n mkdir -p \"$(dirname "$MASTER_MODULE_DIR")\" && sudo -n mv \"$stage_dir\" \"$MASTER_MODULE_DIR\" && sudo -n chown -R root:root \"$MASTER_MODULE_DIR\"" 

}

# HQ 2026-11-18 ruling C2: a node that is itself a Puppet server (nodes.yml capability puppet-server, the master-role
# node) serves the module under test from its own code tree, as a production master does: the same tree the master
# gets, deployed after the revert. The node's own environment holds nothing else of this repository.
deploy_repo_to_node_server() {
  local caps stage_dir="/var/tmp/infra_populi_stage/${MODULE}"
  caps="$(python3 "$NODES_TOOL" get --node "$NODE_KIND" capabilities)" || die "Could not read the capabilities of node ${NODE_KIND}"
  [[ " ${caps} " == *" puppet-server "* ]] || return 0
  echo "==> Deploying local repo to the node's own Puppet server code tree (${NODE_HOST}:${MASTER_MODULE_DIR})"
  ssh -T "$NODE_HOST" "mkdir -p \"$(dirname "$stage_dir")\"" || die "Could not prepare the staging directory on ${NODE_HOST}"
  rsync -a --delete \
    --no-owner --no-group --no-perms --no-acls --no-xattrs \
    --exclude=.git/ --exclude=.github/ --exclude=.vscode/ --exclude=.idea/ --exclude=.codex_state/ \
    -e "ssh -T" \
    "${LOCAL_REPO}/" \
    "${NODE_HOST}:${stage_dir}/" || die "Could not copy the module to ${NODE_HOST}"
  ssh -T "$NODE_HOST" "$(old_module_cleanup)sudo -n rm -rf \"$MASTER_MODULE_DIR\" && sudo -n mkdir -p \"$(dirname "$MASTER_MODULE_DIR")\" && sudo -n mv \"$stage_dir\" \"$MASTER_MODULE_DIR\" && sudo -n chown -R root:root \"$MASTER_MODULE_DIR\"" ||
    die "Could not install the module in ${NODE_HOST}'s code tree"
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

run_agent() {
  # Puppet detailed exit codes (-t implies them): 0 = no changes, 2 = changes applied,
  # 4/6 = failures. 124/137 = killed by the outer timeout.
  # HQ after batch 20, item 6 (a harness mode that tolerates a running agent): when the class starts the agent daemon,
  # a daemon run may hold the agent lock; the harness's run waits for it (polling every 10 s, at most
  # AGENT_LOCK_WAIT_SECONDS) instead of failing "already in progress".
  timeout --kill-after=15 "$AGENT_TIMEOUT_SECONDS" \
    ssh "$NODE_HOST" "sudo /opt/puppetlabs/bin/puppet agent -t --waitforlock 10 --maxwaitforlock ${AGENT_LOCK_WAIT_SECONDS:-600}" 2>&1
}

# The node's clock now (epoch seconds; the node's clock is checked against the laptop's before run 1).
node_now() {
  timeout 30 ssh "$NODE_HOST" "date +%s" 2>/dev/null
}

# What the agent DAEMON logged between two node times. Every agent run logs to the journal (identifier puppet-agent),
# the harness's own `puppet agent -t` runs included (from the ssh session's scope); the daemon's come from the unit
# puppet.service, which separates them. One line per message; empty when the daemon made no run. The master's stored
# reports are not used: they are named by the minute, so two runs in one minute overwrite each other.
daemon_log_between() {
  timeout 60 ssh "$NODE_HOST" "sudo -n journalctl --no-pager -q -o cat -u puppet.service -t puppet-agent --since @$1 --until @$2"
}

die_agent_rc() {
  local run="$1" rc="$2"
  if [[ $rc -eq 124 || $rc -eq 137 ]]; then
    die "Agent run ${run} timed out after ${AGENT_TIMEOUT_SECONDS}s (node severed or hung?)."
  fi
  die "Agent run ${run} failed (exit ${rc})."
}

coverage_check() {
  # Step 1.3: the target's resources must be in the applied catalog. Filtering runs ON THE NODE and
  # prints only Type[title] of resources tagged with a target, so nothing else in the catalog (e.g.
  # the lab-local passwd_common, ruling 6a) ever leaves the node. Fails if a target has 0 concrete
  # resources (defined-type instances are listed but not counted).
  local -a targets=()
  local cls report rc
  for cls in "$@"; do targets+=("${PREFIX}${cls#"$PREFIX"}"); done
  report="$(timeout 60 ssh "$NODE_HOST" "sudo -n python3 - ${NODE_CERTNAME} ${targets[*]}" <<'PY'
import json, sys
catalog = "/opt/puppetlabs/puppet/cache/client_data/catalog/%s.json" % sys.argv[1]
resources = json.load(open(catalog))["resources"]
empty = 0
for target in sys.argv[2:]:
    tag = target.lower()
    mine = [r for r in resources if tag in r.get("tags", []) and r["type"] not in ("Class", "Stage", "Node")]
    concrete = [r for r in mine if "::" not in r["type"]]
    print("COVERAGE %s: %d concrete resources (+%d defined-type instances)"
          % (target, len(concrete), len(mine) - len(concrete)))
    for r in mine:
        print("  %s[%s]" % (r["type"], r["title"]))
    empty += not concrete
sys.exit(3 if empty else 0)
PY
)" && rc=0 || rc=$?
  echo "$report"
  COVERAGE_REPORT="$report"
  if [[ $rc -eq 3 && -n "${P8_PARAMS_VARIANT:-}" && "${P8_VARIANT_NO_RESOURCES:-}" == 1 ]]; then
    # HQ 2026-11-23 ruling 1a: a Phase 3 params variant whose behaviour is to declare nothing (no_resources: true)
    echo "COVERAGE: no concrete resources, as the params variant ${P8_PARAMS_VARIANT} declares (no_resources)"
    return 0
  fi
  [[ $rc -ne 3 ]] || die "Coverage: a target has no concrete resources in the applied catalog (body skipped by a conditional? wrong fixture?)."
  [[ $rc -eq 0 ]] || die "Coverage check could not read the node's cached catalog (exit ${rc})."
}

compile_on_master() {
  # Step 2.2: compile the node's catalog on the master with live node facts (optionally rewritten
  # to a RedHat family); the node is never touched beyond reading its facts. Prints only what
  # compile/filter.rb prints. Returns 0 ok, 3 empty target, 4 unparseable, 5 compile failed.
  local variant="$1"; shift
  local -a targets=()
  local cls work facts_json rc
  for cls in "$@"; do targets+=("${PREFIX}${cls#"$PREFIX"}"); done
  work="$(mktemp -d)"
  mkdir "$work/facts"
  facts_json="$(timeout 60 ssh "$NODE_HOST" "sudo -n /opt/puppetlabs/bin/puppet facts show --render-as json" 2>/dev/null)" ||
    { rm -r "$work"; die "Could not read facts from ${NODE_HOST} (is the node up?)"; }
  python3 "$COMPILE_DIR/facts.py" "$variant" "$NODE_CERTNAME" <<<"$facts_json" >"$work/facts/${NODE_CERTNAME}.yaml" ||
    { rm -r "$work"; die "Could not build ${variant} facts"; }
  cp "$COMPILE_DIR/run.sh" "$COMPILE_DIR/filter.rb" "$work/"
  printf '%s\n' "$MODULE" >"$work/module"
  # HQ 2026-11-18 ruling A1: a rendered file's sha256 (never its content) for a before/after comparison.
  [[ ${#COMPILE_DIGEST_PATHS[@]} -eq 0 ]] || printf '%s\n' "${COMPILE_DIGEST_PATHS[@]}" >"$work/digest_paths"
  rc=0
  # shellcheck disable=SC2029  # target names expand locally by design
  tar -C "$work" -cf - . | timeout 180 ssh -T "$MASTER_HOST" \
    "d=\$(mktemp -d /tmp/p8compile.XXXXXX) && tar -C \"\$d\" -xf - && bash \"\$d/run.sh\" \"\$d\" ${NODE_CERTNAME} ${targets[*]}; rc=\$?; sudo -n rm -rf \"\$d\"; exit \$rc" || rc=$?
  rm -r "$work"
  return "$rc"
}

# ----------------------------
# Step 3.4: per-attempt metrics events (best effort: a metrics failure never changes the verdict)
# ----------------------------
HARNESS_REASON=""
HARNESS_RUN1_EVENTS=""
HARNESS_REVERT_FIRST=0
declare -a HARNESS_CLASSES=() HARNESS_AGENT_RUNS=() EXPECTED_RUN2_REFS=() EXPECTED_RUN2_SOURCES=()

agent_run_summary() {
  local summary
  summary="$(timeout 30 ssh "$NODE_HOST" "sudo -n cat /opt/puppetlabs/puppet/public/last_run_summary.yaml; sudo -n grep -m1 '^transaction_uuid:' /opt/puppetlabs/puppet/cache/state/last_run_report.yaml" 2>/dev/null |
    python3 "$METRICS_TOOL" agent-summary 2>/dev/null)" && HARNESS_AGENT_RUNS+=("$summary") || true
}

# Bytes received on the node's NIC1 (the default-route interface) since its boot; empty when unreadable. The harness
# records the delta across its agent runs per class (HQ NAT review F: the data for a package-cache decision).
node_nic1_rx() {
  local rx
  # shellcheck disable=SC2016  # expanded on the node
  rx="$(timeout 30 ssh "$NODE_HOST" 'dev="$(ip -4 route show default | awk "{print \$5; exit}")"; cat "/sys/class/net/${dev}/statistics/rx_bytes"' 2>/dev/null)" || rx=""
  [[ "$rx" =~ ^[0-9]+$ ]] && printf '%s' "$rx"
  return 0
}

harness_metrics_event() {
  local rc="$1" cls json rx_end=""
  [[ ${#HARNESS_CLASSES[@]} -gt 0 && -z "${FIXTURE_NAME:-}" ]] || return 0
  [[ -z "${HARNESS_RX_START:-}" ]] || rx_end="$(node_nic1_rx)"
  json="$(P8_RUN2_SOURCES="$(printf '%s\n' "${EXPECTED_RUN2_SOURCES[@]-}")" P8_RUN2_HITS="${EXPECTED_RUN2_HITS:-}" python3 - "$rc" \
      "$HARNESS_REVERT_FIRST" "${HARNESS_RUN1_EVENTS:-null}" "${HARNESS_START/,/.}" "${EPOCHREALTIME/,/.}" \
      "$HARNESS_REASON" "${HARNESS_RX_START:-}" "$rx_end" "${HARNESS_AGENT_RUNS[@]}" <<'PY' 2>/dev/null
import json, os, sys
rc, rf, r1, t0, t1, reason, rx0, rx1, *runs = sys.argv[1:]
# a counter that went down means the node rebooted in between: no figure rather than a wrong one
rx = int(rx1) - int(rx0) if rx0.isdigit() and rx1.isdigit() and int(rx1) >= int(rx0) else None
own, inherited = [], {}
for src in filter(None, os.environ.get("P8_RUN2_SOURCES", "").splitlines()):  # one per line: refs contain spaces
    kind, _, rest = src.partition(":")
    if kind == "own":
        own.append(rest)
    elif kind == "inherited":
        ref, _, cls = rest.rpartition("@")
        inherited.setdefault(cls, []).append(ref)
hits = os.environ.get("P8_RUN2_HITS", "")
print(json.dumps({"rc": int(rc), "revert_first": rf == "1", "run1_events": None if r1 in ("", "null") else int(r1),
                  "duration_s": round(float(t1) - float(t0), 1), "reason": reason or None, "nic1_rx_bytes": rx,
                  "run2_expected": ({"hits": int(hits) if hits else 0, "own": own, "inherited": inherited}
                                    if own or inherited else None),
                  "agent_runs": [json.loads(r) for r in runs]}))
PY
)" || return 0
  for cls in "${HARNESS_CLASSES[@]}"; do
    python3 "$METRICS_TOOL" event "$cls" harness "$json" >/dev/null 2>&1 || true
  done
}

# HQ 2026-11-10 ruling 1: plan `expected_run2_events` of the target and its expanded required_base — the only
# resources allowed to report events on run 2 (each justified in the class header and checked by the reviewer).
collect_expected_run2() {
  # HQ 2026-11-11 ruling 6: record WHERE each expected ref comes from — the target's own plan entry, or inherited
  # from an expanded required_base class — so the run record and the batch report list it explicitly.
  local cls ref target is_target
  local -a targets=()
  EXPECTED_RUN2_REFS=()
  EXPECTED_RUN2_SOURCES=()
  [[ -z "${FIXTURE_NAME:-}" ]] || return 0
  for target in "$@"; do targets+=("${PREFIX}${target#"$PREFIX"}"); done
  expand_target_classes "$@"
  for cls in "${EXPANDED_CLASSES[@]}"; do
    [[ "$cls" == "$PREFIX"* ]] || continue
    classify_target "$cls"
    is_target=0
    for target in "${targets[@]}"; do [[ "$target" == "$cls" ]] && is_target=1; done
    for ref in "${CLASSIFY_EXPECTED_RUN2[@]}"; do
      EXPECTED_RUN2_REFS+=("$ref")
      if [[ $is_target -eq 1 ]]; then EXPECTED_RUN2_SOURCES+=("own:${ref}"); else EXPECTED_RUN2_SOURCES+=("inherited:${ref}@${cls#"$PREFIX"}"); fi
    done
  done
}

describe_expected_run2() {
  local src own="" inherited=""
  for src in "${EXPECTED_RUN2_SOURCES[@]}"; do
    case "$src" in
      own:*) own+="${own:+, }${src#own:}" ;;
      inherited:*) src="${src#inherited:}"; inherited+="${inherited:+, }${src%@*} via ${src##*@}" ;;
    esac
  done
  echo "own: ${own:-none}; inherited: ${inherited:-none}"
}

# The resources run 2's REPORT marks changed (Puppet's last-run report, read with the node's own Puppet ruby), one
# `CHANGED <ref>` line each: a change logged below notice (e.g. `notify { ...: loglevel => 'debug' }`) has no console
# line but still counts. Fails when the report cannot be read.
report_changed() {
  local changed
  changed="$(timeout 60 ssh "$NODE_HOST" 'sudo -n /opt/puppetlabs/puppet/bin/ruby - /opt/puppetlabs/puppet/cache/state/last_run_report.yaml' <<'RB'
require "puppet"
report = YAML.unsafe_load_file(ARGV[0])
report.resource_statuses.each { |ref, status| puts ref if status.changed }
RB
)" || return 1
  sed '/^$/d; s/^/CHANGED /' <<<"$changed"
}

# HQ review of the behaviour suite (2026-11-27) ruling 1: the gate is the behaviour suite's own
# (spec/behaviour/lib/behaviour/gate.py), one code path for this harness and the public runner. Either run's logged
# `Error:` line fails it, run 2's changes come from its console and its last-run report, and only the plan's
# expected_run2_events may remain. $1/$2 = run 1's exit code and output, $3/$4 = run 2's (with report_changed's lines).
# Prints the verdict as JSON.
apply_gate() {
  # The runs' outputs go through files: an agent run's output can exceed what one environment variable or argument
  # may hold (128 KiB on Linux; node_base's run 1 does), and the gate would then get no input at all.
  local gate_dir rc=0
  gate_dir="$(mktemp -d)"
  printf '%s' "$2" >"${gate_dir}/out1"
  printf '%s' "$4" >"${gate_dir}/out2"
  printf '%s\n' "${EXPECTED_RUN2_REFS[@]-}" >"${gate_dir}/expected"
  python3 - "$1" "$3" "$gate_dir" <<'PY' | PYTHONPATH="${LOCAL_REPO}/spec/behaviour/lib" python3 -m behaviour.gate || rc=$?
import json, sys
from pathlib import Path
rc1, rc2, d = int(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3])
print(json.dumps({"runs": [{"rc": rc1, "out": (d / "out1").read_text(errors="replace")},
                           {"rc": rc2, "out": (d / "out2").read_text(errors="replace")}],
                  "expected": [r for r in (d / "expected").read_text().splitlines() if r]}))
PY
  rm -r "$gate_dir"
  return "$rc"
}

render_fixture_block() {
  local name="$1" path
  [[ "$name" =~ ^[a-z0-9_]+$ ]] || die "Invalid fixture name: '${name}'"
  path="${FIXTURE_DIR}/${name}.pp"
  [[ -f "$path" ]] || die "Fixture not found: ${path}"
  echo "# BEGIN CODEX MANAGED (do not edit by hand)"
  cat "$path"
  echo "# END CODEX MANAGED"
}


# One lab run at a time (lab_lock.sh): every mode but --render-only writes the master's node file or runs the node.
take_lab_lock() {
  [[ -z "${P8_LAB_LOCKED:-}" ]] || return 0  # a parent (phase3 run, a caller holding the lock) already holds it
  local holder
  holder="$("$LAB_LOCK_TOOL" take "$$" "test_class.sh $*" 2>&1)" ||
    die "another lab run holds the lab lock (${holder}); refusing to run concurrently: it would rewrite the master's node file or the node under it"
  export P8_LAB_LOCKED=1
  LAB_LOCK_HELD=1
  trap release_lab_lock EXIT
}

# A laptop suspend cuts a run mid-request (2026-11-17: linux_policies_user's run 2 hung 557 s and failed when KDE's
# idle suspend paused the VMs). Every lab run holds a logind sleep/idle inhibitor for its lifetime where logind
# offers one; a lid close still suspends (logind's LidSwitchIgnoreInhibited default). P8_NO_SLEEP_INHIBIT=1 skips it.
inhibit_sleep() {
  [[ -z "${P8_SLEEP_INHIBITED:-}" && -z "${P8_NO_SLEEP_INHIBIT:-}" ]] || return 0
  command -v systemd-inhibit >/dev/null 2>&1 || return 0
  systemd-inhibit --what=sleep:idle --who=infra_populi --why=probe true >/dev/null 2>&1 || return 0
  export P8_SLEEP_INHIBITED=1
  exec systemd-inhibit --what=sleep:idle --who=infra_populi --why="lab run: test_class.sh $*" "$0" "$@"
}

release_lab_lock() {
  if [[ "${LAB_LOCK_HELD:-0}" == 1 ]]; then "$LAB_LOCK_TOOL" release "$$" || true; fi
}

main() {
  need_cmd python3
  [[ "${1:-}" == "--render-only" ]] || inhibit_sleep "$@"
  if [[ "${1:-}" == "--node" ]]; then
    NODE_KIND_REQUEST="${2:-}"
    [[ -n "$NODE_KIND_REQUEST" ]] || die "--node needs a kind (nodes.yml)"
    shift 2
  fi
  [[ "${1:-}" == "--render-only" ]] || take_lab_lock "$@"

  if [[ "${1:-}" == "--compile-only" ]]; then
    shift
    local variant=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --facts) variant="${2:-}"; shift 2 ;;
        --defaults) export COMPILE_DEFAULTS=1; shift ;;
        --no-expand) export NO_EXPAND=1; shift ;;
        --file-digest)
          [[ "${2:-}" == /* ]] || die "--file-digest needs an absolute File title"
          COMPILE_DIGEST_PATHS+=("$2"); shift 2 ;;
        *) break ;;
      esac
    done
    [[ -z "$variant" || "$variant" == "debian" || "$variant" == "redhat" || "$variant" == "native" ]] ||
      die "--facts must be debian, redhat or native"
    export COMPILE_ONLY=1
    [[ $# -ge 1 ]] || die "Usage: $0 --compile-only [--facts debian|redhat] [--defaults] [--no-expand] [--file-digest <path>]... <class1> [class2 ...]"
    need_cmd rsync; need_cmd ssh; need_cmd tar
    select_node "$@"
    if [[ -z "$variant" ]]; then
      if [[ "$NODE_OS_FAMILY" == "RedHat" ]]; then variant="native"; else variant="debian"; fi
    fi
    [[ ! ( "$variant" == "debian" && "$NODE_OS_FAMILY" == "RedHat" ) ]] ||
      die "--facts debian cannot rewrite a RedHat node's facts; use native"
    case "$variant" in
      redhat) COMPILE_FACTS_FAMILY="RedHat" ;;
      debian) COMPILE_FACTS_FAMILY="Debian" ;;
      *) COMPILE_FACTS_FAMILY="$NODE_OS_FAMILY" ;;
    esac
    guard_owner_validated_targets "$@"
    # SKIP_DEPLOY=1: the caller already deployed this tree (composite runner, step 2.2).
    [[ "${SKIP_DEPLOY:-0}" == "1" ]] || deploy_repo_to_master
    update_node_codemgr_block "$@"
    echo "==> Compiling on the master (facts: ${variant}; params: $([[ "${COMPILE_DEFAULTS:-0}" == 1 ]] && echo defaults || echo fixtures)); the node is not run"
    local crc=0
    compile_on_master "$variant" "$@" || crc=$?
    case "$crc" in
      0) echo "COMPILE OK (${variant}): $*" ;;
      3) die "Compile succeeded but a target has no concrete resources." ;;
      5) die "COMPILE FAILED (${variant}): $*" ;;
      *) die "Compile check failed (exit ${crc})." ;;
    esac
    exit 0
  fi

  local revert_first=0
  if [[ "${1:-}" == "--revert-first" ]]; then
    # Step 1.2: restore the node baseline before deploying, so run 1 is a first apply.
    revert_first=1
    shift
  fi

  [[ $# -ge 1 ]] || die "Usage: $0 [--revert-first] <class1> [class2 ...] | [--revert-first] --fixture <name> | --render-only <class1> [...]"

  if [[ "$1" == "--fixture" ]]; then
    # Engine self-test: apply a manifest from .codex_state/tools/tests/fixtures/ instead of a class.
    [[ $# -eq 2 ]] || die "Usage: $0 --fixture <name>"
    FIXTURE_NAME="$2"
    set -- "fixture:${FIXTURE_NAME}"
  fi

  if [[ "$1" == "--render-only" ]]; then
    [[ $revert_first -eq 0 ]] || die "--revert-first cannot be combined with --render-only"
    shift
    [[ $# -ge 1 ]] || die "Usage: $0 --render-only <class1> [class2 ...]"
    select_node "$@"
    guard_owner_validated_targets "$@"
    render_managed_block "$@"
    exit 0
  fi

  need_cmd rsync
  need_cmd ssh
  need_cmd scp

  local classes=("$@")
  select_node "${classes[@]}"
  [[ -n "${FIXTURE_NAME:-}" ]] || guard_owner_validated_targets "${classes[@]}"
  HARNESS_START="${EPOCHREALTIME}"
  HARNESS_REVERT_FIRST="$revert_first"
  HARNESS_CLASSES=("${classes[@]}")
  trap 'rc=$?; harness_metrics_event "$rc"; release_lab_lock' EXIT

  mkdir -p "$PARAMS_DIR"

  if [[ $revert_first -eq 1 ]]; then
    echo "==> Reverting the node to its baseline first"
    local revert_out revert_json cls
    revert_out="$("$REVERT_TOOL" --node "$NODE_KIND")" || { echo "$revert_out"; die "Node revert failed; not running the class on an unknown node state."; }
    echo "$revert_out"
    revert_json="$(sed -n 's/^REVERT_METRICS //p' <<<"$revert_out" | tail -1)"
    if [[ -n "$revert_json" && -z "${FIXTURE_NAME:-}" ]]; then
      for cls in "${classes[@]}"; do python3 "$METRICS_TOOL" event "$cls" revert "$revert_json" >/dev/null 2>&1 || true; done
    fi
  fi

  deploy_repo_to_master
  deploy_repo_to_node_server
  update_node_codemgr_block "${classes[@]}"

  # HQ batch-3 acceptance, item 1: is the node still on the latest revert's boot with no agent run since?
  # Checked right before run 1 and carried in the GREEN stamp; record_green.sh refuses a stale one.
  local fresh_boot="" stale_reason="" token fresh_err
  if token="$(timeout 30 "$REVERT_TOOL" --node "$NODE_KIND" --node-state 2>/dev/null)" && [[ -n "$token" ]]; then
    fresh_err="$(mktemp)"
    fresh_boot="$(python3 "$RECORDS_TOOL" fresh-check --node "$NODE_KIND" <<<"$token" 2>"$fresh_err")" ||
      { stale_reason="$(cat "$fresh_err")"; fresh_boot=""; }
    rm -f "$fresh_err"
  else
    stale_reason="the node state token could not be read"
  fi
  if [[ -n "$fresh_boot" ]]; then
    echo "NODE_FRESH: yes (boot ${fresh_boot:0:8} of the latest revert, no agent run since)"
  else
    echo "NODE_FRESH: no (${stale_reason}); record_green.sh will refuse this run's GREEN — use --revert-first" >&2
  fi

  # HQ 2026-11-17 batch-8 ruling 4: the node's clock agrees with the laptop's (the master's is checked at lock time).
  "${LOCAL_REPO}/.codex_state/tools/clock_check.py" "$NODE_HOST" || die "the node's clock is off the laptop's; not running the agent"
  HARNESS_RX_START="$(node_nic1_rx)"
  echo "==> Running puppet agent (run 1 may change; run 2 must exit 0 with no events; timeout ${AGENT_TIMEOUT_SECONDS}s each)"
  local out1 out2 rc1 rc2 reason run1_events

  out1="$(run_agent)" && rc1=0 || rc1=$?
  echo "$out1"
  agent_run_summary
  [[ $rc1 -eq 0 || $rc1 -eq 2 ]] || die_agent_rc 1 "$rc1"
  # Catalog events only: pluginsync writes /File[/opt/puppetlabs/puppet/cache/...] outside Stage[main].
  run1_events="$(grep -E 'Notice: /Stage\[main\]/' <<<"$out1" | grep -cE "$RUN2_FORBIDDEN_RE" || true)"
  run1_plugins="$(grep -cE 'Notice: /File\[/opt/puppetlabs/puppet/cache/' <<<"$out1" || true)"
  HARNESS_RUN1_EVENTS="$run1_events"
  echo "RUN1_EVENTS: ${run1_events} catalog, ${run1_plugins} pluginsync (rc ${rc1}; node $([[ $revert_first -eq 1 ]] && echo "reverted first" || echo "NOT reverted first"))"
  if [[ $revert_first -eq 1 && $run1_events -eq 0 ]]; then
    echo "WARNING: run 1 on a freshly reverted node applied nothing; the class may be a no-op here." >&2
  fi

  local run1_end
  run1_end="$(node_now)"
  [[ "$run1_end" =~ ^[0-9]+$ ]] || die "Could not read the node's clock after run 1 (the between-runs gate fails closed)."

  out2="$(run_agent)" && rc2=0 || rc2=$?
  echo "$out2"
  agent_run_summary
  [[ $rc2 -eq 0 || $rc2 -eq 2 ]] || die_agent_rc 2 "$rc2"

  collect_expected_run2 "${classes[@]}"
  local changed2 verdict gate_rc=0
  changed2="$(report_changed)" || die "Run 2's report could not be read from the node (the gate fails closed)."
  verdict="$(apply_gate "$rc1" "$out1" "$rc2" "${out2}"$'\n'"${changed2}")" || gate_rc=$?
  [[ $gate_rc -le 1 ]] || die "The gate could not judge the runs: ${verdict}"
  EXPECTED_RUN2_HITS="$(python3 -c 'import json, sys; print(json.load(sys.stdin)["expected_hits"])' <<<"$verdict")"
  if [[ ${#EXPECTED_RUN2_REFS[@]} -gt 0 ]]; then
    echo "RUN2_EXPECTED_EVENTS: ${EXPECTED_RUN2_HITS} from ${EXPECTED_RUN2_REFS[*]} [$(describe_expected_run2)] (plan expected_run2_events)"
  fi
  if [[ $gate_rc -ne 0 ]]; then
    python3 -c '
import json, sys
v = json.load(sys.stdin)
if v["errors"]:
    print("Errors logged:\n" + "\n".join(v["errors"]), file=sys.stderr)
if v["unexpected"]:
    print("Run 2 events:\n" + "\n".join(v["unexpected"]), file=sys.stderr)' <<<"$verdict"
    reason="$(python3 -c 'import json, sys; print(json.load(sys.stdin)["reason"])' <<<"$verdict")"
    die "${reason^}."
  fi

  # Between-runs gate (HQ after batch 20, item 6): an agent run the harness did not make (the agent daemon a class
  # starts) between run 1 and the end of run 2 must have changed nothing, or it would hide what run 2 should show.
  # A daemon run's resource events are logged as "(/Stage[main]/...) <event>"; a failed run logs an error.
  local run2_end daemon_log daemon_runs daemon_bad
  run2_end="$(node_now)"
  [[ "$run2_end" =~ ^[0-9]+$ ]] || die "Could not read the node's clock after run 2 (the between-runs gate fails closed)."
  daemon_log="$(daemon_log_between "$run1_end" "$run2_end")" ||
    die "Could not read the agent daemon's log on the node (the between-runs gate fails closed)."
  daemon_runs="$(grep -c 'Applied catalog in' <<<"$daemon_log" || true)"
  daemon_bad="$(grep -E '^\(/Stage\[main\]/|^Could not|[Ee]rror' <<<"$daemon_log" || true)"
  if [[ -n "$daemon_bad" ]]; then
    printf 'The agent daemon between run 1 and run 2:\n%s\n' "$daemon_bad" >&2
    die "An agent run between run 1 and run 2 (the agent daemon) changed something or failed: not idempotent."
  fi
  if [[ "$daemon_runs" -gt 0 ]]; then
    echo "BETWEEN_RUNS: ${daemon_runs} agent daemon run(s) between run 1 and the end of run 2, with no resource event"
  fi

  if [[ -n "${FIXTURE_NAME:-}" ]]; then
    echo "COVERAGE: skipped for engine fixture '${FIXTURE_NAME}'"
  else
    coverage_check "${classes[@]}"
  fi

  if [[ ${EXPECTED_RUN2_HITS:-0} -gt 0 ]]; then
    echo "GREEN: run 2 events limited to the plan's expected_run2_events (${EXPECTED_RUN2_REFS[*]}) (gate v2)."
  else
    echo "GREEN: run 2 exited 0 with no change events (gate v2)."
  fi
  if [[ -n "${P8_PARAMS_VARIANT:-}" ]]; then
    echo "GREEN_STAMP: none (a Phase 3 variant run with params variant ${P8_PARAMS_VARIANT}; never a Phase 1 record)"
  elif [[ -z "${FIXTURE_NAME:-}" ]]; then
    # Step 3.2: stamp the code that went GREEN; record_green.sh refuses anything else.
    local -a stamp_opts=(--run1-events "$run1_events" --coverage "${COVERAGE_REPORT:-}")
    [[ $revert_first -eq 1 ]] && stamp_opts+=(--revert-first)
    if [[ -n "$fresh_boot" ]]; then stamp_opts+=(--fresh-boot "$fresh_boot"); else stamp_opts+=(--stale-reason "$stale_reason"); fi
    stamp_opts+=(--node "$NODE_KIND")
    python3 "$RECORDS_TOOL" stamp "${stamp_opts[@]}" -- "${classes[@]}" || die "Could not write the GREEN stamp."
  fi
}

main "$@"
