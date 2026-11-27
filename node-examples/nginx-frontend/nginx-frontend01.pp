node 'nginx-frontend01' {

  include infra_populi::node_base
  include passwd_common
  include infra_populi::nginx_base

  # Backend - flask application listening on 127.0.0.1:8000
  infra_populi::hello_world_flask {'primary':
    ip_address  => '127.0.0.1',
    port        => 8000,
    uninstall   => false,
    welcome_msg => 'This is our primary application',
  }

  # Frontend for https://nginx-frontend01.puppetdemo.lan
  class { 'infra_populi::nginx_frontend':
    domain                  => 'nginx-frontend01.puppetdemo.lan',
    frontend_sslprefix      => 'star.puppetdemo.lan',
    backend_hosts_and_ports => ['127.0.0.1:8000', ],
    backend_protocol        => 'http',
  }

  # Allow HTTP/HTTPS connections
  include infra_populi::firewall_addon_web

}
