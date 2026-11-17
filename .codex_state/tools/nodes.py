#!/usr/bin/env python3
"""Lab node inventory reader (HQ 2026-11-16 item 2): the only reader of .codex_state/lab/nodes.yml.

  nodes.py validate                                  exit 0 valid, 2 invalid (problems on stderr)
  nodes.py list                                      one line per kind: kind status vm alias hostonly_ip os_family
  nodes.py kinds                                     the kind names, one per line
  nodes.py get   [--node KIND | --class CLS] FIELD   one field of the selected node
  nodes.py env   [--node KIND | --class CLS] [--allow-planned]
                                                     shell assignments (NODE_KIND, NODE_VM, NODE_ALIAS, NODE_CERTNAME,
                                                     NODE_HOSTNAME, NODE_HOSTONLY_IP, NODE_SNAPSHOT, NODE_OS_FAMILY)
                                                     for `eval` in the shell tools

Selection: --node KIND, else (with --class) the plan row's `node` column, else P8_NODE, else `default`. A planned
node is refused unless --allow-planned (bring-up). P8_NODES overrides the inventory path (tests).
"""

from __future__ import annotations

import ipaddress
import os
import re
import shlex
import sys
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
FIELDS = ("status", "vm", "alias", "certname", "hostname", "hostonly_ip", "baseline_snapshot", "os_family", "os",
          "capabilities")
CAPABILITIES = {"server", "desktop", "kde", "gnome", "rhel-subscription", "second-node", "ad-dc", "puppet-server"}
LEGACY_VMS = {"ubuntu": "ubuntu24-puppet8-Node"}  # keeps its revert_node.sh rules (HQ 2026-11-16 item 3)
MASTER_VM = "Ubuntu24-puppet8-Master"
RESERVED_IPS = {"192.168.56.1", "192.168.56.10"}  # laptop, master
NAME = re.compile(r"[a-z][a-z0-9-]{1,30}")
ENV_KEYS = {"kind": "NODE_KIND", "vm": "NODE_VM", "alias": "NODE_ALIAS", "certname": "NODE_CERTNAME",
            "hostname": "NODE_HOSTNAME", "hostonly_ip": "NODE_HOSTONLY_IP", "baseline_snapshot": "NODE_SNAPSHOT",
            "os_family": "NODE_OS_FAMILY"}


def path() -> Path:
    return Path(os.environ.get("P8_NODES") or REPO / ".codex_state" / "lab" / "nodes.yml")


def load() -> dict:
    data = yaml.safe_load(path().read_text())
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), dict):
        raise SystemExit(f"ERROR: {path()} needs a `nodes` mapping")
    return data


def problems(data: dict) -> list[str]:
    out: list[str] = []
    nodes = data["nodes"]
    if data.get("default") not in nodes:
        out.append(f"default {data.get('default')!r} is not a node kind")
    elif nodes[data["default"]].get("status") != "active":
        out.append("the default node must be active")
    seen: dict[str, dict[str, str]] = {f: {} for f in ("vm", "alias", "certname", "hostname", "hostonly_ip")}
    for kind, n in nodes.items():
        where = f"node {kind}"
        if not NAME.fullmatch(str(kind)):
            out.append(f"{where}: kind must be a lowercase slug")
        if not isinstance(n, dict):
            out.append(f"{where}: not a mapping")
            continue
        missing = [f for f in FIELDS if f not in n]
        if missing:
            out.append(f"{where}: missing {', '.join(missing)}")
            continue
        if n["status"] not in ("active", "planned"):
            out.append(f"{where}: status must be active|planned")
        if n["status"] == "active" and not n["baseline_snapshot"]:
            out.append(f"{where}: an active node needs its baseline_snapshot")
        vm = str(n["vm"])
        if vm == MASTER_VM:
            out.append(f"{where}: the master VM is never a node")
        elif LEGACY_VMS.get(kind) != vm and not re.fullmatch(r"p8lab-[a-z0-9-]+", vm):
            out.append(f"{where}: vm {vm!r} must be named p8lab-* (only `ubuntu` keeps {LEGACY_VMS['ubuntu']})")
        try:
            ip = ipaddress.ip_address(str(n["hostonly_ip"]))
            if ip not in ipaddress.ip_network("192.168.56.0/24") or str(ip) in RESERVED_IPS:
                out.append(f"{where}: hostonly_ip {ip} must be a free address on vboxnet0 192.168.56.0/24")
        except ValueError:
            out.append(f"{where}: hostonly_ip {n['hostonly_ip']!r} is not an address")
        if n["os_family"] not in ("Debian", "RedHat"):
            out.append(f"{where}: os_family must be Debian|RedHat")
        caps = n["capabilities"]
        if not isinstance(caps, list) or not caps or not set(caps) <= CAPABILITIES:
            out.append(f"{where}: capabilities must be a non-empty subset of {sorted(CAPABILITIES)}")
        for f, owners in seen.items():
            value = str(n[f])
            if value in owners:
                out.append(f"{where}: {f} {value!r} is also node {owners[value]}'s")
            owners[value] = kind
    return out


