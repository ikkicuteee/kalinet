import json
import threading
from unittest.mock import Mock, patch

import pytest

from app.core.scanner_service import ScannerService, is_local_target, parse_nmap_xml
from app.utils.command_runner import CommandCancelled, CommandResult, CommandTimedOut
from app.utils.validators import validate_ports

XML = '''<?xml version="1.0"?>
<!DOCTYPE nmaprun>
<nmaprun><host><status state="up"/><ports>
<extraports state="closed" count="98"/>
<port protocol="tcp" portid="22"><state state="open"/><service name="ssh" product="OpenSSH" version="9.0" extrainfo="protocol 2.0"/></port>
<port protocol="tcp" portid="80"><state state="filtered"/></port>
</ports></host><runstats><finished exit="success"/></runstats></nmaprun>'''


def runner_for(output=XML):
    runner = Mock()
    runner.run.return_value = CommandResult((), 0, output, "")
    return runner


@pytest.mark.parametrize("value", ["22", "1,65535", "80, 443", "8000-8010", "1-65535"])
def test_valid_ports(value):
    assert validate_ports(value)


@pytest.mark.parametrize("value", ["", "0", "65536", "-1", "80,", "80,,443", "9-2", "1-65536",
                                    "80;id", "--top-ports 1", "T:80", "1.5", "*", "80\n22", "８０"])
def test_invalid_ports(value):
    with pytest.raises(ValueError):
        validate_ports(value)


@pytest.mark.parametrize("target", ["127.0.0.1", "127.0.0.2", "::1", "localhost", "localhost."])
def test_loopback(target):
    assert is_local_target(target)


@pytest.mark.parametrize("target", ["192.0.2.1", "2001:db8::1", "example.com", "localhost.example"])
def test_remote_authorization_required(target):
    runner = runner_for()
    with pytest.raises(ValueError, match="authorization"):
        ScannerService(runner).scan(target)
    runner.run.assert_not_called()


def test_xml_ports_version_and_grouped_states():
    result = parse_nmap_xml(XML)
    assert result["open_ports"] == 1
    assert result["ports"][0]["version"] == "OpenSSH 9.0 protocol 2.0"
    assert result["ports"][1]["service"] == ""
    assert result["grouped_ports"] == [{"state": "closed", "count": 98}]


@pytest.mark.parametrize("xml", ["", "<nmaprun>", "<other/>", "<nmaprun/>",
    '<nmaprun><host/><host/><runstats><finished exit="success"/></runstats></nmaprun>',
    '<!DOCTYPE nmaprun [<!ENTITY x "danger">]><nmaprun>&x;</nmaprun>',
    '<!DOCTYPE nmaprun [<!ENTITY x SYSTEM "file:///etc/passwd">]><nmaprun>&x;</nmaprun>',
    XML.replace('portid="22"', 'portid="65536"')])
def test_invalid_or_unsafe_xml(xml):
    with pytest.raises(ValueError):
        parse_nmap_xml(xml)


def test_empty_completed_scan():
    xml = '<nmaprun><runstats><finished exit="success"/></runstats></nmaprun>'
    result = ScannerService(runner_for(xml)).scan("127.0.0.1")
    assert result["status"] == "Completed"
    assert result["open_ports"] == 0
    assert result["ports"] == []


@pytest.mark.parametrize("mode,ports,flag", [("Quick", "", "-F"), ("Standard", "", None), ("Custom TCP", "80,443", "-p")])
def test_unprivileged_command_modes(mode, ports, flag):
    runner = runner_for()
    result = ScannerService(runner).scan("::1", mode=mode, ports=ports, service_detection=True)
    assert result["status"] == "Completed"
    args = runner.run.call_args.args[0]
    assert args[:7] == ["nmap", "--unprivileged", "-sT", "-Pn", "-n", "-oX", "-"]
    assert "-6" in args and "-sV" in args and args[-1] == "::1"
    if flag:
        assert flag in args
    else:
        assert "-F" not in args and "-p" not in args


def test_hostname_pinned_to_one_address():
    runner = runner_for()
    runner.run.side_effect = [CommandResult((), 0, json.dumps(["2001:db8::1", "192.0.2.1", "192.0.2.2"]), ""),
                              CommandResult((), 0, XML, "")]
    result = ScannerService(runner).scan("lab.example", authorized=True)
    assert result["resolved_target"] == "192.0.2.1"
    assert runner.run.call_args.args[0][-1] == "192.0.2.1"
    assert "lab.example" not in runner.run.call_args.args[0]


def test_missing_nmap():
    with patch("app.utils.command_runner.shutil.which", return_value=None):
        result = ScannerService().scan("127.0.0.1")
    assert result["status"] == "Failed"
    assert "nmap" in result["error"] and "missing" in result["error"]
    assert result["open_ports"] is None


@pytest.mark.parametrize("exception,status", [(CommandCancelled, "Cancelled"), (CommandTimedOut, "Timed out")])
def test_interruption_retains_raw_output_not_complete_results(exception, status):
    runner = runner_for()
    runner.run.side_effect = exception("interrupted", CommandResult((), -9, "<nmaprun>", "details"))
    result = ScannerService(runner).scan("127.0.0.1")
    assert result["status"] == status
    assert result["stdout"] == "<nmaprun>"
    assert result["open_ports"] is None
    assert result["ports"] == []


def test_cancel_before_start():
    runner = runner_for()
    cancel = threading.Event()
    cancel.set()
    assert ScannerService(runner).scan("localhost", cancel=cancel)["status"] == "Cancelled"
    runner.run.assert_not_called()


def test_service_prevents_concurrent_scans():
    service = ScannerService(runner_for())
    service._lock.acquire()
    try:
        with pytest.raises(ValueError, match="already running"):
            service.scan("127.0.0.1")
    finally:
        service._lock.release()


def test_numeric_host_range_rejected():
    runner = runner_for()
    with pytest.raises(ValueError, match="ranges"):
        ScannerService(runner).scan("192.0.2.1-10", authorized=True)
    runner.run.assert_not_called()


@pytest.mark.parametrize("target", ["0.0.0.0", "::", "224.0.0.1", "255.255.255.255"])
def test_nonunicast_rejected(target):
    runner = runner_for()
    assert ScannerService(runner).scan(target, authorized=True)["status"] == "Failed"
    runner.run.assert_not_called()
