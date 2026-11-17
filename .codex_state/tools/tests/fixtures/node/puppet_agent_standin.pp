# MOCK-APPLY node fixture `puppet_agent_standin` (HQ 2026-10-27 ruling 7) for classes that declare
# `service { 'puppet': ensure => running, enable => true }` (node_base_domain_desktop). On the lab node a real agent
# daemon would start a catalog run of its own between the harness's run 1 and run 2, applying the catalog and hiding
# run-2 changes (gate v2 would no longer prove idempotency). The fixture adds a systemd drop-in that replaces
# puppet.service's ExecStart with a sleep, so Service['puppet'] is really enabled and started, but no agent runs.
# NOT verified with this fixture: the agent daemon itself running on its interval.
# Lifted by: a harness mode that tolerates a running agent daemon between runs 1 and 2 (HQ batch-7 ruling 2)
file { '/etc/systemd/system/puppet.service.d':
  ensure => directory,
  owner  => 'root',
  group  => 'root',
  mode   => '0755',
}
file { '/etc/systemd/system/puppet.service.d/p8test-standin.conf':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0644',
  content => "# P8TEST STAND-IN: no agent daemon in the lab harness (see the fixture header)\n[Service]\nExecStart=\nExecStart=/bin/sleep infinity\n",
  notify  => Exec['p8test puppet.service stand-in daemon-reload'],
}
exec { 'p8test puppet.service stand-in daemon-reload':
  command     => '/usr/bin/systemctl daemon-reload',
  refreshonly => true,
  before      => Service['puppet'],
}
