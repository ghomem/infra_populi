#!/usr/bin/env python3
"""Lab clocks agree with the laptop's (HQ 2026-11-17 batch-8 ruling 4).

A laptop suspend pauses the VMs; the master then ran 2 h 26 min behind for the rest of the morning (no VirtualBox
guest time service; systemd-timesyncd's next poll was up to 34 min of guest time away). Certificates, report times
and the freshness token all assume one clock, so a run refuses while any lab host is off by more than a few seconds.

    clock_check.py [--max-skew SECONDS] <ssh-alias>...

Each host's `date -u +%s.%N` is read over ssh and compared with the midpoint of the laptop's clock around the call;
half the round trip is the measurement's uncertainty and is given to the host. Prints `CLOCK <alias> <skew>s` per
host; exit 0 all within the limit, 1 a host is off (CLOCK_SKEW) or its clock could not be read (CLOCK_UNREADABLE),
2 usage. The default limit is 5 s; P8_CLOCK_MAX_SKEW overrides it.
"""

import argparse
import os
import subprocess
import sys
import time

DEFAULT_MAX_SKEW = 5.0
SSH_TIMEOUT = 20


def skew(alias):
    """(skew in seconds, uncertainty), or a reason string when the host's clock cannot be read."""
    t0 = time.time()
    try:
        proc = subprocess.run(["ssh", alias, "date -u +%s.%N"], capture_output=True, text=True,
                              timeout=SSH_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return f"no answer within {SSH_TIMEOUT}s"
    t1 = time.time()
    if proc.returncode != 0:
        return f"ssh exited {proc.returncode}: {proc.stderr.strip()[-200:]}"
    try:
        remote = float(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return f"unparseable date output {proc.stdout.strip()[:80]!r}"
    return remote - (t0 + t1) / 2, (t1 - t0) / 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--max-skew", type=float,
                    default=float(os.environ.get("P8_CLOCK_MAX_SKEW", DEFAULT_MAX_SKEW)))
    ap.add_argument("hosts", nargs="+")
    args = ap.parse_args(argv)
    bad = 0
    for alias in args.hosts:
        result = skew(alias)
        if isinstance(result, str):
            print(f"CLOCK_UNREADABLE {alias}: {result}", file=sys.stderr)
            bad = 1
            continue
        off, err = result
        if abs(off) - err > args.max_skew:
            print(f"CLOCK_SKEW {alias}: {off:+.1f}s off the laptop's clock (limit {args.max_skew:g}s); "
                  f"resync it (`sudo systemctl restart systemd-timesyncd`, then `timedatectl`) before a lab run",
                  file=sys.stderr)
            bad = 1
        else:
            print(f"CLOCK {alias} {off:+.3f}s")
    return bad


if __name__ == "__main__":
    sys.exit(main())
