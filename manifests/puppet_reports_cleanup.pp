# puppet_infrastructure::puppet_reports_cleanup
#
# Removes Puppet report files older than the configured retention period to
# prevent unbounded growth in the report directory.
#
# Dependencies:
# - Hiera data for `puppet::reportdir`
# - Hiera data for `puppet::reportdays`
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
