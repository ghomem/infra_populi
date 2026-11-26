# Node fixture p8test_desktop_login: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
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
Exec['p8test first desktop login of p8testuser'] -> Puppet_infrastructure::Mount_shares_desktop <| |>
