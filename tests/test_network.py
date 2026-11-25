import json
from unittest.mock import Mock, patch

import pytest

from app.core.network_utils import NetworkService, parse_interfaces, parse_nameservers, count_listening_sockets
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
            ("ss", "-H", "-lntu"): "tcp LISTEN 0 128 127.0.0.1:22 0.0.0.0:*\nudp UNCONN 0 0 *:5353 *:*\n",
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


@pytest.mark.parametrize("header", ["", "Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port\n"])
def test_ss_matches_headerless_and_tuln(header):
    rows = "udp UNCONN 0 0 0.0.0.0:5353 0.0.0.0:*\ntcp LISTEN 0 128 [::]:22 [::]:*\n"
    assert count_listening_sockets(header + rows) == 2


@pytest.mark.parametrize("output", ["", "\n", "Netid State Recv-Q Send-Q Local Address:Port Peer Address:Port\n"])
def test_ss_zero_is_valid(output):
    assert count_listening_sockets(output) == 0


def test_ss_malformed_is_not_zero():
    with pytest.raises(ValueError, match="Unrecognized"):
        count_listening_sockets("unexpected text")


def test_dns_missing_optional_providers_is_normal(tmp_path):
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("nameserver 192.0.2.53\n")
    runner = Mock()
    with patch("app.core.network_utils.shutil.which", return_value=None):
        servers, sources, notes = NetworkService(runner, resolv).detect_dns(10, None)
    assert servers == ["192.0.2.53"]
    assert notes == []
    assert sources == {str(resolv): servers}
    runner.run.assert_not_called()


def test_networkmanager_and_stub_sources(tmp_path):
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("nameserver 127.0.0.53\n")
    runner = Mock()
    runner.run.return_value = CommandResult((), 0, "IP4.DNS[1]:192.0.2.53\nIP6.DNS[1]:2001:db8::53\n", "")
    with patch("app.core.network_utils.shutil.which", side_effect=lambda name: name if name == "nmcli" else None):
        servers, sources, notes = NetworkService(runner, resolv).detect_dns(10, None)
    assert servers == ["127.0.0.53", "192.0.2.53", "2001:db8::53"]
    assert len(sources) == 2
    assert notes == []


def test_inactive_provider_preserves_resolver_file(tmp_path):
    resolv = tmp_path / "resolv.conf"
    resolv.write_text("nameserver 192.0.2.53\n")
    runner = Mock()
    runner.run.side_effect = CommandError("service inactive")
    with patch("app.core.network_utils.shutil.which", return_value="available"):
        servers, _, notes = NetworkService(runner, resolv).detect_dns(10, None)
    assert servers == ["192.0.2.53"]
    assert notes
