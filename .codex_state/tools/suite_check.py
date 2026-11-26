#!/usr/bin/env python3
"""The public behaviour suite stays free of the lab and the engine (HQ review of design note F, rulings 2 and 8).

  suite_check.py [--staged | <path>...]   (no argument: every file of spec/behaviour/)

Refuses, in any file under spec/behaviour/:
  - a lab value: a node's name, alias, VM, certname, address or baseline snapshot (nodes.yml), the master's name or
    address, the controller's address, the lab networks (192.168.56.0/24, VirtualBox NAT 10.0.2.0/24);
  - a reference to the engine: `.codex_state`, the advisor, Codex, or one of the engine's files by name (the sets cite
    them only as {{SITE:...}} placeholders).
And in a params fixture (spec/behaviour/fixtures/params/**.json), anything that is not plainly fake (ruling 2: the
one exception to "never commit params", real or lab-specific values stay outside git):
  - an IPv4 address outside RFC 5737, loopback, 0.0.0.0 and private ranges (a public host is real);
  - a domain name outside the reserved ones (.invalid, .test, .example, .localhost, example.com/net/org);
  - an e-mail address outside those domains;
  - private key material, or an opaque base64/hex value of 32 or more characters (a hash, a digest, a token) unless it is
    an SSH public key body (AAAA...) or carries `p8test`.
Exit 0 clean, 1 with findings (one line each: path: problem).
"""

from __future__ import annotations

import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SUITE = REPO / "spec" / "behaviour"
sys.path.insert(0, str(TOOLS))

ENGINE_WORDS = re.compile(r"\.codex_state|\b[Cc]odex\b|\badvisor\b")
LAB_NETS = [ipaddress.IPv4Network("192.168.56.0/24"), ipaddress.IPv4Network("10.0.2.0/24")]
FAKE_NETS = [ipaddress.IPv4Network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "127.0.0.0/8",
                                                "0.0.0.0/32", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
RESERVED = re.compile(r"(^|\.)(invalid|test|example|localhost)$|(^|\.)example\.(com|net|org)$", re.I)
ADDR = re.compile(r"(?<![\d.])(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?![\d.])")
DOMAIN = re.compile(r"(?<![\w.@-])((?:[a-z0-9-]+\.)+([a-z]{2,24}))(?![\w-])", re.I)
EMAIL = re.compile(r"[\w.+-]+@([\w-]+(?:\.[\w-]+)+)")
OPAQUE = re.compile(r"[A-Za-z0-9+/=]{32,}")  # base64 or hex: a hash, a digest or a token
FILE_SUFFIX = re.compile(r"\.(sh|py|pp|erb|epp|json|ya?ml|md|txt|conf|cfg|pem|key|crt|log|service|timer|j2)$", re.I)


def lab_values() -> list[str]:
    import behaviour_move as bm  # noqa: PLC0415
    import nodes  # noqa: PLC0415
    out = {v for k, v in bm.LAB.items() if k not in ("LOCALDIR", "NODE_NETWORK", "NODE_PRIMARY_ADDR")}
    for n in nodes.load()["nodes"].values():
        out |= {str(n.get(f)) for f in ("vm", "alias", "certname", "hostname", "hostonly_ip", "baseline_snapshot")
                if n.get(f)}
    return sorted(out, key=len, reverse=True)


def engine_files() -> list[str]:
    import behaviour_move as bm  # noqa: PLC0415
    return sorted(bm.SITE, key=len, reverse=True)


def token(value: str) -> re.Pattern:
    """The value as a whole token; a regex escape such as \\A before it counts as a token start."""
    return re.compile(rf"(?:(?<=\\[A-Za-z])|(?<![\w.-])){re.escape(value)}(?![\w-]|\.\d)")


def text_problems(text: str, lab: list[str], files: list[str]) -> list[str]:
    out = []
    for v in lab:
        if token(v).search(text) or token(v.replace(".", "\\.")).search(text):
            out.append(f"names a lab value ({v})")
    for m in ADDR.finditer(text):
        try:
            ip = ipaddress.IPv4Address(m.group(1))
        except ValueError:
            continue
        if any(ip in net for net in LAB_NETS):
            out.append(f"names a lab address ({ip})")
    m = ENGINE_WORDS.search(text)
    if m:
        out.append(f"refers to the engine ({m.group(0)})")
    for f in files:
        if token(f).search(text):
            out.append(f"names an engine file ({f}); cite it as a {{{{SITE:...}}}} placeholder")
    return sorted(set(out))


def strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)
    elif isinstance(obj, str):
        yield obj


def netmask(text: str) -> bool:
    try:
        ipaddress.IPv4Network(f"0.0.0.0/{text}")
        return True
    except ValueError:
        return False


def fake_problems(value: str) -> list[str]:
    out = []
    if "{{" in value:
        return out  # a placeholder: the run supplies the value
    for m in ADDR.finditer(value):
        try:
            ip = ipaddress.IPv4Address(m.group(1))
        except ValueError:
            continue
        if not any(ip in net for net in FAKE_NETS) and not netmask(str(ip)):
            out.append(f"a public address ({ip}) is a real host")
    for m in EMAIL.finditer(value):
        if not RESERVED.search(m.group(1)):
            out.append(f"an e-mail address at a real domain ({m.group(0)})")
    for m in DOMAIN.finditer("" if value.startswith("$") else value):  # a crypt hash ($6$...) is no host
        name = m.group(1)
        if ADDR.fullmatch(name) or FILE_SUFFIX.search(name) or name.lower().startswith("p8test"):
            continue
        if not RESERVED.search(name):
            out.append(f"a domain name outside the reserved ones ({name})")
    if "PRIVATE KEY" in value:
        out.append("private key material")
    for m in OPAQUE.finditer(value):
        blob = m.group(0)
        if blob.startswith("AAAA") or "p8test" in value:
            continue
        out.append(f"an opaque value ({blob[:12]}...) that may be a real hash or token")
    return out


def check_file(path: Path, lab: list[str], files: list[str]) -> list[str]:
    rel = path.relative_to(REPO) if path.is_relative_to(REPO) else path
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    found = [f"{rel}: {p}" for p in text_problems(text, lab, files)]
    params = SUITE / "fixtures" / "params"
    if path.suffix == ".json" and path.is_relative_to(params):
        try:
            data = json.loads(text)
        except ValueError as err:
            return found + [f"{rel}: not JSON ({err})"]
        found += [f"{rel}: {p}" for s in strings(data) for p in fake_problems(s)]
    return sorted(set(found))


def staged() -> list[Path]:
    names = subprocess.run(["git", "-C", str(REPO), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                           capture_output=True, text=True, check=True).stdout.split()
    return [REPO / n for n in names if n.startswith("spec/behaviour/")]


def main(argv: list[str]) -> int:
    if argv == ["--staged"]:
        paths = staged()
    elif argv:
        paths = [Path(a).resolve() for a in argv]
    else:
        paths = sorted(p for p in SUITE.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    lab, files = lab_values(), engine_files()
    found = [p for path in paths if path.is_file() for p in check_file(path, lab, files)]
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
