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
#   extra_files  fileserver mount [extra_files] -> /etc/puppetlabs/code/p8test_extra_files (puppet:///extra_files/...
#          used by ssl_*, mysql_server, openvpn_server); restarts puppetserver only when the mount changed.
#   pki    throwaway p8test PKI inside that mount: a self-signed "p8test throwaway CA" and one server cert
#          (CN p8test.invalid; SANs *.p8test.invalid, star.example.com) laid out under every name the
#          manifests source (ssl/<prefix>.*, ssl/db/*, openvpn/keys/*) for prefixes p8test and
#          star.example.com (the lab Hiera's example hashman::sslprefix). The CA key is discarded.
#   hiera  lab fixture keys the manifests look up and the lab Hiera lacks, in data/p8test_fixtures.yaml, as
#          a hierarchy level AFTER Common (it can never override an existing key).
# Every value is obviously fake (p8test, .invalid, example.com); nothing is production-derived.
#
# Never restores, powers off or resets the master; never touches passwd_common.
# After a section reports CHANGED for the first time, HQ takes a new master snapshot.
# ---------------------------------------------------------------------------

set -euo pipefail

readonly MASTER_HOST="puppet8master"
readonly PUPPET_LINT_VERSION="4.3.0"
readonly AGENT_GEM="/opt/puppetlabs/puppet/bin/gem"

readonly EXTRA_DIR="/etc/puppetlabs/code/p8test_extra_files"
readonly ENV_DIR="/etc/puppetlabs/code/environments/production"

usage() { echo "Usage: $0 [lint|extra_files|pki|hiera|all]" >&2; exit 2; }

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

section_extra_files() {
  ssh -T "$MASTER_HOST" "sudo -n bash -s -- '$EXTRA_DIR'" <<'REMOTE'
set -euo pipefail
dir="$1" conf=/etc/puppetlabs/puppet/fileserver.conf changed=0
if [[ ! -d "$dir" ]]; then
  install -d -o root -g puppet -m 0750 "$dir"; changed=1
fi
stanza="[extra_files]
  path ${dir}"
if ! grep -qx '\[extra_files\]' "$conf" 2>/dev/null; then
  [[ -f "$conf" ]] && cp -p "$conf" "${conf}.bak.$(date +%Y%m%dT%H%M%S)"
  printf '# Managed by infra_populi master_fixtures.sh (section extra_files): lab fixture mount\n%s\n' "$stanza" >>"$conf"
  changed=1
elif ! grep -A1 -x '\[extra_files\]' "$conf" | grep -qx "  path ${dir}"; then
  echo "ERROR extra_files: ${conf} has an [extra_files] mount with another path; not touching it" >&2; exit 1
fi
if [[ $changed -eq 1 ]]; then
  systemctl restart puppetserver
  for _ in $(seq 1 90); do
    [[ "$(curl -sk https://localhost:8140/status/v1/simple 2>/dev/null)" == running ]] && break; sleep 2
  done
  echo "CHANGED extra_files: mount [extra_files] -> ${dir}; puppetserver $(curl -sk https://localhost:8140/status/v1/simple)"
else
  echo "OK extra_files: mount [extra_files] -> ${dir} present"
fi
REMOTE
}

