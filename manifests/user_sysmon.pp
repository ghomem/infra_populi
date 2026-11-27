# Puppet 8 migration: release-0.9.10 manifest validated unchanged.
# Module dependency: citrin-htpasswd 1.0.3 (the htpasswd type).
### Purpose ########
# This class defines an Adagios sysmon user

### Dependencies ###
# modules: leinaddm-htpasswd
define infra_populi::user_sysmon( $myname = 'Dummy Dummier', $myhash = '', $myemail = 'dummy@localhost', $mygrouplist = [ ] ) {

  $myusername = $title

  # from module leinaddm-htpasswd
  $htpasswd_file = '/etc/thruk/htpasswd'
  htpasswd { $myusername : cryptpasswd => $myhash, target => $htpasswd_file }

  file { "/etc/naemon/conf.d/contacts/${myusername}.cfg":
  mode    => '0664',
  owner   => 'naemon',
  group   => 'naemon',
  content => template('infra_populi/users/sysmon_contact.erb'),
  }

}

