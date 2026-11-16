# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependencies: none of its own; through puppet_infrastructure::backup: puppetlabs-cron_core 1.3.0 (vendored with Puppet 8.24.2).
### Purpose ########
# This class provides sysmon backups
class puppet_infrastructure::sysmon_backup {

  $mysystype = 'sysmon'
  $mybasedir = lookup("${mysystype}::basedir")
  $myprefix  = lookup("${mysystype}::address")
  $mybackdir = lookup("${mysystype}::backdir")
  $myndays   = lookup("${mysystype}::backdays")
  $compression = lookup( { 'name' => "${mysystype}::compression", 'default_value' => true } )
  $mybindir  = lookup('filesystem::bindir')

  puppet_infrastructure::backup { $mysystype: basedir => $mybasedir, prefix => $myprefix, backdir => $mybackdir, ndays => $myndays, bindir => $mybindir, compression => $compression }

}
