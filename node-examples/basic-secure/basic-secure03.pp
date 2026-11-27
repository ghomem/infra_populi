node 'basic-secure03' {

    # FIXME: please edit with the IPs you want to whitelist for ssh
    $ssh_ip_whitelist = [ 'A.B.C.D' ]

    class {'infra_populi::node_base':
        ssh_strict              => true,
        ssh_acl                 => $ssh_ip_whitelist,
    }

    include passwd_common

    # open HTTP ports to the Internet
    include infra_populi::firewall_addon_web
}

