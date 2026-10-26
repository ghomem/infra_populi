#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TRACKED TOOLING. Idempotent builder of lab-master fixture state on puppet8master
# (ruling 6 and the 2026-10-26 ruling-4 amendment). Every section checks before it
# changes anything and reports CHANGED or OK, so a second run reports OK only.
#
# Sections:
#   lint   puppet-lint at a pinned version in the agent ruby (/opt/puppetlabs/puppet),
#          used by pregate over ssh. Never in puppetserver's JRuby, never on the laptop
#          (a production Puppet 5 node).
#   (step 4.1 adds: extra_files mount, throwaway p8test PKI, Hiera fixture keys)
#
# Never restores, powers off or resets the master; never touches passwd_common.
# After a section reports CHANGED for the first time, HQ takes a new master snapshot.
# ---------------------------------------------------------------------------

set -euo pipefail

readonly MASTER_HOST="puppet8master"
readonly PUPPET_LINT_VERSION="4.3.0"
readonly AGENT_GEM="/opt/puppetlabs/puppet/bin/gem"

usage() { echo "Usage: $0 [lint|all]" >&2; exit 2; }

section_lint() {
  ssh -T "$MASTER_HOST" "sudo -n bash -s -- '$AGENT_GEM' '$PUPPET_LINT_VERSION'" <<'REMOTE'
set -euo pipefail
gem="$1" version="$2"
installed="$("$gem" list --exact puppet-lint --local 2>/dev/null | sed -n 's/^puppet-lint (\(.*\))$/\1/p')"
if [[ ",${installed// /}," == *",${version},"* ]]; then
  echo "OK lint: puppet-lint ${version} already installed (installed: ${installed})"
else
  "$gem" install puppet-lint --version "$version" --no-document >/dev/null
  echo "CHANGED lint: installed puppet-lint ${version} (previously: ${installed:-none})"
fi
"$(dirname "$gem")/puppet-lint" --version
REMOTE
}

case "${1:-all}" in
  lint | all) section_lint ;;
  *) usage ;;
esac
