"""Tests for probe_helpers.sh (HQ batch-12 ruling 6): each helper runs here in bash against local listeners, files
and stubs, never against the lab."""
import http.server
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

HELPERS = Path(__file__).resolve().parents[1] / "probe_helpers.sh"


def sh(script: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", f"source {HELPERS}\n{script}"], capture_output=True, text=True,
                          env={**os.environ, **(env or {})}, timeout=60)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def listener():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(16)
    conns = []
    stop = threading.Event()

    def accept():
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                conns.append(srv.accept()[0])
            except OSError:
                pass
    t = threading.Thread(target=accept, daemon=True)
    t.start()
    yield srv.getsockname()[1]
    stop.set()
    t.join()
    for c in conns:
        c.close()
    srv.close()


def test_sourcing_prints_nothing():
    r = sh("true")
    assert (r.returncode, r.stdout, r.stderr) == (0, "", "")


def test_count_sums_files_and_reads_stdin_and_is_zero_without_matches(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("x 1\ny\nx 2\n")
    b.write_text("x 3\n")
    r = sh(f"p8_count '^x' {a} {b}; echo rc=$?; p8_count '^z' {a}; echo rc=$?; printf 'x\\nx\\n' | p8_count x; "
           f"p8_count x {tmp_path}/missing; echo rc=$?")
    assert r.stdout == "3\nrc=0\n0\nrc=0\n2\n0\nrc=0\n"


def test_listening_tcp_open_and_closed(listener):
    closed = free_port()
    r = sh(f"p8_listening {listener}; p8_tcp 127.0.0.1 {listener}; p8_tcp 127.0.0.1 {closed} 1; echo rc=$?; "
           f"p8_listening {closed} | wc -l")
    assert r.stdout == f"127.0.0.1:{listener}\nopen\nclosed\nrc=0\n0\n"


def test_tcp_binds_the_source_address(listener):
    r = sh(f"p8_tcp 127.0.0.1 {listener} 2 127.0.0.1; p8_tcp 127.0.0.1 {listener} 2 192.0.2.1")
    assert r.stdout == "open\nclosed\n"


def test_http_code_and_no_answer(tmp_path):
    (tmp_path / "index.html").write_text("p8test\n")
    handler = lambda *a: http.server.SimpleHTTPRequestHandler(*a, directory=str(tmp_path))  # noqa: E731
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    srv.RequestHandlerClass.log_message = lambda *a: None
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        r = sh(f"p8_http http://127.0.0.1:{port}/; p8_http http://127.0.0.1:{port}/missing; "
               f"p8_http http://127.0.0.1:{free_port()}/; echo rc=$?; "
               f"p8_http http://p8test.invalid:{port}/ --resolve p8test.invalid:{port}:127.0.0.1")
    finally:
        srv.shutdown()
    assert r.stdout == "200\n404\n000\nrc=0\n200\n"


def test_service_states_from_systemctl(tmp_path):
    stub = tmp_path / "systemctl"
    stub.write_text("#!/bin/sh\ncase \"$1 $2\" in\n  'is-active nginx') echo active ;;\n  'is-enabled nginx') echo enabled ;;\n"
                    "  is-active*) echo inactive; exit 3 ;;\n  *) echo 'Failed to get unit file state' >&2; exit 1 ;;\nesac\n")
    stub.chmod(0o755)
    r = sh("p8_service nginx; p8_service p8test-none; echo rc=$?", env={"PATH": f"{tmp_path}:{os.environ['PATH']}"})
    assert r.stdout == "active enabled\ninactive absent\nrc=0\n"


def test_digest_owner_mode_and_hash(tmp_path):
    f = tmp_path / "f"
    f.write_text("p8test\n")
    f.chmod(0o640)
    r = sh(f"p8_digest {f} {tmp_path}/missing")
    import hashlib
    import pwd
    import grp
    st = f.stat()
    owner = f"{pwd.getpwuid(st.st_uid).pw_name}:{grp.getgrgid(st.st_gid).gr_name}"
    digest = hashlib.sha256(b"p8test\n").hexdigest()
    assert r.stdout == f"{f} {owner} 640 {digest}\n{tmp_path}/missing absent\n"


def test_rc_prints_the_status_line_and_exit_code():
    r = sh("p8_rc sh -c 'echo \"WARNING - x | perf=1\"; echo more; exit 1'; echo after=$?; p8_rc true")
    assert r.stdout == "WARNING - x | perf=1\nrc=1\nafter=0\n\nrc=0\n"


@pytest.mark.skipif(shutil.which("openssl") is None, reason="needs openssl")
def test_tls_accepts_the_served_version_and_refuses_the_other(tmp_path):
    key, crt = tmp_path / "k.pem", tmp_path / "c.pem"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt,
                    "-days", "1", "-subj", "/CN=p8test.invalid"], check=True, capture_output=True)
    port = free_port()
    srv = subprocess.Popen(["openssl", "s_server", "-accept", f"127.0.0.1:{port}", "-cert", crt, "-key", key,
                            "-tls1_3", "-www", "-quiet"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            if sh(f"p8_tcp 127.0.0.1 {port} 1").stdout == "open\n":
                break
            time.sleep(0.1)
        r = sh(f"p8_tls 127.0.0.1 {port} p8test.invalid tls1_3; p8_tls 127.0.0.1 {port} p8test.invalid tls1_2; "
               f"p8_tls 127.0.0.1 {free_port()} p8test.invalid tls1_3")
    finally:
        srv.terminate()
        srv.wait()
    assert r.stdout == "accepted\nrefused\nrefused\n"


def test_hold_returns_at_once_and_ends_the_connection_after_its_seconds(listener):
    start = time.monotonic()
    r = sh(f"p8_hold 127.0.0.1 {listener} 3; echo rc=$?")
    assert r.stdout == "rc=0\n" and time.monotonic() - start < 2
    time.sleep(1)
    assert sh(f"p8_established 127.0.0.1 {listener}").stdout == "1\n"
    time.sleep(3)
    assert sh(f"p8_established 127.0.0.1 {listener}").stdout == "0\n"
