# MOCK-APPLY node fixture `hashman_master_standin` (HQ 2026-10-27 ruling 7) for hashman_web. Hashman runs on the Puppet
# master, and hashman_web needs the site's logo files, which a lab agent node lacks: the lab Hiera (the upstream example
# common.yaml) sets hashman::companylogo / hashman::companylogomail to '/path/to/logo.png' / '/path/to/logo-email.png',
# local files the class copies from the node it runs on. Placeholder content stands in for the site's images.
# (2026-11-17, HQ ruling 2: the code-tree directory left this fixture; the agent package ships it.)
# Behaviour (the web interface, the logos rendered) is NOT verified by a GREEN with this fixture.
# Lifted by: a master-role node with the site's logo files (no nodes.yml kind yet; HQ batch-5 ruling 6)
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
