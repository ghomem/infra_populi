#!/usr/bin/env python3
"""Turn `puppet facts show --render-as json` output (stdin) into a yaml-terminus facts file (stdout).

  facts.py debian   the node's own facts, unchanged
  facts.py redhat   the same facts with the os.* family/name/release rewritten to RHEL 9 (composite
                    compiles of RedHat branches, e.g. node_base -> filesystem_yum; step 2.2)
The YAML document embeds the values as JSON (valid YAML flow style).
"""
import json
import sys

sys.dont_write_bytecode = True

REDHAT_OS = {"family": "RedHat", "name": "RedHat",
             "release": {"full": "9.4", "major": "9", "minor": "4"}}


def transform(values: dict, variant: str) -> dict:
    if variant == "debian":
        return values
    if variant == "redhat":
        os_facts = dict(values.get("os", {}))
        os_facts.update(REDHAT_OS)
        os_facts.pop("distro", None)
        return {**values, "os": os_facts}
    raise SystemExit(f"unknown facts variant: {variant}")


def to_yaml(values: dict, certname: str = "puppet8node") -> str:
    return f"--- !ruby/object:Puppet::Node::Facts\nname: {certname}\nvalues: {json.dumps(values, sort_keys=True)}\n"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    data = json.load(sys.stdin)
    sys.stdout.write(to_yaml(transform(data, sys.argv[1])))
