# @summary Restricts selected commands to members of a designated group.
#
# Applies root ownership and the requested group and mode to each command path.
# When no group is provided, RedHat-family systems use `wheel` and all other
# systems use `sudo`.
#
# @param restricted_cmds Command path or paths to restrict.
# @param restricted_group Group permitted to execute the commands.
# @param restricted_mode File mode applied to the commands.
#
# @dependencies
# - The structured `os.family` fact
# - The target system's `wheel` or `sudo` group when no group is specified
define puppet_infrastructure::filesystem_sec (
  $restricted_cmds = '',
  $restricted_group = '',
  $restricted_mode = '0750',
) {
  $os_family = $facts['os']['family']

  if $restricted_group == '' {
    if $os_family == 'RedHat' {
      $restricted_group = 'wheel'
    } else {
      $restricted_group = 'sudo'
    }
  }

  file { $restricted_cmds:
    owner => 'root',
    group => $restricted_group,
    mode  => $restricted_mode,
  }
}
