#!/usr/bin/python3

import glob
import os
import subprocess
import sys
from datetime import datetime, timezone

# Local change #19 (HQ after batch 20, item 3): `puppet certregen healthcheck` does not exist on OpenVox 8, so the
# expiry dates are read directly from the CA's signed certificates (openssl). Thresholds and output are kept.
CA_SIGNED_DIRS = ["/etc/puppetlabs/puppetserver/ca/signed",  # Puppet >= 7 / OpenVox
                  "/etc/puppetlabs/puppet/ssl/ca/signed"]    # Puppet <= 6


def read_expiry(path):
    output = subprocess.check_output(["openssl", "x509", "-enddate", "-noout", "-in", path], text=True)
    when = datetime.strptime(output.strip().split("=", 1)[1], "%b %d %H:%M:%S %Y %Z")
    return when.replace(tzinfo=timezone.utc)


def main():

    if os.geteuid() != 0:
        print("please run as root")
        sys.exit(1)
    signed_dir = next((d for d in CA_SIGNED_DIRS if os.path.isdir(d)), None)
    certificates = sorted(glob.glob(os.path.join(signed_dir, "*.pem"))) if signed_dir else []
    if not certificates:
        print("no signed certificates found in %s" % " or ".join(CA_SIGNED_DIRS))
        sys.exit(1)

    # This runs the command and collects the output
    # This will be the list of each machine's certificate expiry, read from the certificate itself (local change
    # #19; the upstream comment here described certregen's dictionaries)
    try:
        list_of_certs = [(os.path.basename(path)[:-len(".pem")], read_expiry(path)) for path in certificates]
    except Exception:
        print("reading the certificates in %s failed" % signed_dir)
        sys.exit(1)
    now = datetime.now(timezone.utc)
    expiring_machine_name = None
    earliest_expiration_date = datetime.max.replace(tzinfo=timezone.utc)

    # Here we will check the status of each machine and report the result in Nagios format
    for name, expiration_date in list_of_certs:
        if expiration_date <= now:
            print("Critical: certificate of %s has expired on %s." % (name, expiration_date))
            sys.exit(2)
        if expiration_date < earliest_expiration_date:
            earliest_expiration_date = expiration_date
            expiring_machine_name = name

    expiring_time = "%d days" % (earliest_expiration_date - now).days

    if (abs((now - earliest_expiration_date).days) < 10):
        print ("Critical: certificate of %s will expire in %s" % (expiring_machine_name, expiring_time))
        sys.exit(2)
    elif (abs((now - earliest_expiration_date).days) < 30):
        print ("Warning: Certificate of %s will expire in %s" % (expiring_machine_name, expiring_time))
        sys.exit(1)
    else:
        print ("OK: The next certificate expiration will be from %s, in %s" % (expiring_machine_name, expiring_time))
        sys.exit(0)


if __name__ == "__main__":
    main()