def plan_node(cls: str) -> str:
    sys.path.insert(0, str(TOOLS.parent))
    import gen_migration_order as gen  # noqa: PLC0415
    row = gen.parse_plan().get(cls.removeprefix("puppet_infrastructure::"))
    return (getattr(row, "node", "") or "") if row is not None else ""


def select(data: dict, kind: str | None = None, cls: str | None = None, allow_planned: bool = False) -> dict:
    chosen = kind or (plan_node(cls) if cls else "") or os.environ.get("P8_NODE") or data["default"]
    if chosen not in data["nodes"]:
        raise SystemExit(f"ERROR: unknown node kind {chosen!r} (known: {', '.join(data['nodes'])})")
    node = {"kind": chosen, **data["nodes"][chosen]}
    if node["status"] != "active" and not allow_planned:
        raise SystemExit(f"ERROR: node {chosen} is {node['status']} (no verified baseline yet); not used by the engine")
    return node


def main(argv: list[str]) -> int:
    data = load()
    if argv == ["validate"]:
        found = problems(data)
        for p in found:
            print(f"INVALID nodes.yml: {p}", file=sys.stderr)
        if not found:
            print(f"VALID nodes.yml: {len(data['nodes'])} kinds, default {data['default']}")
        return 2 if found else 0
    found = problems(data)
    if found:
        raise SystemExit(f"ERROR: nodes.yml is invalid: {found[0]} (run nodes.py validate)")
    if argv == ["list"]:
        for kind, n in data["nodes"].items():
            print(f"{kind} {n['status']} {n['vm']} {n['alias']} {n['hostonly_ip']} {n['os_family']}")
        return 0
    if argv == ["kinds"]:
        print("\n".join(data["nodes"]))
        return 0
    if argv[:1] in (["get"], ["env"]):
        cmd, rest = argv[0], argv[1:]
        kind = cls = None
        allow = "--allow-planned" in rest
        rest = [a for a in rest if a != "--allow-planned"]
        if rest[:1] == ["--node"]:
            kind, rest = rest[1], rest[2:]
        elif rest[:1] == ["--class"]:
            cls, rest = rest[1], rest[2:]
        node = select(data, kind, cls, allow_planned=allow)
        if cmd == "get":
            if len(rest) != 1 or (rest[0] not in node):
                raise SystemExit(f"ERROR: get needs one field of {', '.join(node)}")
            value = node[rest[0]]
            print(" ".join(value) if isinstance(value, list) else ("" if value is None else value))
            return 0
        if rest:
            raise SystemExit("ERROR: env takes no field")
        for field, var in ENV_KEYS.items():
            print(f"{var}={shlex.quote('' if node[field] is None else str(node[field]))}")
        return 0
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
