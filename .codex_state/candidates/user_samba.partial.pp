# CANDIDATE - NOT PRODUCTION, PARTIAL MIGRATION. Do not deploy.
# What was fixed: $localdir was resolved by legacy dynamic scoping (removed since
#   Puppet 4); replaced with lookup('filesystem::localdir'), the repository-standard
#   pattern. This made the Puppet 8 catalog COMPILE.
# What is UNVERIFIED: everything else. The class never reached GREEN - it failed
#   during apply because the node lacks pdbedit, ldbsearch, ldbmodify,
#   create-user.pl and set-user-samba-hash.sh. No two-run idempotency was ever
#   demonstrated. Do NOT assume this migration is complete.
# Blocked: Category 5, needs a Zentyal/Samba domain-controller node. See
#   blocked.txt and DESIGN_DECISIONS.md.
#
# CANDIDATE NAMING CONVENTION - applies to the whole candidates directory:
#   .reimplemented.pp - behaviour redesigned, diverges from upstream (network_dhcp)
#   .migrated.pp      - migration COMPLETE, blocked only on validation
#                       (firewall_addon_hosting)
#   .partial.pp       - migration INCOMPLETE, a compile-blocker fixed, never
#                       validated end-to-end (user_samba)

define puppet_infrastructure::user_samba( $myname = 'Dummy Dummier',
                                   $mysmbhash = '',
){
  $localdir = lookup('filesystem::localdir')
  $username = $title

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
