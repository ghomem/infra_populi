# Puppet 8 migration: lock an existing Hashman user; skip when already locked.
# Module dependencies: none (core exec resource only).
### Purpose ########
# This class locks an existing user

### Dependencies ###
# classes: infra_populi::hashman_base
define infra_populi::user_lock( ){

  $myuser = $title
  $hashmandir = lookup('hashman::bindir')
  $hashmandb = lookup('hashman::dbdir')

  exec { "user_lock_${myuser}":
  # the last part is to avoid E_ERR on already locked users
  command => "${hashmandir}/common/pp_auth.py lock ${myuser} DUMMYARG; exit 0",
  unless => "/bin/grep -Eq \"^[[:space:]]*[\$]${myuser}_pwd_hash[[:space:]]*=[[:space:]]*'!\" ${hashmandb}/hashes.pp",
  require =>  Class[ 'infra_populi::hashman_base' ],
  }

}
