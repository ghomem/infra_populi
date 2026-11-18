# shellcheck shell=bash
# probe_helpers.sh — helper functions for Phase 3 probes (HQ batch-12 ruling 6). phase3.py prepends this file to
# every script it runs on a node or the peer, so a check's probe, effect, action or mismatch may call them.
#
# Each helper prints one stable line (or one line per item) and exits 0, so a probe's exit code is never a helper's
# accident. Read-only helpers only observe. Mutating helpers (p8_hold) belong in a check's action; phase3.py refuses
# them in a probe, an effect or a mismatch.
#
# Read-only: p8_count, p8_listening, p8_tcp, p8_http, p8_service, p8_digest, p8_rc, p8_tls, p8_established
# Mutating:  p8_hold

# p8_count PATTERN [FILE...] — the number of lines matching the extended regex (stdin when no file is given);
# 0 when nothing matches or a file is missing.
p8_count() {
  local pattern="$1"; shift
  grep -E -c -- "$pattern" "$@" 2>/dev/null | awk -F: '{ s += $NF } END { print s + 0 }'
}

# p8_listening PORT [tcp|udp] — the local addresses listening on the port, sorted, one per line (nothing when none).
p8_listening() {
  local proto="${2:-tcp}"
  ss -H -ln"${proto:0:1}" "sport = :$1" 2>/dev/null | awk '{ print $4 }' | sort -u
}

# p8_tcp HOST PORT [TIMEOUT] [SOURCE] — `open` when a TCP connection is accepted within TIMEOUT seconds (2), else
# `closed`; SOURCE binds the local address.
p8_tcp() {
  local src=()
  [[ -n "${4:-}" ]] && src=(-s "$4")
  if nc -z -w "${3:-2}" "${src[@]}" "$1" "$2" >/dev/null 2>&1; then echo open; else echo closed; fi
}

# p8_http URL [CURL_ARGS...] — the HTTP status code (000 when nothing answers within 5 s); extra arguments go to
# curl (e.g. --resolve, -H 'Host: x', -k, --cacert).
p8_http() {
  local url="$1"; shift
  local code
  code=$(curl -s -o /dev/null --max-time 5 -w '%{http_code}' "$@" "$url" 2>/dev/null)
  echo "${code:-000}"
}

# p8_service UNIT — `<active state> <enabled state>`, e.g. `active enabled`; `absent` for an unknown enabled state.
p8_service() {
  local active enabled
  active=$(systemctl is-active "$1" 2>/dev/null)
  enabled=$(systemctl is-enabled "$1" 2>/dev/null)
  echo "${active:-unknown} ${enabled:-absent}"
}

# p8_digest FILE... — `<path> <owner>:<group> <mode> <sha256>` per file, or `<path> absent`.
p8_digest() {
  local f
  for f in "$@"; do
    if [[ -f "$f" ]]; then
      echo "$f $(stat -c '%U:%G %a' "$f") $(sha256sum "$f" | cut -d' ' -f1)"
    else
      echo "$f absent"
    fi
  done
}

# p8_rc COMMAND [ARGS...] — runs the command, prints the first line of its standard output, then `rc=<exit code>`
# (for Nagios-style checks, whose status is the first line and the exit code).
p8_rc() {
  local out rc
  out=$("$@" 2>/dev/null)
  rc=$?
  printf '%s\n' "${out%%$'\n'*}"
  echo "rc=$rc"
}

# p8_tls HOST PORT SERVERNAME VERSION — `accepted` when a handshake with that protocol version (tls1_2, tls1_3)
# completes, else `refused`. Reads the handshake's `New, <version>` line: openssl prints a `Protocol :` line even for
# a refused TLS 1.2 attempt.
p8_tls() {
  if openssl s_client -connect "$1:$2" -servername "$3" "-$4" </dev/null 2>/dev/null | grep -q '^New, TLSv1'; then
    echo accepted
  else
    echo refused
  fi
}

# p8_established HOST PORT — the number of this machine's established TCP connections to HOST:PORT.
p8_established() {
  ss -tnH state established "( dport = :$2 and dst $1 )" 2>/dev/null | wc -l
}

# p8_hold HOST PORT SECONDS [SOURCE] — MUTATING: opens a TCP connection to HOST:PORT and holds it for SECONDS in the
# background (detached, so it outlives the probe's session), then ends it; returns at once. netcat alone would hold
# the connection forever after its input ends, so `timeout` ends it.
p8_hold() {
  local src=()
  [[ -n "${4:-}" ]] && src=(-s "$4")
  setsid -f timeout "$3" nc "${src[@]}" "$1" "$2" </dev/null >/dev/null 2>&1
}
