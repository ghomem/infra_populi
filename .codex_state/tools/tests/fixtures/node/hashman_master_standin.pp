# MOCK-APPLY node fixture `hashman_master_standin` (HQ 2026-10-27 ruling 7) for hashman_web: the site's logo files.
# hashman_web copies the logos from the paths in Hiera; the lab Hiera (the upstream example common.yaml) sets
# hashman::companylogo / hashman::companylogomail to '/path/to/logo.png' / '/path/to/logo-email.png', local files of
# the master that are the site's own images. Placeholder content stands in for them.
# (2026-11-17, HQ ruling 2: the code-tree directory left this fixture; the agent package ships it. 2026-11-18, HQ ruling
# C2: hashman_web runs on the master-role node p8lab-puppetserver, so the master itself is no longer a stand-in; the
# web interface, logins and password changes are verified end to end there. Only the images remain placeholders.)
# Not verified with this fixture: that the site's real images render.
# Lifted by: the site's logo files (a production read, Salatiel's); no lab node can lift it.
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
