node 'backups01' {

  # Basic declarations
  class { 'infra_populi::node_base':
    filesystem_security => false, # the unprivileged user 'backups' needs to execute the ssh command
  }
  include passwd_common
  include passwd_backups_srv
  include infra_populi::backup_rsnapshot_pre

  $bindir = lookup('filesystem::bindir')

  # defaults for the classes below
  # can be overrriden
  $mydir      = '/home/backups/in'
  $myuser     = 'backups'
  $snapdir    = '/home/backups/snapshots'
  $tarballdir = '/home/backups/tarballs'
  $mynode1    = 'hostname.domain.xxx'

  file { [ $mydir, $snapdir, $tarballdir ]:
    ensure  => directory,
    mode    => '0644',
    owner   => $myuser,
    group   => $myuser,
  }

  # fetches data from a remote directory
  infra_populi::sync { "${mynode01}_folders":
    localdir       => $mydir,
    localuser      => $myuser,
    remotedir      => '/directory/to/backup',
    remoteuser     => $myuser,
    hour           => '15',
    minute         => '00',
    hostlist       => "${mynode1}:22",
    bwlimit_mbitps => 80,
  }

  # performs backups of a local directory keeping 7 days of tarball copies
  infra_populi::backup { "${mynode01}_backups" :
    basedir  => "${mydir}/${mynode01}",
    prefix   => '',
    backdir  => "${tarballdir}/${mynode01}",
    ndays    => 7,
    bindir   => $bindir,
  }

  # performs backups of a local directory, keeping 30 days of rsnapshots copies
  infra_populi::backup_rsnapshot { "${mynode1}":
    basedir => "${mydir}/${mynode01}",
    prefix  => '',
    backdir => "${snapdir}/${mynode01}",
    user    => $myuser,
    hour    => '03',
    minute  => '0',
    ndays   => 30,
  }

}
