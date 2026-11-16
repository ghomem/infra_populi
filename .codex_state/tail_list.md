# Tail list (HQ 2026-11-16 item 6) — the one list of classes that cannot go GREEN on their node yet
A class goes here when it is blocked with its exact need: what it needs (another OS, a desktop, a second node, a
service the lab lacks…) and the node kind of `.codex_state/lab/nodes.yml` that would lift it. Each line keeps its
blocked.txt entry (category + evidence); this list is the queue to revisit as nodes come up. Advisor-maintained,
append-only (a lifted class gets a dated `lifted:` note, never a deletion).

| class | needs | lifted by (node kind) | blocked since | evidence |
|---|---|---|---|---|
| openvpn_server | puppetserver must load puppet-filemapper's `puppetx/filemapper` (a ruby-load-path entry or server-libdir pluginsync on the master) | none: a master ruling, not a node (escalations/openvpn_server.md) | 2026-11-16 | blocked.txt category 1; puppetserver.log 18:43:54Z |
| mysql_server | an HQ ruling: `service_name => 'mysql'` in the class (marker) or a production Hiera binding, for puppetlabs-mysql 17's MariaDB default on Ubuntu | none: a ruling, not a node (escalations/mysql_server.md) | 2026-11-16 | blocked.txt category 1; run-1 log .codex_state/logs/mysql_server.*.log |
| hashman_base | its mock-apply lifted: a master-role node (a node that is a Puppet server, whose code tree holds the user database) | master-role node (no nodes.yml kind yet; HQ batch-5 ruling 6) | 2026-11-16 | PASS mock-apply (node_fixture puppetserver_code_tree), not blocked |
| hashman_web | its mock-apply lifted: a master-role node (code tree + the site's logo files) | master-role node (no nodes.yml kind yet; HQ batch-5 ruling 6) | 2026-11-16 | PASS mock-apply (node_fixture hashman_master_standin), not blocked |
| mysql_server | lifted: 2026-11-16 (HQ batch-5 ruling 2: service_name => 'mysql', a module-compatibility change; class_rulings.txt) | — | — | unblocked |
| user_desktop_sudoer | groups lpadmin and sambashare (desktop packages), absent on the Ubuntu server node | kubuntu (or gnome) | 2026-11-16 | blocked.txt category 5; `getent group lpadmin sambashare` empty on puppet8node |
| mysql_db | an HQ ruling: where the MySQL client package is set (puppetlabs-mysql 17's mariadb-client default removes the MySQL server) | none: a ruling, not a node (escalations/mysql_db.md) | 2026-11-16 | blocked.txt category 1; dpkg.log removals 23:28:30 |
