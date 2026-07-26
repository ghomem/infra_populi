# @summary Deploys a password-setting script for named OpenVPN connections.
#
# The generated script prompts for a password and applies it to each configured
# NetworkManager VPN connection. This defined type can manage multiple scripts.
#
# @example Place the script in a local binary directory
#   puppet_infrastructure::openvpn_set_vpn_passwd_file { '/usr/local/AS/bin/set_vpn_passwd.sh':
#     vpn_list => ['VPN1', 'VPN2', 'VPN3'],
#   }
#
# @param vpn_list NetworkManager connection names; names must not contain spaces.
# @param file_owner Owner and group assigned to the generated script.
# @param file_path Absolute path of the generated script.
#
# @dependencies
# - `puppet_infrastructure/openvpn/set_vpn_passwd.sh.erb` from this module
# - `nmcli` and `kdialog` on the target system when the script is executed
define puppet_infrastructure::openvpn_set_vpn_passwd_file (
  Array $vpn_list = [],
  $file_owner = 'root',
  $file_path = $title,
) {

  file { $file_path:
    mode    => '0755',
    owner   => $file_owner,
    group   => $file_owner,
    content => template('puppet_infrastructure/openvpn/set_vpn_passwd.sh.erb'),
  }
}
