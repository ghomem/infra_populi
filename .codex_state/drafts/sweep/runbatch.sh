#!/usr/bin/env bash
# runbatch.sh <class>...: copy each drafted set into the repo and run it; one outcome line per class
S=/tmp/claude-1000/-home-salatiel-work-infra-populi/b798a4a6-79e3-4867-b8fb-db365dc52fef/scratchpad/sweep
cd ~/work/infra_populi || exit 1
for c in "$@"; do
  cp "$S/$c.yml" ".codex_state/checks/$c.yml"
  python3 .codex_state/tools/phase3.py run "$c" > "$S/run_$c.log" 2>&1
  echo "$c rc=$? $(grep -E '^PHASE3' "$S/run_$c.log" | cut -d' ' -f2) $(grep -E '^==> VARIANT .*: [A-Z_]+$' "$S/run_$c.log" | sed 's/==> VARIANT //' | tr '\n' ' ')"
done
