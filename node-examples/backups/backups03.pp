node 'backups03' {

  # Basic declarations
  include infra_populi::node_base
  include passwd_common
  include infra_populi::backup_rsnapshot_pre

  # performs backups of a local directory, keeping 30 days of rsnapshots copies
  $mynode1 = 'hostname'
  infra_populi::backup_rsnapshot { "${mynode1}":
    basedir => "/directory/to/backup",
    prefix  => 'testrsnapshot',
    backdir => "/home/backups/rsnapshottest",
    user    => backups,
    hour    => '03',
    minute  => '0',
    ndays   => 30,
  }

}
