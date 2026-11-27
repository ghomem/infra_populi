# Puppet 8 migration: release-0.9.10 manifest; upstream defect fixed (HQ ruling 2026-10-27): the default branch reassigned the parameter $restricted_group (Puppet 8: Cannot reassign variable) and now assigns $restricted_group_real, same values; plus one local change (policy B, HQ batch-12 ruling 5; rules/local_changes.md #6): links => follow, so a listed command that is a link (nc, telnet, ftp) has the program it points to restricted, not the link.
# Module dependencies: none.
### Purpose ########
# This classe provides extra filesystem security by restricting a certain set of commands to a certain group
define infra_populi::filesystem_sec ( $restricted_cmds = '' , $restricted_group = '' , $restricted_mode = '0750' )
{
  $os_family = $facts['os']['family']
  
  if $restricted_group == '' {
    if $os_family == 'RedHat' {
      $restricted_group_real = 'wheel'
    } else {
      $restricted_group_real = 'sudo'
    }
  } else {
    $restricted_group_real = $restricted_group
  }

  # Local change #6: manage the program a link points to, not the link (a link has no mode of its own)
  file { $restricted_cmds:
    links => follow,
    owner => root,
    group => $restricted_group_real,
    mode  => $restricted_mode,
  }

}

