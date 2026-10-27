# MOCK-APPLY node fixture `samba_dc_standin` (HQ ruling 7, 2026-10-26: user_samba stand-in accepted; 2026-10-27 ruling 7).
# Stateful STAND-INS for the Zentyal/Samba DC commands user_samba runs (pdbedit, ldbsearch, create-user.pl,
# set-user-samba-hash.sh). They keep a fake user/hash store under /var/tmp/p8test_samba_standin so the class's
# unless-guards see the effect of its own commands. Nothing talks to Samba: behaviour is NOT verified.
file { '/var/tmp/p8test_samba_standin': ensure => directory, owner => 'root', group => 'root', mode => '0700' }
file { '/usr/bin/pdbedit':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    #!/bin/sh
    # P8TEST STAND-IN for pdbedit -Lw (lists username:... lines of the fake store)
    [ "$1" = "-Lw" ] || { echo "p8test stand-in: only -Lw" >&2; exit 2; }
    cut -d' ' -f1 /var/tmp/p8test_samba_standin/users 2>/dev/null | sed 's/$/:0:XXXX:p8test-standin:[U          ]:LCT-00000000:/'
    exit 0
    | EOT
}
file { '/usr/bin/ldbsearch':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    #!/bin/sh
    # P8TEST STAND-IN for: ldbsearch -H <sam.ldb> sAMAccountName='<user>' unicodepwd
    for a in "$@"; do case "$a" in sAMAccountName=*) u="${a#sAMAccountName=}"; u="${u#\'}"; u="${u%\'}" ;; esac; done
    [ -n "$u" ] && [ -f "/var/tmp/p8test_samba_standin/hash.$u" ] && echo "unicodePwd:: $(cat "/var/tmp/p8test_samba_standin/hash.$u")"
    exit 0
    | EOT
}
file { '/usr/bin/create-user.pl':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    #!/bin/sh
    # P8TEST STAND-IN for Zentyal create-user.pl <user> <first> <last> <smbhash>: records "user first last"
    [ $# -ge 3 ] || exit 2
    echo "$1 $2 $3" >> /var/tmp/p8test_samba_standin/users
    | EOT
}
file { '/usr/bin/set-user-samba-hash.sh':
  ensure  => file,
  mode    => '0755',
  content => @(EOT),
    #!/bin/sh
    # P8TEST STAND-IN for set-user-samba-hash.sh <first> <last> <smbhash>: stores the hash for the matching user
    u="$(awk -v f="$1" -v l="$2" '$2 == f && $3 == l { print $1; exit }' /var/tmp/p8test_samba_standin/users)"
    [ -n "$u" ] || { echo "p8test stand-in: no user $1 $2" >&2; exit 1; }
    printf '%s\n' "$3" > "/var/tmp/p8test_samba_standin/hash.$u"
    | EOT
}
