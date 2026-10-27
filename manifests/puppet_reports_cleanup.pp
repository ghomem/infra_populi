# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependency: puppetlabs-cron_core 1.3.0 (vendored with Puppet 8.24.2).
### Purpose ########
# This class cleans up puppet reports to avoid filling the disk
class puppet_infrastructure::puppet_reports_cleanup {

  $reportdir  = lookup('puppet::reportdir')
  $reportdays = lookup('puppet::reportdays')

  cron { 'puppet_report_cleanup':
  command  => "find ${reportdir} -type f -mtime +${reportdays} | xargs rm",
  user     => root,
  monthday => '*',
  hour     => '0',
  minute   => '0',
  }

}
