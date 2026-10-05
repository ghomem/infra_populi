# Puppet 8 migration: release-0.9.8 manifest validated unchanged.
# Module dependency: puppetlabs-cron_core 1.3.0 (via backup; vendored with Puppet 8.24.2).
### Purpose ########
# This class provides puppet backups
class puppet_infrastructure::puppet_backup {

  $mysystype = 'puppet'
  $mybasedir = lookup("${mysystype}::basedir")
  $myprefix  = lookup("${mysystype}::address")
  $mybackdir = lookup("${mysystype}::backdir")
  $myndays   = lookup("${mysystype}::backdays")
  $compression = lookup( { 'name' => "${mysystype}::compression", 'default_value' => true } )
  $mybindir  = lookup('filesystem::bindir')

  puppet_infrastructure::backup { $mysystype: basedir => $mybasedir, prefix => $myprefix, backdir => $mybackdir, ndays => $myndays, bindir => $mybindir, compression => $compression }

}
