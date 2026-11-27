# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own (flatten is a Puppet core function); through infra_populi::user_base: puppetlabs-stdlib 9.7.0, puppetlabs-sshkeys_core 2.5.0 (vendored).
### Purpose ########
# This class defines a sudoer user

### Dependencies ###
# classes: infra_populi::user_base
define infra_populi::user_sudoer( $myname= 'Dummy Dummier', $myhash= 'dummyhash', $mykey = 'dummykey', $mygrouplist = [ ], $ignorekey = false, $myppsigs = '', $myppwrapped = '', $myhome = '', String $myhomemode = '', String $user_shell = '/bin/bash') {

  if $facts['os']['family'] == 'RedHat' {
    $grouplist = flatten( [ $mygrouplist, [ 'wheel' ] ] )
  } else {
    $grouplist = flatten( [ $mygrouplist, [ 'sudo' ] ] )
  }

  infra_populi::user_base { $title : myname => $myname, myhash => $myhash , mykey => $mykey, mygrouplist => $grouplist, ignorekey => $ignorekey, myppsigs => $myppsigs, myppwrapped => $myppwrapped, myhome => $myhome, myhomemode => $myhomemode, user_shell => $user_shell }

}
