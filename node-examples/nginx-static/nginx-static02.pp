node 'nginx-static02' {

  # Static HTTP server with defined type infra_populi::nginx_static_domain
  # Acess by IP configurable, see 'redirect_default' below

  include infra_populi::node_base
  include passwd_common
  include infra_populi::nginx_base

  file { '/var/www':
    ensure => directory,
  }

  file { '/var/www/html':
    ensure => directory,
  }

  # Hello world index.html
  file { '/var/www/html/index.html':
    mode    => '0644',
    owner   => 'root',
    group   => 'root',
    content => "<html><head></head><body><h1>Hello World - ${trusted['certname']}<h1></body></html>",
    require => Class[ 'infra_populi::nginx_base' ],
  }
 
  infra_populi::nginx_static_domain { 'nginx-static02.puppetdemo.lan':
    domain                 => 'nginx-static02.puppetdemo.lan',
    www_root               => '/var/www/html',
    server_default_create  => true,
    # By default this class creates an HTTP server and a default server
    # that returns 404 when the website is accessed by the IP.
    # If you want the website to be accessible by IP you can uncomment
    # the below to set 'redirect_default' to 'true'
    #redirect_default       => true,
  }

  # open HTTP ports to the Internet
  include infra_populi::firewall_addon_web

}
