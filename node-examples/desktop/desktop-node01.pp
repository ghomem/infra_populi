node 'desktop-node01' {

  class {'infra_populi::node_base_desktop':
    apt_surface_list => $apt_surface_desktop,
    firewall_strict_purge => false,
    firewall_ignore_patterns => [ 'lxdbr0', 'docker' ],
  }

}

