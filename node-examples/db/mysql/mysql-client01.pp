node 'mysql-client01' {

  include infra_populi::node_base
  include passwd_common

  package { 'mariadb-client':
    ensure => 'installed',
  }

}
