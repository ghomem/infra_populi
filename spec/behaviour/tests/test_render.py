import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from behaviour import probes, render  # noqa: E402

VALUES = {"NODE_ADDR": "198.51.100.20", "SERVER_NAME": "server.example.invalid", "NODE:rhel9": "rhel-node",
          "LOCALDIR": "/opt/site"}


def test_a_placeholder_is_replaced_by_its_value():
    assert render.render("ping -c1 {{NODE_ADDR}}; ls {{LOCALDIR}}/bin", VALUES) == "ping -c1 198.51.100.20; ls /opt/site/bin"


def test_the_re_form_escapes_operators_but_not_hyphens():
    assert render.render(r"\A{{SERVER_NAME|re}}\n", VALUES) == r"\Aserver\.example\.invalid\n"
    assert render.re_escape("p8-x.y") == r"p8-x\.y"


def test_the_plus_form_adds_to_the_last_number_of_an_address():
    assert render.render("{{NODE_ADDR+100}}", VALUES) == "198.51.100.120"
    with pytest.raises(ValueError):
        render.render("{{NODE_ADDR+250}}", VALUES)


def test_a_family_placeholder_takes_its_argument():
    assert render.render("on {{NODE:rhel9}}", VALUES) == "on rhel-node"


def test_a_placeholder_without_a_value_is_an_error_never_left_in_a_script():
    with pytest.raises(KeyError):
        render.render("{{PEER_ADDR}}", VALUES)


def test_docker_style_templates_are_not_placeholders():
    text = "docker inspect -f '{{.State.Running}} {{json .Config.Cmd}}' x"
    assert render.names(text) == set()
    assert render.render(text, {}) == text


def test_render_obj_limits_rendering_to_the_named_keys():
    data = {"what": "{{NODE_ADDR}} in prose", "checks": [{"probe": "ping {{NODE_ADDR}}",
                                                           "expect": {"stdout": "{{SERVER_NAME|re}}"}}]}
    out = render.render_obj(data, VALUES, only={"probe", "stdout"})
    assert out["what"] == "{{NODE_ADDR}} in prose"
    assert out["checks"][0]["probe"] == "ping 198.51.100.20"
    assert out["checks"][0]["expect"]["stdout"] == r"server\.example\.invalid"
    assert render.needed(data, only={"probe"}) == {"NODE_ADDR"}


@pytest.mark.parametrize("probe, mutating, problem", [
    ("puppet agent -t", False, "runs Puppet"),
    ("rsync -a x y:", False, "copies"),
    ("systemctl restart nginx", False, "changes a service"),
    ("systemctl restart nginx", True, None),
    ("echo x > /etc/x", False, "redirects into a file"),
    ("ssh root@198.51.100.1 true", False, "ssh to a host other than the node"),
    ("ssh -o BatchMode=yes 127.0.0.1 true", False, None),
    ("p8_hold 1 2", False, "mutating helper"),
    ("iptables -S | grep 10.255.255.2", False, None),
])
def test_probe_rules(probe, mutating, problem):
    found = probes.probe_problems(probe, mutating)
    assert (problem is None and not found) or (problem and any(problem in p for p in found)), found


def test_meets_checks_the_exit_code_and_both_patterns():
    check = {"expect": {"rc": 0, "stdout": r"^active$", "stdout_not": "failed"}}
    assert probes.meets(check, 0, "active\n")
    assert not probes.meets(check, 1, "active\n")
    assert not probes.meets(check, 0, "active\nfailed\n")
