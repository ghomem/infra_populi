# hashman_base: authoring notes (the comments of .codex_state/checks/hashman_base.yml, moved here when the set moved to spec/behaviour/checks/)

```
# Phase 3 checks for puppet_infrastructure::hashman_base (class; required_base filesystem_base; a plain GREEN since
# 2026-11-17, HQ ruling 2: the agent package ships /etc/puppetlabs/code/environments/production/manifests, so the former
# node_fixture puppetserver_code_tree was dropped).
# Fixture: class defaults (debug_mode false) and the lab Hiera (hashman::company 'My Company', hashman::address via
# puppet::address puppet.example.com, hashman::testenv 'False', no minpasswordlen/relaxpassword keys -> 6 / True,
# hashman::dbdir = puppet::manifdir/01_hashman/, hashman::bindir = /opt/puppet-infrastructure/hashman).
# What the checks show: the CLI and its library rendered from Hiera, the empty database files, the Python packages, that
# the CLI starts, and (2026-11-18, HQ ruling C2: node puppetserver, the master-role node p8lab-puppetserver; hashman_base
# composed with postfix_smtp_node, the local MTA its mail needs) the database as Puppet code on a master: the
# administrator adds the fixture user p8hashuser with the CLI, sets its password with `setpw`, and copies the role line
# it prints into the client's node definition. The peer's (ubuntu2) agent run against the master-role server applies
# the user, and PAM there accepts the password. The former `uncovered` note is lifted by that.
# 2026-11-20 (backfill batch 6): purpose and outcomes (HQ rulings 2 and C1), and the server's own agent run after the
# administrator's change (node_agent), which must leave the database alone (replace => 'no').
# 2026-11-20 correction round 1 (review 20261120T104729Z, purpose gap): the CLI's revocation and key distribution were
# not covered. Added: the administrator sets p8hashuser's SSH key (setpubkey), adds p8hashlocked and p8hashexpired with
# passwords and locks one, expires the other, adds and deletes p8hashdel (userdel); the client node definition gets the
# three users' role lines. The agent runs now follow that change. Prototyped on p8lab-puppetserver 2026-11-20: lock
# prefixes the hash with '!', expire turns '$6$' into '$!6$' (the CLI's own auth still accepts an expired password;
# user_base treats any '!' as locked), userdel leaves no line of the user in any database file.
# 2026-11-20 correction round 2 (review 20261120T111006Z, purpose gap): the CLI's support-team notifications (the lab's
# MTA queues them: the fake relayhost defers them, so the queue can be read) and the hashman_web precondition for the
# mails to users. The earlier mail row's evidence was wrong (the lab's hashman::mailfrom is hashman@mycompany.com).
# Authoring error 2026-11-20 (run 20261120T105405Z): the key lines were matched with p8_count (grep -E), and a key's
# base64 body holds '+', a regex quantifier, so the present key read 0; the locked user's key-absence check read 0 for
# the same reason whatever the file held. All three now match the key as a fixed string (grep -F). The behaviour in
# that run was as expected (keys.pp held the key: the-next-agent-run-keeps-the-database passed).
  # 2026-11-18 authoring correction (run 1, 20261118T091214Z): the action ran `setpw` before `unlock`; setpw first
  # authenticates the old password (pp_auth.py.erb:146), which a locked user cannot, so `set -e` stopped the action
  # and nothing was written. The administrator unlocks first, as the web flow (unlock, then login) does. The behaviour
  # is unchanged.
```
