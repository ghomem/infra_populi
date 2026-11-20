# Puppet 8 migration: release-0.9.10 manifest; local changes #14: the backup directory declared here; #15: the script fails loudly.
# Module dependencies: puppetlabs-cron_core 1.3.0 (vendored with Puppet 8.24.2); puppetlabs-stdlib 9.7.0 (ensure_resource).
### Purpose ########
# This class implements simple tar based generic backups
define puppet_infrastructure::backup (
  $basedir, $prefix, $backdir, $ndays, $bindir,
  $user = 'root',
  $hour = '23',
  $minute = '0',
  $monthday = '*',
  Boolean $compression = true,
) {

  # parameters are needed for resources and erb template

  # The directory the script writes into. It is declared here, where the target is received, so that every caller is
  # covered; its parent (filesystem::backdir) is filesystem_base's. ensure_resource lets two backups share a target.
  ensure_resource('file', $backdir, { 'ensure' => 'directory', 'owner' => $user, 'group' => 'root', 'mode' => '0755' })

  file { "${bindir}/backup-${title}.sh":
  mode    => '0755',
  owner   => 'root',
  group   => 'root',
  content => template('puppet_infrastructure/backup/backup.sh.erb'),
  }

  cron { "cron_${title}_backup":
  command   => "${bindir}/backup-${title}.sh",
  user      => $user,
  hour      => $hour,
  minute    => $minute,
  monthday  => $monthday,
  require   => File[ "${bindir}/backup-${title}.sh" ]
  }

}