section_pki() {
  ssh -T "$MASTER_HOST" "sudo -n bash -s -- '$EXTRA_DIR'" <<'REMOTE'
set -euo pipefail
dir="$1" marker="$1/.p8test_pki_v1"
[[ -d "$dir" ]] || { echo "ERROR pki: ${dir} missing — run the extra_files section first" >&2; exit 1; }
if [[ -f "$marker" ]]; then
  echo "OK pki: throwaway p8test PKI present ($(cat "$marker"))"; exit 0
fi
w="$(mktemp -d /tmp/p8test_pki.XXXXXX)"; trap 'rm -rf "$w"' EXIT
cd "$w"
subj_o="/O=p8test lab fixture (THROWAWAY, not a real CA)"
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "${subj_o}/CN=p8test throwaway CA" 2>/dev/null
openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj "${subj_o}/CN=p8test.invalid" 2>/dev/null
printf 'subjectAltName=DNS:p8test.invalid,DNS:*.p8test.invalid,DNS:star.example.com\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' >ext.cnf
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 3650 -extfile ext.cnf 2>/dev/null
openssl dhparam -out dh2048.pem 2048 2>/dev/null
put() { install -D -o root -g puppet -m "$3" "$1" "${dir}/$2"; }
for p in p8test star.example.com; do
  put server.crt "ssl/${p}.crt" 0644; put server.crt "ssl/${p}.pem" 0644
  put server.key "ssl/${p}.key" 0640; put server.key "ssl/${p}-key.pem" 0640
  put ca.crt "ssl/${p}.intermediate.crt" 0644; put ca.crt "ssl/${p}-chain.pem" 0644
done
put ca.crt ssl/db/ca.pem 0644; put server.crt ssl/db/server-cert.pem 0644; put server.key ssl/db/server-key.pem 0640
put ca.crt openvpn/keys/ca.crt 0644; put dh2048.pem openvpn/keys/dh2048.pem 0644
put server.crt openvpn/keys/server.crt 0644; put server.key openvpn/keys/server.key 0640
find "$dir" -type d -exec chown root:puppet {} + -exec chmod 0750 {} +
openssl verify -CAfile ca.crt server.crt >/dev/null
fp="$(openssl x509 -noout -fingerprint -sha256 -in server.crt | cut -d= -f2)"
echo "created $(date -u +%Y-%m-%dT%H:%M:%SZ); server cert sha256 ${fp}; CA key discarded" >"$marker"
chmod 0644 "$marker"
echo "CHANGED pki: $(find "$dir" -type f ! -name '.*' | wc -l) files; $(openssl x509 -noout -subject -enddate -in server.crt | tr '\n' ' ')"
REMOTE
}

section_hiera() {
  ssh -T "$MASTER_HOST" "sudo -n bash -s -- '$ENV_DIR'" <<'REMOTE'
set -euo pipefail
env="$1" data="$1/data/p8test_fixtures.yaml" hiera="$1/hiera.yaml" changed=""
want="$(cat <<'YAML'
# Managed by infra_populi .codex_state/tools/master_fixtures.sh (section hiera). LAB FIXTURE keys only:
# obviously fake values, nothing production-derived; a hierarchy level AFTER Common.
sysmon::basedir: '/var/tmp/p8test-sysmon/'
sysmon::address: 'sysmon.p8test.invalid'
sysmon::backdir: "%{lookup('filesystem::backdir')}/sysmon"
sysmon::backdays: '10'
puppet8node::postfix_smtp_node::relayuser: 'p8test-relay'
puppet8node::postfix_smtp_node::relaypass: 'p8test-not-a-secret'
YAML
)"
if [[ "$(cat "$data" 2>/dev/null)" != "$want" ]]; then
  printf '%s\n' "$want" | install -o root -g puppet -m 0640 /dev/stdin "$data"; changed="data"
fi
if ! grep -q 'p8test_fixtures.yaml' "$hiera"; then
  cp -p "$hiera" "${hiera}.bak.$(date +%Y%m%dT%H%M%S)"
  /opt/puppetlabs/puppet/bin/ruby -ryaml -e '
    h = YAML.load_file(ARGV[0])
    h["hierarchy"] << { "name" => "P8 lab fixtures (master_fixtures.sh; after Common)", "path" => "p8test_fixtures.yaml" }
    File.write(ARGV[0], h.to_yaml)' "$hiera"
  changed="${changed:+$changed+}hierarchy"
fi
/opt/puppetlabs/puppet/bin/ruby -ryaml -e 'YAML.load_file(ARGV[0]); YAML.load_file(ARGV[1])' "$hiera" "$data"
if [[ -n "$changed" ]]; then echo "CHANGED hiera: ${changed} ($(grep -c '::' "$data") keys)"; else echo "OK hiera: fixture keys and hierarchy level present"; fi
REMOTE
}

case "${1:-all}" in
  lint) section_lint ;;
  extra_files) section_extra_files ;;
  pki) section_pki ;;
  hiera) section_hiera ;;
  all) section_lint; section_extra_files; section_pki; section_hiera ;;
  *) usage ;;
esac
