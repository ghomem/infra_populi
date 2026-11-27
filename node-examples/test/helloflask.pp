node 'helloflask' {

  include infra_populi::node_base
  include passwd_common

  infra_populi::hello_world_flask {'primary':
    ip_address  => '0.0.0.0',
    port        => 80,
    uninstall   => false,
    welcome_msg => 'This is our primary application',
  }

  infra_populi::hello_world_flask {'secondary':
    ip_address  => '0.0.0.0',
    port        => 8080,
    uninstall   => false,
    welcome_msg => 'This is our secondary application',
  }

  # open HTTP ports to the Internet
  include infra_populi::firewall_addon_web
  firewall { "1000 accept alt http": proto => 'tcp', dport => 8080 , action => 'accept' }

}
