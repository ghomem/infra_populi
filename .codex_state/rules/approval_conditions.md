# Approval conditions — single source
Conditions HQ ruled to be recorded in the behaviour approval report: behaviour that holds only under a stated
condition, or that differs from the baseline and is accepted without a change. The approval report reads them from
here. Add an item only with its HQ source and the evidence. Advisor-only file.

| # | class | condition | evidence | source |
|---|---|---|---|---|
| 1 | openvpn_server (and network_vpn) | The server's data channel is compressed one way only on OpenVPN 2.6: it receives LZO, it sends uncompressed. Accepted with no change; clients should drop compression at the cutover (documentation_list.md item 3, cutover item 6). | checks/results/openvpn_server/20261119T160852Z-author.json and 20261119T161347Z-reviewer (the-data-channel-is-compressed-both-ways) | HQ batch-14 ruling 2 |
| 3 | ssh_secure | The idle disconnect (client_alive_interval) is enforced by sshd's own idle timeouts on OpenSSH 9.2 and later (local change #8). On an older sshd (RHEL 9) it is not enforced: ClientAliveCountMax 0 ends no session there either, and no shell workaround is made. | checks/results/ssh_secure/20261119T170300Z-author.json (an-idle-session-is-ended-after-the-interval, Ubuntu 24.04, OpenSSH 9.6); the RHEL 9 case is an uncovered row of the set (lifted_by rhel9) | HQ batch-14 ruling 3 |

Removed: #2 (caching_nameserver on IPv4-only hosts) became a finding (HQ batch-15 ruling 6) and was fixed by local change #9 (Phase 1 PASS 20261120T000035Z, Phase 3 PASS 20261120T000624Z); the numbers are not reused.
