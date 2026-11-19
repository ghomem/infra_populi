# Approval conditions — single source
Conditions HQ ruled to be recorded in the behaviour approval report: behaviour that holds only under a stated
condition, or that differs from the baseline and is accepted without a change. The approval report reads them from
here. Add an item only with its HQ source and the evidence. Advisor-only file.

| # | class | condition | evidence | source |
|---|---|---|---|---|
| 1 | openvpn_server (and network_vpn) | The server's data channel is compressed one way only on OpenVPN 2.6: it receives LZO, it sends uncompressed. Accepted with no change; clients should drop compression at the cutover (documentation_list.md item 3, cutover item 6). | checks/results/openvpn_server/20261119T160852Z-author.json and 20261119T161347Z-reviewer (the-data-channel-is-compressed-both-ways) | HQ batch-14 ruling 2 |
| 2 | caching_nameserver (and network_vpn) | Recursion is shown in the lab with named IPv4-only (`-4`, a lab fixture). On a host without working IPv6, BIND 9.18.39 with this configuration answered SERVFAIL for some names: IPv6 attempts that fail at once still count against max-recursion-queries (50). No class change. It becomes a finding only if Salatiel confirms that a production host lacks IPv6. | checks/network_vpn.yml header (authoring correction 2026-11-19: the -d trace and the -4 comparison); results/network_vpn/20261119T115047Z-author (SERVFAIL) and 20261119T140625Z-author (with -4) | HQ batch-14 ruling 5 |
