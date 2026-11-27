node 'backups04' {

  # Basic declarations
  include infra_populi::node_base
  include passwd_common

  $bindir = lookup('filesystem::bindir')

  # performs backups of a local directory keeping 7 days of tarball copies
  infra_populi::backup { 'backup' :
    basedir  => '/directory/to/backup',
    prefix   => 'backup-file',
    backdir  => '/home/backups/localbackups',
    ndays    => 7,
    bindir   => $bindir,
  }

}
