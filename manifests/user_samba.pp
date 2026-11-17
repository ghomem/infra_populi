# Puppet 8 migration: manage Zentyal/Samba users and password hashes.
# Module dependencies: none (uses Puppet built-in exec resources and core functions).
define puppet_infrastructure::user_samba( $myname = 'Dummy Dummier',
                                   $mysmbhash = '',
){
  $username = $title
  $localdir = lookup('filesystem::localdir')

  $separate_name = split($myname, ' ')
  $first_name    = $separate_name[0]
  $last_name     = $separate_name[-1]

  exec { "create zentyal user: ${username}":
    command => "create-user.pl $username ${first_name} ${last_name} ${mysmbhash}",
    user    => 'root',
    path    => "${localdir}/bin:/usr/bin",
    unless  => "pdbedit -Lw | grep -w ${username}",
  }

  exec { "set ${username} samba hash":
    command => "set-user-samba-hash.sh ${first_name} ${last_name} ${mysmbhash}",
    user    => 'root',
    path    => "${localdir}/bin:/usr/bin",
    unless  => "ldbsearch -H /var/lib/samba/private/sam.ldb sAMAccountName='${username}' unicodepwd | grep -w ${mysmbhash}",
    require => Exec["create zentyal user: ${username}"],
  }
}
