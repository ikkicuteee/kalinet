from unittest.mock import Mock

import pytest

from app.core.diagnostics_service import DiagnosticsService, parse_ping, parse_traceroute, parse_dns, summarize
from app.utils.command_runner import CommandCancelled, CommandError, CommandResult

PING = "4 packets transmitted, 3 received, 25% packet loss, time 3003ms\nrtt min/avg/max/mdev = 1.0/2.0/3.0/0.5 ms\n"
DNS = ";; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 1\n;; ANSWER SECTION:\nexample.com. 60 IN A 192.0.2.1\n\n;; Query time: 1 msec\n"


def test_ping_statistics():
    assert parse_ping(PING) == dict(transmitted=4, received=3, loss_percent=25.0,
                                    min_ms=1.0, avg_ms=2.0, max_ms=3.0, mdev_ms=0.5)


def test_unreachable_ping():
    stats = parse_ping("4 packets transmitted, 0 received, +4 errors, 100% packet loss, time 3000ms")
    assert stats == dict(transmitted=4, received=0, loss_percent=100.0)


def test_traceroute_timeouts_and_hops():
    hops = parse_traceroute("traceroute to example.com\n 1 192.0.2.1 0.123 ms\n 2 *\n 3 192.0.2.3 2.45 ms !H\n")
    assert hops[0]["latencies_ms"] == [0.123]
    assert hops[1]["timeouts"] == 1
    assert "!H" in hops[2]["details"]


def test_dns_answers_only():
    result = parse_dns(DNS + ";; AUTHORITY SECTION:\nexample.com. 60 IN NS ns.example.com.\n")
    assert result["status"] == "NOERROR"
    assert result["records"] == [dict(name="example.com.", ttl="60", **{"class": "IN"}, type="A", value="192.0.2.1")]


@pytest.mark.parametrize("status", ["NXDOMAIN", "SERVFAIL", "REFUSED"])
def test_dns_error_with_zero_exit(status):
    runner = Mock()
    runner.run.return_value = CommandResult((), 0, f";; ->>HEADER<<- status: {status}, id: 1", "")
    result = DiagnosticsService(runner).run("DNS Lookup", "example.com")
    assert status in result["error"]


def test_nodata_is_not_nxdomain():
    runner = Mock()
    runner.run.return_value = CommandResult((), 0, ";; ->>HEADER<<- status: NOERROR, id: 1", "")
    result = DiagnosticsService(runner).run("DNS Lookup", "example.com")
    assert result["error"] is None
    assert "NODATA" in summarize(result)


@pytest.mark.parametrize("tool,target,options,expected", [
    ("Ping", "::1", {"count": 2}, ["ping", "-n", "-c", "2", "-W", "2", "::1"]),
    ("Traceroute", "::1", {}, ["traceroute", "-n", "-m", "30", "-q", "1", "-w", "1", "-6", "::1"]),
    ("DNS Lookup", "example.com", {"record_type": "AAAA"}, ["dig", "+time=2", "+tries=1", "example.com", "AAAA"]),
])
def test_command_arguments(tool, target, options, expected):
    runner = Mock()
    runner.run.return_value = CommandResult((), 0, "", "")
    DiagnosticsService(runner).run(tool, target, **options)
    assert runner.run.call_args.args[0] == expected
    assert runner.run.call_args.kwargs["timeout"] == 10


@pytest.mark.parametrize("tool", ["Ping", "Traceroute", "DNS Lookup"])
def test_injection_rejected_before_execution(tool):
    runner = Mock()
    with pytest.raises(ValueError):
        DiagnosticsService(runner).run(tool, "example.com; whoami")
    runner.run.assert_not_called()


@pytest.mark.parametrize("error", [CommandError("ping timed out"), CommandError("Required utility missing"),
                                   CommandCancelled("Operation cancelled")])
def test_command_errors_are_reportable(error):
    runner = Mock()
    runner.run.side_effect = error
    result = DiagnosticsService(runner).run("Ping", "localhost")
    assert result["error"] == str(error)
    assert result["stdout"] == ""


def test_timeout_preserves_partial_hops():
    runner = Mock()
    runner.run.side_effect = CommandError("traceroute timed out", CommandResult((), -9, " 1 192.0.2.1 1.5 ms\n", "partial"))
    result = DiagnosticsService(runner).run("Traceroute", "example.com")
    assert result["parsed"][0]["hop"] == 1
    assert result["stderr"] == "partial"
    assert "timed out" in summarize(result)


def test_ping_failure_preserves_statistics():
    runner = Mock()
    runner.run.side_effect = CommandError("ping failed", CommandResult((), 1, "4 packets transmitted, 0 received, 100% packet loss", ""))
    result = DiagnosticsService(runner).run("Ping", "192.0.2.1")
    assert result["parsed"]["loss_percent"] == 100


@pytest.mark.parametrize("tool", ["Ping", "Traceroute", "DNS Lookup"])
def test_malformed_output_not_success(tool):
    runner = Mock()
    runner.run.return_value = CommandResult((), 0, "nonsense", "")
    assert DiagnosticsService(runner).run(tool, "localhost")["error"]
