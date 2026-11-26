"""Placeholders in check sets and fixtures.

A set names the machines and site paths of a run through placeholders, never literally, so it runs on any test nodes:

  {{NAME}}        the value of NAME for this run
  {{NAME|re}}     the value escaped for a regular expression (the dots and other operators, not `-`)
  {{NAME+N}}      an IPv4 address value with N added to its last number (an extra address on the same network)
  {{NAME:arg}}    a family of values (for example {{NODE:rhel9}}, the name of the run's rhel9 node)

The runner supplies the values (README.md lists them). A placeholder with no value is an error, never left in a
script that runs.
"""

from __future__ import annotations

import ipaddress
import re

PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)(?::([a-z0-9][a-z0-9-]*))?(?:\+(\d{1,3}))?(\|re)?\}\}")
RE_SPECIAL = set(".^$*+?()[]{}|\\")


def re_escape(value: str) -> str:
    """Escape a value for a regular expression the way the sets write it: operators only, `-` stays as it is."""
    return "".join("\\" + ch if ch in RE_SPECIAL else ch for ch in value)


def key(name: str, arg: str | None) -> str:
    return f"{name}:{arg}" if arg else name


def names(text: str) -> set[str]:
    """The values a text needs (`NAME` or `NAME:arg`)."""
    return {key(m.group(1), m.group(2)) for m in PLACEHOLDER.finditer(text)}


def render(text: str, values: dict[str, str]) -> str:
    """The text with every placeholder replaced; KeyError names a placeholder without a value."""
    def one(m: re.Match) -> str:
        k = key(m.group(1), m.group(2))
        if k not in values:
            raise KeyError(k)
        value = str(values[k])
        if m.group(3):
            addr = ipaddress.IPv4Address(value)
            last = int(str(addr).rsplit(".", 1)[1]) + int(m.group(3))
            if last > 255:
                raise ValueError(f"{{{{{k}+{m.group(3)}}}}}: {value} + {m.group(3)} leaves the network")
            value = str(addr).rsplit(".", 1)[0] + f".{last}"
        return re_escape(value) if m.group(4) else value
    return PLACEHOLDER.sub(one, text)


def render_obj(obj, values: dict[str, str], only=None):
    """A copy of a YAML/JSON structure with its strings rendered. `only` (a set of mapping keys) limits rendering to
    strings found under those keys; strings elsewhere are kept as they are."""
    def walk(o, under: str | None):
        if isinstance(o, dict):
            return {k: walk(v, k if only is None or k in only else under) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v, under) for v in o]
        if isinstance(o, str) and (only is None or under in only):
            return render(o, values)
        return o
    return walk(obj, None)


def needed(obj, only=None) -> set[str]:
    """Every placeholder a structure uses (under `only` keys when given)."""
    found: set[str] = set()

    def walk(o, under: str | None):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, k if only is None or k in only else under)
        elif isinstance(o, list):
            for v in o:
                walk(v, under)
        elif isinstance(o, str) and (only is None or under in only):
            found.update(names(o))
    walk(obj, None)
    return found
