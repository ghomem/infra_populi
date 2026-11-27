# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own (flatten is a Puppet core function); through infra_populi::user_base: puppetlabs-stdlib 9.7.0, puppetlabs-sshkeys_core 2.5.0 (vendored).
### Purpose ########
# This defined type defines a desktop sudoer user

### Dependencies ###
# defined type: infra_populi::user_base
# defined type: infra_populi::user_kde_lock_screen
define infra_populi::user_desktop_sudoer( $myname = 'Dummy Dummier', $myhash = '', $mykey = 'dummykey', $mygrouplist = [ ], $ignorekey = false, $myppsigs = '', $myppwrapped = '', $screenlock_timeout_minutes = 5, $screenlock_grace_seconds = 0, String $myhomemode = '', String $user_shell = '/bin/bash') {

  $grouplist = flatten( [ $mygrouplist, [ $title, 'cdrom', 'dip', 'plugdev', 'lp', 'lpadmin', 'sambashare', 'adm', 'sudo' ] ] )
  infra_populi::user_base { $title : myname => $myname, myhash => $myhash , mykey => $mykey, mygrouplist => $grouplist, ignorekey => $ignorekey, myppsigs => $myppsigs, myppwrapped => $myppwrapped, myhomemode => $myhomemode, user_shell => $user_shell }

  infra_populi::user_kde_lock_screen { $title : screenlock_timeout_minutes => $screenlock_timeout_minutes, screenlock_grace_seconds => $screenlock_grace_seconds }

}
