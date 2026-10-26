#!/usr/bin/env bash
# Runs ON puppet8master (step 2.2): compile puppet8node's catalog with the facts shipped alongside.
# $1 = work dir holding facts/puppet8node.yaml and filter.rb; remaining args = target classes.
set -u
d="$1"; shift
# Redirects are written by the ssh user into its own temp dir on purpose.
# shellcheck disable=SC2024
sudo -n /opt/puppetlabs/bin/puppet catalog compile puppet8node \
  --facts_terminus yaml --yamldir "$d" --render-as json >"$d/out" 2>"$d/err"
rc=$?
# Compiler messages only (Error/Warning lines and their indented continuation lines).
sed 's/\x1b\[[0-9;]*m//g' "$d/err" | awk '/^(Error|Warning):/ {keep=1; print; next} keep && /^[[:space:]]/ {print; next} {keep=0}' | cut -c1-400
if [ "$rc" -ne 0 ]; then echo "COMPILE_FAILED: puppet catalog compile exited $rc"; exit 5; fi
/opt/puppetlabs/puppet/bin/ruby "$d/filter.rb" "$@" <"$d/out"
