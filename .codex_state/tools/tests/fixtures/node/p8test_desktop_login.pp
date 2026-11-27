# Node fixture `p8test_desktop_login` for mount_shares_desktop on the GNOME node (kind gnome). It replaces the stand-in
# `p8test_desktop_home` (HQ after batch 20, item 6: the lift "the desktop login"). The define writes its two scripts into
# /home/<username>/Desktop (mount_shares_desktop.pp:7-8) and never declares it: on a desktop the user's first graphical
# login creates ~/Desktop (xdg-user-dirs, started by the session). Here that login happens for real: the fixture
# declares the test user p8testuser (never a real account) and logs it in to GNOME once through GDM's automatic login,
# then waits until the session has created ~/Desktop. The directory is not declared: it is the login's.
# Runs only while ~/Desktop is absent, and before the define's files.
# Lifted by: nothing needed — a test asset (rules/test_asset_fixtures.txt): ~/Desktop comes from a real first login.
user { 'p8testuser':
  ensure     => present,
  home       => '/home/p8testuser',
  managehome => true,
  shell      => '/bin/bash',
}
file { '/usr/local/sbin/p8test-first-desktop-login':
  ensure  => file,
  owner   => 'root',
  group   => 'root',
  mode    => '0755',
  content => @(LOGIN),
    #!/bin/sh
    # p8test fixture (p8test_desktop_login): one real GNOME login of p8testuser (GDM automatic login), waiting until the
    # session's xdg-user-dirs has created ~/Desktop; the automatic login is removed again afterwards.
    set -e
    conf=/etc/gdm3/custom.conf
    cp "$conf" /run/p8test-gdm-custom.conf.orig
    sed -i -e '/^AutomaticLogin/d' -e 's/^\[daemon\]$/[daemon]\nAutomaticLoginEnable=true\nAutomaticLogin=p8testuser/' "$conf"
    systemctl restart gdm3
    for i in $(seq 180); do
      [ -d /home/p8testuser/Desktop ] && break
      sleep 1
    done
    cp /run/p8test-gdm-custom.conf.orig "$conf"
    test -d /home/p8testuser/Desktop
    | LOGIN
}
exec { 'p8test first desktop login of p8testuser':
  command => '/usr/local/sbin/p8test-first-desktop-login',
  creates => '/home/p8testuser/Desktop',
  timeout => 300,
  require => [User['p8testuser'], File['/usr/local/sbin/p8test-first-desktop-login']],
}
Exec['p8test first desktop login of p8testuser'] -> Infra_populi::Mount_shares_desktop <| |>
