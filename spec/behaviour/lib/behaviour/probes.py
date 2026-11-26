"""Probe rules and verdicts.

A probe is a shell script run as root on the node (or on the peer, with `host: peer`). Read-only probes only observe;
a mutating check declares its change (`mutates`) and is judged on a separate read-only `effect`. No probe runs Puppet
or copies to another host; it names the run's other machines only through placeholders (README.md), never literally.
"""

from __future__ import annotations

import re

HOST_RULES = [
    (re.compile(r"\b(scp|sftp|rsync)\s"), "copies to/from another host"),
    (re.compile(r"\bpuppet\s+(agent|apply|resource)\b|/opt/puppetlabs/bin/puppet\b"), "runs Puppet (changes the node)"),
]
READONLY_RULES = [
    (re.compile(r"\bsystemctl\s+(start|stop|restart|reload|enable|disable|mask|unmask|kill)\b"), "changes a service"),
    (re.compile(r"\b(apt|apt-get|dpkg|dnf|yum|rpm)\s+(-\S+\s+)*(install|remove|purge|-i|-e)\b"), "changes packages"),
    (re.compile(r"(^|[\s;&|])(rm|tee|truncate|shred|useradd|userdel|groupadd|groupdel|chmod|chown)\s"),
     "changes files or accounts"),
    (re.compile(r"(?<![0-9&])>>?\s*(?!/dev/null\b|&)\S"), "redirects into a file"),
]
LOCAL_SSH = re.compile(r"(^|[\s;&|(])ssh\s")  # ssh as a command, not a path like /etc/ssh/
LOCAL_TARGET = re.compile(r"(\S+@)?(127\.0\.0\.1|localhost|::1)\b")
MUTATING_HELPER = re.compile(r"\bp8_hold\b")

# Probes that hand a value to a tool and take its verdict: a mismatch control (one value deliberately wrong, which
# must fail the same expectation after apply) shows the check discriminates.
TOOL_VERDICT = [
    (re.compile(r"\bopenssl\s+s_client\b"), "openssl s_client (TLS verdict)"),
    (re.compile(r"\bcurl\b[^\n]*(-H\s*['\"]?Host:|--resolve\b)"), "curl by host (HTTP verdict for a vhost)"),
    (re.compile(r"(^|[\s;&|(])ssh\s[^\n]*(\S+@\S+|-o\s*(Ciphers|KexAlgorithms|MACs|HostKeyAlgorithms|"
                r"PubkeyAuthentication|PasswordAuthentication|PreferredAuthentications)=)"), "ssh login/negotiation"),
    (re.compile(r"\b(su|runuser)\s+-|\bsudo\s+-u\s"), "a login as another user"),
    (re.compile(r"\b(mysql|psql|smbclient|ldapsearch)\b[^\n]*\s-[uUD]\s*\S"), "a client login with a user"),
]


def tool_verdict(probe: str) -> str | None:
    return next((why for pat, why in TOOL_VERDICT if pat.search(probe)), None)


def probe_problems(probe: str, mutating: bool = False) -> list[str]:
    """What a probe (or a mutating check's action, with `mutating`) may not do."""
    rules = HOST_RULES if mutating else HOST_RULES + READONLY_RULES
    out = [f"probe {why}: {pat.pattern}" for pat, why in rules if pat.search(probe)]
    if not mutating and MUTATING_HELPER.search(probe):
        out.append("probe calls a mutating helper (p8_hold), which belongs in a check's action")
    if LOCAL_SSH.search(probe) and not LOCAL_TARGET.search(probe):
        out.append("probe uses ssh to a host other than the node itself (127.0.0.1/localhost)")
    return out


def meets(check: dict, rc: int, out: str) -> bool:
    """Whether a probe's exit code and output meet the check's (rendered) expectation."""
    exp = check.get("expect") or {}
    passed = rc == exp.get("rc", 0)
    if passed and "stdout" in exp:
        passed = re.search(exp["stdout"], out, re.M) is not None
    if passed and "stdout_not" in exp:
        passed = re.search(exp["stdout_not"], out, re.M) is None
    return passed
