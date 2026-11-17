# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: puppetlabs-stdlib 9.7.0 (member); through puppet_infrastructure::user_sudoer/user_base: puppetlabs-sshkeys_core 2.5.0 (vendored).
### Purpose ########
# This defined type supports managing several users_sudoers and excluding some of them of this management

define puppet_infrastructure::users_sudoers (
  # A hash-of-hashes of the users to be managed (this may include users that are to be excluded of management)
  Hash $configs,
  # An array with the resource names of the users that are to be excluded from being managed (even if they are present in the $configs hash)
  Array $unmanaged_users = [],
) {

  # We filter to get only those elements of the config hash which are _not_ members of the unmanaged_users array.
  # See the puppet docs for the builtin function filter, in particular the final example
  # ("Example: Using the filter function with a hash and a two-parameter lambda"):
  # https://puppet.com/docs/puppet/5.3/function.html#filter
  $configs_filtered = $configs.filter |$key, $value| {!member($unmanaged_users, $key)}

  # Create the users
  create_resources (puppet_infrastructure::user_sudoer, $configs_filtered)

}
