import json
from unittest.mock import Mock, patch

import pytest

from app.core.network_utils import NetworkService, parse_interfaces, parse_nameservers
from app.utils.command_runner import CommandCancelled, CommandError, CommandResult

ADDRESSES = json.dumps([
    {"ifname": "lo", "operstate": "UNKNOWN", "addr_info": [
        {"family": "inet", "local": "127.0.0.1", "prefixlen": 8}]},
    {"ifname": "eth0", "operstate": "UP", "address": "00:11:22:33:44:55", "addr_info": [
        {"family": "inet", "local": "192.0.2.10", "prefixlen": 24},
        {"family": "inet6", "local": "2001:db8::10", "prefixlen": 64}]}])


def test_interface_addresses():
    interface = parse_interfaces(ADDRESSES)[1]
    assert interface["ipv4"] == ["192.0.2.10/24"]
    assert interface["ipv6"] == ["2001:db8::10/64"]
    assert interface["state"] == "UP"


@pytest.mark.parametrize("output", ["broken", "{}", "[1]", '[{"ifname":"eth0","addr_info":null}]'])
def test_malformed_interfaces(output):
    with pytest.raises(ValueError):
        parse_interfaces(output)


def test_nameservers():
    assert parse_nameservers("nameserver 127.0.0.53\nnameserver 2001:db8::1 # comment\nnameserver invalid") == [
        "127.0.0.53", "2001:db8::1"]
    assert parse_nameservers("Global: 1.1.1.1\nLink 2 (eth0): 2001:db8::1 1.1.1.1", True) == [
        "1.1.1.1", "2001:db8::1"]


def test_collection_and_dns_fallback(tmp_path):
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("nameserver 192.0.2.53\n")
    def run(args, **kwargs):
        if args[0] == "resolvectl":
            raise CommandError("service unavailable")
        outputs = {
            ("ip", "-j", "addr"): ADDRESSES,
            ("ip", "-j", "route"): '[{"dst":"default","gateway":"192.0.2.1","dev":"eth0"}]',
            ("ip", "-j", "-6", "route"): "[]",
            ("ip", "-s", "link"): "link statistics",
            ("ss", "-H", "-lntu"): "tcp LISTEN ...\nudp UNCONN ...\n",
        }
        return CommandResult(tuple(args), 1 if args[0] == "ping" else 0, outputs.get(tuple(args), ""), "")
    runner = Mock()
    runner.run.side_effect = run
    with patch("app.core.network_utils.psutil.net_io_counters", return_value={}):
        result = NetworkService(runner, resolv).collect()
    assert result["active_interface"] == "eth0"
    assert result["gateway"] == "192.0.2.1"
    assert result["dns_servers"] == ["192.0.2.53"]
    assert result["listening_ports"] == 2
    assert result["connectivity"] == "No ICMP reply"


def test_all_commands_unavailable(tmp_path):
    runner = Mock()
    runner.run.side_effect = CommandError("missing")
    with patch("app.core.network_utils.psutil.net_io_counters", return_value={}):
        result = NetworkService(runner, tmp_path / "absent").collect()
    assert result["interfaces"] == []
    assert result["connectivity"] == "Unknown"
    assert result["active_interface"] is None
    assert result["listening_ports"] is None
    assert result["warnings"]


def test_cancel_propagates():
    runner = Mock()
    runner.run.side_effect = CommandCancelled("cancelled")
    with pytest.raises(CommandCancelled):
        NetworkService(runner).collect()
