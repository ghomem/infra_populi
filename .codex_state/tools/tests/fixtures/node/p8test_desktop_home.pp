# MOCK-APPLY node fixture `p8test_desktop_home` (HQ 2026-10-27 ruling 7; HQ batch-8 ruling 5) for mount_shares_desktop.
# The define writes its two scripts into /home/<username>/Desktop (mount_shares_desktop.pp:7-8) and never declares it:
# on a desktop the user's first graphical login creates ~/Desktop (xdg-user-dirs), and no class of the code tree owns
# it. This declares the fixture user p8testuser (never a real account) with that directory, as a first login leaves it.
# Lifted by: a first graphical login of the user on a lab desktop node (xdg-user-dirs creates ~/Desktop)
user { 'p8testuser':
  ensure     => present,
  home       => '/home/p8testuser',
  managehome => true,
  shell      => '/bin/bash',
}
file { '/home/p8testuser/Desktop':
  ensure  => directory,
  owner   => 'p8testuser',
  group   => 'p8testuser',
  mode    => '0755',
  require => User['p8testuser'],
}
