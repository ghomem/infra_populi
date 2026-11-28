# letsencrypt_base — behaviour finding: the Hetzner DNS plugin cannot be installed on Ubuntu 24.04 (OPEN 2026-11-28; more than one reasonable design)

Found by the set's `hetzner` variant (HQ 2026-11-27 item 1: a variant production uses; provider `hetzner-cloud`,
renew on the 1st and 15th), run twice: `.codex_state/checks/public/harness/letsencrypt_base/20261127T232211Z.json` and
`20261127T235617Z.json`, both APPLY_FAILED (agent run 1 exit 6; certbot's configuration, renewal cron and hooks are
skipped "because of failed dependencies").

## What happens

For `hetzner` and `hetzner-cloud` the class installs the Certbot plugin with Puppet's `pip` package provider into the
system Python (manifests/letsencrypt_base.pp, baseline: `$package_name = 'certbot-dns-hetzner'`,
`$package_provider = 'pip'`, `$ensure_value = $package_version` with 3.0.0 for hetzner-cloud and 2.0.0 for hetzner,
after `python3-pip` from apt). Ubuntu 24.04's Python 3.12 is marked externally managed (PEP 668), so pip refuses.
Reproduced on a fresh node (P8NODE_BASELINE_GREEN_v6) with the provider's command:

```
$ pip3 install -q certbot-dns-hetzner==3.0.0
error: externally-managed-environment
× This environment is externally managed
...
note: ... You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.
rc=1
```

Ubuntu 24.04 has no package for the plugin (`apt-cache search certbot-dns` lists cloudflare, digitalocean, dnsimple,
gandi, gehirn, google, infomaniak, linode, ovh, rfc2136, ... and no hetzner); certbot itself is 2.9.0 from universe.
The `digitalocean` provider (apt: python3-certbot-dns-digitalocean) is unaffected: the set's base run passes.

## Production

The hetzner variant is one production uses (HQ item 1 classed it so from fleet_variant_usage.md). Today's production
nodes run an Ubuntu release whose Python is not externally managed, so the class works there; on 24.04 every
hetzner node loses certificate issuance and renewal: the plugin is missing and the letsencrypt configuration that
depends on it is skipped on every run.

## Options (more than one reasonable design, so escalated: HQ batch-12 ruling 5)

- **A. pip with `--break-system-packages`** (`install_options => ['--break-system-packages']` on the package): the
  smallest change; installs into the system Python, which Debian warns can break apt-managed Python packages (the
  plugin pulls in requests and dns-lexicon versions apt also ships).
- **B. A virtual environment** for certbot and the plugin (e.g. /opt/certbot-venv), with the letsencrypt module pointed
  at that certbot (`letsencrypt::certbot_path` or equivalent): isolated and the documented route, but a larger change
  touching how puppet/letsencrypt runs certbot on every provider.
- **C. Snap**: certbot from the snap with a Hetzner plugin snap, if one is maintained; changes the certbot source for
  every provider.
- **D. Another DNS-01 route for Hetzner** (e.g. RFC 2136, which apt packages, if Hetzner's DNS offers it): changes the
  interface (the API token becomes TSIG keys).

Recommendation: B. It keeps the system Python untouched and follows the distribution's guidance. Its scope (how the
module invokes certbot) needs a ruling, and the cutover list should note that A is the only drop-in option.

Status of the set: the `hetzner` variant stays as written (its checks state the purpose); the class's behaviour state
is a finding until a ruling.
