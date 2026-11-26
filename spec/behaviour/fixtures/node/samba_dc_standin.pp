# Node fixture samba_dc_standin: stand-ins the class under test expects on the node (a service, a path or a user
# the test node does not have). Applied before the class; placeholders are filled from the run.
file { '/var/tmp/p8test_samba_standin': ensure => directory, owner => 'root', group => 'root', mode => '0700' }
file { '/usr/bin/pdbedit':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    [ "$1" = "-Lw" ] || { echo "p8test stand-in: only -Lw" >&2; exit 2; }
    cut -d' ' -f1 /var/tmp/p8test_samba_standin/users 2>/dev/null | sed 's/$/:0:XXXX:p8test-standin:[U          ]:LCT-00000000:/'
    exit 0
    | EOT
}
file { '/usr/bin/ldbsearch':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    for a in "$@"; do case "$a" in sAMAccountName=*) u="${a#sAMAccountName=}"; u="${u#\'}"; u="${u%\'}" ;; esac; done
    [ -n "$u" ] && [ -f "/var/tmp/p8test_samba_standin/hash.$u" ] && echo "unicodePwd:: $(cat "/var/tmp/p8test_samba_standin/hash.$u")"
    exit 0
    | EOT
}
file { '/usr/bin/create-user.pl':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    [ $# -ge 3 ] || exit 2
    echo "$1 $2 $3" >> /var/tmp/p8test_samba_standin/users
    | EOT
}
file { '/usr/bin/set-user-samba-hash.sh':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    u="$(awk -v f="$1" -v l="$2" '$2 == f && $3 == l { print $1; exit }' /var/tmp/p8test_samba_standin/users)"
    [ -n "$u" ] || { echo "p8test stand-in: no user $1 $2" >&2; exit 1; }
    printf '%s\n' "$3" > "/var/tmp/p8test_samba_standin/hash.$u"
    | EOT
}
