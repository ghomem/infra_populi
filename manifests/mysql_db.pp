# Puppet 8 migration: 874f854 manifest validated unchanged.
# Module dependencies: puppetlabs-mysql 17.3.0.
# Create a MySQL database with a read/write user and, optionally,
# a read-only user. Remote accounts require TLS; network access is
# restricted separately by the node firewall.
#
define infra_populi::mysql_db (
  String $db_name,
  String $rw_user,
  String $rw_pass,
  Optional[String] $ro_user = undef,
  Optional[String] $ro_pass = undef,
) {

  if ($ro_user and !$ro_pass) or ($ro_pass and !$ro_user) {
    fail('ro_user and ro_pass must either both be provided or both be omitted')
  }

  mysql::db { "${db_name}-rw":
    dbname      => $db_name,
    user        => $rw_user,
    password    => $rw_pass,
    charset     => 'utf8mb3',
    collate     => 'utf8mb3_general_ci',
    host        => '%',
    grant       => ['ALL'],
    tls_options => ['SSL'],
    require     => Class['infra_populi::mysql_server'],
  }

  if $ro_user and $ro_pass {
    mysql::db { "${db_name}-ro":
      dbname      => $db_name,
      user        => $ro_user,
      password    => $ro_pass,
      charset     => 'utf8mb3',
      collate     => 'utf8mb3_general_ci',
      host        => '%',
      grant       => ['SELECT', 'SHOW VIEW'],
      tls_options => ['SSL'],
      require     => Mysql::Db["${db_name}-rw"],
    }
  }
}
