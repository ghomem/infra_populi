# openvpn_domain: authoring notes (the comments of .codex_state/checks/openvpn_domain.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::openvpn_domain (class; node ubuntu; MOCK-APPLY: node fixture
# p8test_domain_dns puts the lab DC's DNS first in the node's resolv.conf). The class installs Samba/winbind/Kerberos,
# writes smb.conf (security = domain), krb5.conf, nsswitch.conf, pam_winbind.conf and /etc/pam.d/openvpn, and joins the
# node to the domain with join-domain.sh (net join) unless the join user already resolves. Fixture (params, never
# committed): join_user p8testuser / fake password, domain_hostname p8lab-dc, NetBIOS P8TEST, tld example, separator +,
# groups [p8testgroup]. The peer is p8lab-dc, the lab's Samba AD DC (realm P8TEST.EXAMPLE): reverted with the node so
# the join starts from a domain without this machine, and asked whether it now holds the node's machine account.
# Probes read the node's own Samba/winbind state and files; the DC is reached only by the tools the class configures.
# 2026-11-21 (backfill batch 8): purpose and outcomes (HQ rulings 2 and C1), and the login itself as behaviour: the DC
# gets two fixture users (p8testvpnin in p8testgroup, p8testvpnout outside it) and pamtester runs the login service's
# auth and account stacks on the node. /etc/pam.d/openvpn (password lines only, line 7 without a module) is used by no
# baseline service: openvpn_server's plugin names login (its set checks the plugin line); it is checked as installed.
# Prototyped 2026-11-21 on the ubuntu node with the dc peer.
# Correction round 1, 2026-11-21 (review 20261121T042709Z, purpose): the Kerberos configuration as an outcome, measured
# with kinit against the DC (the default realm's case follows the domain_tld parameter: batch 8 report, for HQ).
# Correction round 2, 2026-11-21 (review 20261121T050106Z, purpose): host resolution through WINS (nsswitch's hosts
# line), measured with the DC up (the runner powers the peer off after a run, so a lookup after the run times out).
# Correction round 3, 2026-11-21 (HQ after batch 18, item 1; review 20261121T051116Z): logins by the bare name
# (winbind use default domain). Kerberos (item 2, a finding with one clear fix): the check now expects the purpose,
# kinit without naming a realm working with the lowercase-tld fixture; it fails on the baseline template (before
# evidence for local change #17, the realm upper-cased when built).
  # 2026-11-18 authoring correction (run 1, 20261118T004132Z): the probe split `id -nG` on spaces, which cuts the group
  # name "domain users" in two; the user resolved with both groups (run 1 printed p8testgroup only). The probe now
  # matches the whole names in id's output; the behaviour is unchanged.
```
