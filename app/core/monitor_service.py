"""Serial ICMP probes. The worker publishes plain records and never calls Tk."""
from datetime import datetime
import logging
import queue
import threading

from app.core.diagnostics_service import parse_ping
from app.utils.command_runner import CommandRunner, CommandError, CommandCancelled, CommandTimedOut
from app.utils.validators import validate_target

LOG = logging.getLogger("kalinet.monitor")


def timestamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class MonitorService:
    def __init__(self, runner=None):
        self.runner = runner or CommandRunner()
        self.events = queue.Queue()
        self.worker = None
        self.cancel = threading.Event()

    def start(self, target, interval, timeout):
        if self.running():
            raise ValueError("Monitoring is already running.")
        target = validate_target(target)
        if type(interval) is not int or not 1 <= interval <= 3600:
            raise ValueError("Interval must be from 1 to 3600 seconds.")
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise ValueError("Timeout must be from 1 to 60 seconds.")
        self.cancel.clear()
        self.worker = threading.Thread(target=self._run, args=(target, interval, timeout),
                                       name="kalinet-monitor")
        self.worker.start()

    def running(self):
        return self.worker is not None and self.worker.is_alive()

    def stop(self):
        self.cancel.set()

    def _run(self, target, interval, timeout):
        failure = None
        try:
            while not self.cancel.is_set():
                status, detail, output = "Probe error", "", ""
                try:
                    result = self.runner.run(["ping", "-n", "-c", "1", "-W", "2", target],
                                             timeout=timeout, cancel=self.cancel, accepted_codes=(0, 1))
                    output = result.stdout
                except CommandCancelled:
                    break
                except CommandError as exc:
                    detail = str(exc)
                    if isinstance(exc, CommandTimedOut):
                        status = "Timed out"
                    if exc.result:
                        output = exc.result.stdout
                    elif not isinstance(exc, CommandTimedOut):
                        failure = detail  # Missing executable or failure to start.
                stats = parse_ping(output)
                sent, received = stats.get("transmitted"), stats.get("received")
                if received is not None:
                    status = "Reachable" if received else "No reply"
                elif not detail:
                    detail = "Ping did not return packet statistics."
                self.events.put(("sample", dict(timestamp=timestamp(), status=status,
                    latency_ms=stats.get("avg_ms"), sent=sent, received=received, detail=detail)))
                if failure or self.cancel.wait(interval):
                    break
        except Exception as exc:
            LOG.exception("Monitoring failed")
            failure = str(exc)
        finally:
            self.events.put(("finished", failure))


class MonitorSession:
    def __init__(self, target, interval):
        self.target = target
        self.interval = interval
        self.started_at = timestamp()
        self.samples = []
        self.sent = self.received = self.latency_count = 0
        self.latency_sum = 0.0
        self.minimum = self.maximum = None

    def add(self, sample):
        self.samples.append(sample)
        if sample["sent"] is not None and sample["received"] is not None:
            self.sent += sample["sent"]
            self.received += sample["received"]
        latency = sample["latency_ms"]
        if latency is not None:
            self.latency_sum += latency
            self.latency_count += 1
            self.minimum = latency if self.minimum is None else min(self.minimum, latency)
            self.maximum = latency if self.maximum is None else max(self.maximum, latency)

    def statistics(self):
        return dict(sent=self.sent, received=self.received,
                    loss_percent=100 * (self.sent - self.received) / self.sent if self.sent else None,
                    min_ms=self.minimum, max_ms=self.maximum,
                    avg_ms=self.latency_sum / self.latency_count if self.latency_count else None)

    def result(self, status, error=None):
        return dict(target=self.target, interval=self.interval, started_at=self.started_at,
                    finished_at=timestamp(), status=status, error=error, statistics=self.statistics(),
                    samples=self.samples.copy())
