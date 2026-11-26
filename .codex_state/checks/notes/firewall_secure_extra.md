# firewall_secure_extra: authoring notes (the comments of .codex_state/checks/firewall_secure_extra.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::firewall_secure_extra (class; node ubuntu; required_base filesystem_base;
# required_external firewall). Fixture (params, never committed; set 2026-11-18 to exercise the class's own purpose,
# the extras over firewall_secure): acl [the laptop's host-only address]; anti_ddos true; service_list [[8888, tcp]];
# ddos_limit 3 (connections per source), ddos_limit_per_time_unit 2 with unit sec (new connections); ip_filter true
# with ip_whitelist [the peer's host-only address + 100]; ip_blacklist [the peer's host-only address + 150];
# country_whitelist '' and internal_forward false; ssh_port 22. The peer (ubuntu2) reaches the node from three
# addresses it adds to its own NIC: its primary one (on no list), +100 (whitelisted for the service) and +150
# (blacklisted). Node probes name no other host; peer probes name only the class node's host-only address and compute
# their own addresses.
# 2026-11-23 (the sweep, HQ 2026-11-23 ruling 1): anti_ddos without ip_filter, and no anti_ddos with strict mode, are
# checks in the variant runs `ddosonly` and `plain`; rule 002, fragments, geoip and internal forwarding name what is
# missing, with their evidence.
  # Correction round 4 (2026-11-19, HQ batch-12 ruling 2; review 20261118T225957Z), the last for this class: the
  # held-SSH check records the SSH rules' counters before and after, so a run that holds fewer than 8 shows which
  # rule took the connection (three hand repetitions on the applied node, 2026-11-19: 8 held each time, only rule 112
  # dropped, 16 packets a round: the 9th and 10th SYNs and their retransmissions; 114 and 117 dropped none); the
  # expectation stays 8, no legitimate interaction having shown; the held connections use the probe helpers.
  # Correction round 3 (2026-11-18, HQ batch-11 rulings 1 and 3; review 20261118T182854Z):
  # - local change #5 (rules/local_changes.md): the blacklist drop is titled 00 and covers all protocols, so the
  #   blacklist check expects ICMP and SSH dropped, and a non-listed source is shown unaffected;
  # - the rows say TCP where the type's default protocol makes a rule TCP-only (501-518, 524);
  # - the ICMP-fragment check is removed (rule 518 matches TCP fragments only); rules 518 and 002 are uncovered rows
  #   with their measurements (both counted nothing in every measured case; see the rows).
  # Correction round 2 (2026-11-18, review 20261118T180137Z): rule 503 and fragments became checks (python's
  # TCP_MAXSEG sets the SYN's MSS; a 3000-byte ping is fragmented), loopback got a check, and rows were added for
  # rule 002 and for anti_ddos without ip_filter. Measured by hand on the applied node before writing them.
  # Correction round 1 (2026-11-18, review 20261118T172004Z): the SSH limits, the flush script and the RST limit
  # became behaviour checks; the mangle rows now say which rule each packet met (measured by hand on the applied node).
# Correction round 1 of the swept set (2026-11-25, review 20261125T160917Z, purpose): both variants were checked as rule
# text only. Variant runs have no peer, so each now connects from a network namespace on the node behind a veth pair
# (node side 192.0.2.1; RFC 5737 addresses), as firewall_secure's strict check does: in `plain` (acl now also lists
# 192.0.2.3) a listed source reaches SSH, an unlisted one is dropped and still reaches the opened service port; in
# `ddosonly` held connections from any source stop at ddos_limit.
# Correction round 2 of the swept set (2026-11-25, review 20261125T164112Z): ddosonly's new-connection rate was still
# rule text; a second namespace check makes the base run's 20 paced attempts from 192.0.2.2.
  # 2026-11-18 authoring correction (run 1, 20261118T165605Z): netcat-openbsd keeps a connection open after its input
  # ends, so the 3 held connections outlived this check, and the next check's source was over the connection limit
  # (rule 521 dropped all 10). Each connection is now ended by `timeout 20`, and the check waits 2 s after.
  # 2026-11-18 authoring correction (run 3, 20261118T172550Z; it passed in run 2): 10 `nc -z -w1` started from a shell
  # loop let 6 in, because a dropped SYN is retransmitted after about 1 s, when the limit has refilled. Ten SYNs sent
  # at once measure the connection limit (3) instead (measured by hand: 3, 2, 1 in). The probe now makes 20 paced
  # attempts (one every 0.1 s, each waiting 80 ms, under the retransmission, then closed) and bounds the count by the
  # measured duration (by hand: 8 in 2164 ms, 9 in 2410 ms, 10 in 2856 ms).
  # 2026-11-18 authoring correction (run 1, 20261118T165605Z): conntrack classes a SYN+FIN packet and an RST outside
  # any connection as INVALID, so rule 501 (ctstate INVALID, first of the mangle drops) drops them, and 505 and the RST
  # limit (519/520 in INPUT) never see them (verified by hand on the applied node: 501 counted exactly 5 SYN+FIN and 50
  # RST packets; 505, 519 and 520 counted 0). The check now zeroes the mangle counters first and reads rule 501.
  # SSH brute-force limits, added in correction round 1 (the same rules and numbers as firewall_secure, whose set
  # measured them): each check first waits 61 s so the previous check's 60 s recent window and the overall limit
  # clear; held connections end by `timeout` (netcat-openbsd keeps a connection open after its input ends).
  # Flush script, added in correction round 1: the class's WARNING (lines 11-13) asks for it after any input change.
```
