# @summary Adds HTTP and HTTPS ingress rules for hosts with a managed firewall.
#
# @note This class only adds web traffic rules. Include a base firewall class,
#   such as puppet_infrastructure::firewall or
#   puppet_infrastructure::firewall_secure, or provide equivalent firewall
#   setup before applying this addon.
#
# @see puppetlabs-firewall

class puppet_infrastructure::firewall_addon_web {

  # webserver specific firewall rules - simple case
  firewall { '200 accept http':  proto => 'tcp', dport => 80,  jump => 'accept', }
  firewall { '201 accept https': proto => 'tcp', dport => 443, jump => 'accept', }

}
