# MOCK-APPLY node fixture `puppetserver_code_tree` (HQ 2026-10-27 ruling 7). hashman_base runs on the Puppet master:
# its user database lives in the master's code tree (hashman::dbdir = puppet::manifdir/01_hashman, puppet::manifdir =
# <basedir>/code/environments/production/manifests). An agent-only node has /etc/puppetlabs/code/environments/production
# but no manifests/ directory; this declares only that directory, so the class can apply on the lab node. Applying the
# class to the lab master instead would write its database into the master's live site manifests. Behaviour (pp_auth,
# the database as Puppet code on a master) is NOT verified by a GREEN with this fixture.
file { '/etc/puppetlabs/code/environments/production/manifests':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
