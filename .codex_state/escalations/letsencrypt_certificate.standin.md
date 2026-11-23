# letsencrypt_certificate — stand-in lift "a lab ACME endpoint" (RULED: stays a stand-in for Salatiel's acceptance, HQ 2026-11-23)

HQ after batch 20, item 6 asks for the stand-in lifts the lab can reach with small additions. This one is not small,
and its design has a choice in it, so it is escalated and the run continues.

## What the class does
`letsencrypt_certificate` declares `letsencrypt::certonly` with certbot's DNS-01 plugin for DigitalOcean or Hetzner
(`--dns-digitalocean` / `--authenticator dns-hetzner`, credentials from `dns-creds.ini`). certbot proves control of
the domain by creating a TXT record through the provider's HTTPS API, then the ACME server checks that record in DNS.
The stand-in (`letsencrypt_cert_standin`) supplies an existing self-signed certificate, so certonly's guard skips the
issuance.

## What a lab ACME endpoint needs
1. An ACME server: Pebble (Let's Encrypt's test server) on the ubuntu2 peer, its URL set as the letsencrypt module's
   server in the lab Hiera, its CA trusted by certbot on the node.
2. The provider's API: the lab cannot hold a real DigitalOcean or Hetzner token, so a stand-in for the API is
   unavoidable: a small HTTPS service on the peer answering the plugin's record calls, the provider's host name
   pointed at the peer on the node, its certificate from a lab CA the node trusts.
3. DNS for the test domain, if the TXT record is to be validated for real.

## Options
- **A (recommended):** Pebble + pebble-challtestsrv (Pebble's test DNS server) + the API stand-in, which writes the TXT
  records into challtestsrv; Pebble validates DNS-01 against challtestsrv. certbot obtains a real certificate from a
  real ACME exchange with real DNS validation; only the provider's API is substituted.
- **B:** Pebble with `PEBBLE_VA_ALWAYS_VALID=1` (no validation) + an API stand-in that only accepts the calls. Fewer
  parts; issuance and renewal are tested, DNS validation is not.
- **C:** keep the stand-in, for Salatiel's acceptance in the approval report.

Either A or B adds a lab-side service, a Hiera key and a node-side trust and host entry (fixtures), and touches no class
file. The provider-API stand-in remains a stand-in in A and B: the report would say so.
