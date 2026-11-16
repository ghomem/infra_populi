# MOCK-APPLY node fixture `hashman_master_standin` (HQ 2026-10-27 ruling 7) for hashman_web. Hashman runs on the Puppet
# master, and hashman_web needs two things a lab agent node lacks:
# - the master's code tree directory that its required_base hashman_base writes the user database into (the same as
#   fixture puppetserver_code_tree);
# - the site's logo files: the lab Hiera (the upstream example common.yaml) sets hashman::companylogo /
#   hashman::companylogomail to '/path/to/logo.png' / '/path/to/logo-email.png', local files the class copies from the
#   node it runs on. Placeholder content stands in for the site's images.
# Behaviour (the web interface, the logos rendered) is NOT verified by a GREEN with this fixture.
file { '/etc/puppetlabs/code/environments/production/manifests':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { ['/path', '/path/to']:
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { ['/path/to/logo.png', '/path/to/logo-email.png']:
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "p8test placeholder logo (hashman_master_standin)\n",
}
