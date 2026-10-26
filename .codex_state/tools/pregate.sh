#!/usr/bin/env bash
# Pre-VM gate entry point (ruling 4). Logic and documentation: pregate.py next to this file.
# Usage: pregate.sh [--json] <class> | pregate.sh --staged
set -euo pipefail
exec python3 "$(dirname "$(readlink -f "$0")")/pregate.py" "$@"
