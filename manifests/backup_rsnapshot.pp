# @summary Configures a named rsnapshot backup and its daily cron schedule.
#
# Renders an rsnapshot configuration for a local directory and schedules the
# daily retention level.
#
# @dependencies
# - `puppet_infrastructure::backup_rsnapshot_pre` for rsnapshot and its
#   configuration directory
# - `puppet_infrastructure/backup/rsnapshot.conf.erb` from this module
define puppet_infrastructure::backup_rsnapshot (
  $basedir,
  $prefix,
  $backdir,
  $ndays,
  $user = 'root',
  $hour = '23',
  $minute = '0',
) {

  $myconffile = "/etc/rsnapshot.d/rsnapshot-${title}.conf"

  file { $myconffile:
    mode    => '0644',
    owner   => 'root',
    group   => 'root',
    content => template('puppet_infrastructure/backup/rsnapshot.conf.erb'),
  }

  cron { "cron_snapshot_${title}_backup":
    command => "/usr/bin/rsnapshot -c ${myconffile} daily",
    user    => $user,
    hour    => $hour,
    minute  => $minute,
    require => File[$myconffile],
  }
}
