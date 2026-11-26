import shutil
import sys
import threading
from unittest.mock import Mock

import pytest

from app.core.monitor_service import MonitorService, MonitorSession
from app.utils.command_runner import CommandCancelled, CommandError, CommandResult, CommandTimedOut

REPLY = "1 packets transmitted, 1 received, 0% packet loss\nrtt min/avg/max/mdev = 2.5/2.5/2.5/0.0 ms"
LOST = "1 packets transmitted, 0 received, 100% packet loss"


def test_interval_history_and_packet_statistics():
    service = MonitorService(Mock())
    service.runner.run.side_effect = [CommandResult((), 0, REPLY, ""), CommandResult((), 1, LOST, ""),
                                      CommandTimedOut("timeout"), CommandError("missing ping")]
    # Replace the interruptible wait with a deterministic clock.
    service.cancel.wait = Mock(return_value=False)
    service.start("localhost", 7, 10)
    service.worker.join(2)
    assert not service.running()
    assert [call.args for call in service.cancel.wait.call_args_list] == [(7,), (7,), (7,)]
    session = MonitorSession("localhost", 7)
    for expected in ["Reachable", "No reply", "Timed out", "Probe error"]:
        kind, sample = service.events.get_nowait()
        assert kind == "sample" and sample["status"] == expected and sample["timestamp"]
        session.add(sample)
    assert service.events.get_nowait() == ("finished", "missing ping")
    assert session.statistics() == dict(sent=1 + 1, received=1, loss_percent=50.0,
                                        min_ms=2.5, avg_ms=2.5, max_ms=2.5)
    assert service.runner.run.call_args.args[0] == ["ping", "-n", "-c", "1", "-W", "2", "localhost"]


def test_duplicate_start_and_cancel_in_flight():
    service = MonitorService(Mock())
    entered = threading.Event()
    def probe(*args, cancel, **kwargs):
        entered.set()
        assert cancel.wait(2)
        raise CommandCancelled("cancelled")
    service.runner.run.side_effect = probe
    service.start("localhost", 3600, 5)
    try:
        assert entered.wait(1)
        with pytest.raises(ValueError, match="already"):
            service.start("localhost", 1, 5)
    finally:
        service.stop()
        service.worker.join(1)
    assert not service.running()
    assert service.events.get_nowait() == ("finished", None)
    assert service.events.empty()


def test_stop_wakes_long_interval_and_restart():
    service = MonitorService(Mock())
    service.runner.run.return_value = CommandResult((), 0, REPLY, "")
    for _ in range(2):
        service.start("::1", 3600, 2)
        assert service.events.get(timeout=1)[0] == "sample"
        service.stop()
        service.worker.join(1)
        assert not service.running()
        assert service.events.get(timeout=1) == ("finished", None)


@pytest.mark.parametrize("target,interval", [("127.0.0.1;id", 1), ("::1", 0), ("::1", 3601), ("::1", True)])
def test_invalid_monitor_input(target, interval):
    service = MonitorService(Mock())
    with pytest.raises(ValueError):
        service.start(target, interval, 5)
    service.runner.run.assert_not_called()


@pytest.mark.skipif(sys.platform != "linux" or not shutil.which("ping"), reason="Requires Linux iputils ping")
def test_real_loopback_probe():
    service = MonitorService()
    service.start("127.0.0.1", 3600, 5)
    try:
        kind, sample = service.events.get(timeout=7)
        assert kind == "sample" and sample["status"] == "Reachable", sample
        assert sample["latency_ms"] is not None
    finally:
        service.stop()
        service.worker.join(2)
