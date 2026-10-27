#!/usr/bin/env bash
# Records path (ruling 3 / step 3.2): the ONLY way a GREEN class is recorded. It refuses unless the
# class's current code is exactly what went GREEN (harness stamp), the manifest carries a migration
# header naming its module dependencies, the worktree holds nothing but the class's files and the
# tracker, and the standing composite compiles still match their expectations. Then it writes the
# tracker marker, commits, regenerates the order file, commits that, and pushes.
#
# Usage: record_green.sh <class> [--defect "<short>"] [--fix "<what>"] [--no-push]
#   --defect   tracker marker `[from: <baseline>; upstream defect fixed: <short>]` (HQ ck1 ruling 3);
#              only for a fix HQ has ruled on.
#   --fix      a records fix after a reviewer FAIL on an already-recorded class: comments/header and the
#              tracker only (code must equal HEAD); commit `P8: record <class>: <what>`.
# Exit: 0 recorded; 1 refused (nothing committed); 4 composite DIFF (nothing committed).
# P8_COMPOSITE_CMD overrides the composite check (tests).
set -euo pipefail

TOOLS="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO="$(git -C "$TOOLS" rev-parse --show-toplevel)"
RECORDS=(python3 "$TOOLS/records.py")
COMPOSITE_CMD="${P8_COMPOSITE_CMD:-python3 $TOOLS/composite_compile.py}"
TRACKER=".codex_state/migrated_classes.txt"
ORDER=".codex_state/migration_order.md"
NECESSARY=".codex_state/necessary_modules.txt"

refuse() { echo "RECORD REFUSED: $*" >&2; exit 1; }

[[ $# -ge 1 ]] || { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }
CLS="${1#puppet_infrastructure::}"
shift
[[ "$CLS" =~ ^[a-z][a-z0-9_]*$ ]] || refuse "invalid class name '${CLS}'"
DEFECT="" FIX="" PUSH=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --defect) DEFECT="${2:-}"; [[ -n "$DEFECT" ]] || refuse "--defect needs a short description"; shift 2 ;;
    --fix) FIX="${2:-}"; [[ -n "$FIX" ]] || refuse "--fix needs a short description"; shift 2 ;;
    --no-push) PUSH=0; shift ;;
    *) refuse "unknown argument '$1'" ;;
  esac
done
cd "$REPO"
[[ -f "manifests/${CLS}.pp" ]] || refuse "no manifests/${CLS}.pp"

START_HEAD="$(git rev-parse HEAD)"
# 1. git position: on main, level with origin/main, no merge/rebase in progress.
[[ "$(git rev-parse --abbrev-ref HEAD)" == main ]] || refuse "not on main"
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/main)" ]] || refuse "HEAD != origin/main (push or pull first)"

# 2. the worktree holds only this class's files and the tracker.
mapfile -t allowed < <("${RECORDS[@]}" class-files "$CLS")
allowed+=("$TRACKER")
mapfile -t dirty < <(git status --porcelain --untracked-files=all | cut -c4-)
for path in "${dirty[@]}"; do
  [[ -n "$path" ]] || continue
  ok=0
  for a in "${allowed[@]}"; do [[ "$path" == "$a" ]] && ok=1 && break; done
  [[ $ok -eq 1 ]] || refuse "worktree holds '${path}', which is not a file of ${CLS} (stash or commit it separately)"
done

# 3. GREEN stamp matches the current code; 4. header present.
"${RECORDS[@]}" verify-stamp "$CLS" || refuse "no valid GREEN stamp"
"${RECORDS[@]}" header-check "$CLS" || refuse "migration header missing or incomplete"
if [[ -n "$FIX" ]]; then
  python3 .codex_state/gen_migration_order.py --classify "$CLS" >/dev/null
  grep -qE "^(${CLS} Done|Done ${CLS})( |$)" "$TRACKER" || refuse "--fix is for an already-recorded class; ${CLS} is not Done"
  "${RECORDS[@]}" code-unchanged "$CLS" || refuse "--fix may not change code"
fi

# 5. standing composite compiles (step 2.2) on the tree being recorded.
echo "==> Standing composite compiles"
if ! $COMPOSITE_CMD; then
  echo "RECORD REFUSED: a composite compile no longer matches compile/composites.txt — a regression to" \
       "investigate, or a fix to record in composites.txt in its own commit first" >&2
  exit 4
fi

# 6. tracker marker, then the class commit.
if [[ -n "$DEFECT" ]]; then
  "${RECORDS[@]}" tracker-set "$CLS" --defect "$DEFECT"
else
  "${RECORDS[@]}" tracker-set "$CLS"
fi
for path in "${allowed[@]}"; do
  if [[ -n "$(git status --porcelain -- "$path")" ]]; then git add -- "$path"; fi
done
git diff --cached --quiet && refuse "nothing to commit for ${CLS}"
SUBJECT="P8: migrate puppet_infrastructure::${CLS}"
[[ -z "$FIX" ]] || SUBJECT="P8: record ${CLS}: ${FIX}"
git commit -q -m "$SUBJECT"
echo "RECORDED $(git rev-parse --short HEAD) ${SUBJECT}"

# 7. necessary_modules.txt (local-only): Forge modules the header names.
if [[ -f "$NECESSARY" ]]; then
  while read -r forge; do
    [[ -n "$forge" ]] || continue
    grep -qxF "$forge" "$NECESSARY" || { echo "$forge" >>"$NECESSARY"; echo "NECESSARY_MODULES += ${forge}"; }
  done < <("${RECORDS[@]}" header-modules "$CLS" || echo "")
fi

# 8. regenerate the order file and commit it if it changed.
python3 .codex_state/gen_migration_order.py
if [[ -n "$(git status --porcelain -- "$ORDER")" ]]; then
  git add -- "$ORDER"
  git commit -q -m "P8: regenerate migration order after ${CLS}"
  echo "RECORDED $(git rev-parse --short HEAD) P8: regenerate migration order after ${CLS}"
fi

# 9. push.
if [[ $PUSH -eq 1 ]]; then
  git push -q
  echo "PUSHED $(git rev-parse --short HEAD)"
fi

# 10. metrics event (step 3.4): the commits this record made.
mapfile -t made < <(git log --format=%h "${START_HEAD}..HEAD")
python3 "$TOOLS/metrics.py" event "$CLS" record \
  "$(python3 -c 'import json, sys; print(json.dumps({"commits": sys.argv[1:]}))' "${made[@]}")" || true
