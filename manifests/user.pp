# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own; through puppet_infrastructure::user_base: puppetlabs-stdlib 9.7.0, puppetlabs-sshkeys_core 2.5.0 (vendored).
### Purpose ########
# This class defines a normal user not belonging to any special groups

### Dependencies ###
# classes: puppet_infrastructure::user_base
define puppet_infrastructure::user( $myname = 'Dummy Dummier', $myhash = '', $mykey = 'dummykey', $mygrouplist = [ ], $myhome = '', String $myhomemode = '', String $user_shell = '/bin/bash') {

  puppet_infrastructure::user_base { $title : myname => $myname, myhash => $myhash , mykey => $mykey, mygrouplist => $mygrouplist, myhome => $myhome, myhomemode => $myhomemode, user_shell => $user_shell }

}

