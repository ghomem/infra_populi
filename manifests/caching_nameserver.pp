# Puppet 8 migration: release-0.9.10 manifest; local change #9: named IPv4-only on a host without a global IPv6 address.
# Module dependency: puppetlabs-stdlib 9.7.0 (file_line).
### Purpose ########
# This class provides a caching nameserver server using bind

# allowed_networks is an array of networks with bitmask. Example ['192.168.1.0/24', '192.168.5.0/24']
class infra_populi::caching_nameserver ( Array $allowed_networks = [] ){

    if ( $facts['os']['family'] == 'RedHat' ){

        $package_name = 'bind'
        $service_name = 'named'
        $conf_file    = '/etc/named.conf'
        $directory    = '/var/named'

    }
    else {

        $package_name = 'bind9'
        $service_name = 'named'
        $conf_file    = '/etc/bind/named.conf.options'
        $directory    = '/var/cache/bind'
    }

    package { 'bind':
        ensure => present,
        name   => $package_name,
    }

    service { $service_name:
        ensure  => 'running',
        require => Package['bind'],
    }

    file { $conf_file :
        owner   => root,
        group   => root,
        mode    => '0644',
        content => template('infra_populi/bind/named.conf.options.erb'),
        notify  => Service[ $service_name ],
    }

    # On a host without a global unicast IPv6 address (2000::/3; a unique-local fd00::/8 address is reported as scope
    # global but reaches no internet), BIND's IPv6 attempts fail at once yet use up its recursion budget, and names
    # with long delegation chains get SERVFAIL: there, named runs IPv4-only. A host with one is left as it is.
    $global_ipv6 = $facts['networking']['interfaces'].any |$name, $iface| {
        $iface['bindings6'] =~ Array and $iface['bindings6'].any |$b| { $b['address'] =~ /\A[23][0-9a-fA-F]{3}:/ }
    }
    if !$global_ipv6 {
        $named_defaults = $facts['os']['family'] ? {
            'RedHat' => { 'path' => '/etc/sysconfig/named', 'line' => 'OPTIONS="-4"' },
            default  => { 'path' => '/etc/default/named', 'line' => 'OPTIONS="-u bind -4"' },
        }
        file_line { 'named IPv4 only':
            path    => $named_defaults['path'],
            line    => $named_defaults['line'],
            match   => '^OPTIONS=',
            require => Package['bind'],
            notify  => Service[ $service_name ],
        }
    }

}
