"""Real Tk event-loop tests with mocked services; skip if no desktop is available."""
import gc
import threading
import time
import tkinter as tk
from unittest.mock import Mock

import pytest

from app.core.config_service import DEFAULTS
from app.core.diagnostics_service import DiagnosticsService
from app.gui.main_window import MainWindow
from app.utils.command_runner import CommandResult


@pytest.fixture
def window(monkeypatch, tmp_path):
    # Collect cyclic references from earlier Tk roots on the GUI thread.
    gc.collect()
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("app.gui.main_window.ConfigService.load", lambda self: dict(DEFAULTS))
    monkeypatch.setattr(MainWindow, "refresh", lambda self: None)
    try:
        probe = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Desktop unavailable: {exc}")
    probe.destroy()
    app = MainWindow()
    app.withdraw()
    yield app
    def exists():
        try:
            return app.winfo_exists()
        except tk.TclError:
            return False
    if exists():
        app.close()
        deadline = time.monotonic() + 2
        while exists() and time.monotonic() < deadline:
            app.update()
            time.sleep(.01)
    del app
    gc.collect()


def pump_until(window, predicate):
    deadline = time.monotonic() + 3
    while not predicate() and time.monotonic() < deadline:
        window.update()
        time.sleep(.01)
    assert predicate()


def test_diagnostics_updates_and_dashboard_timestamp(window):
    page = window.pages["Network Diagnostics"]
    runner = Mock()
    runner.run.return_value = CommandResult((), 0,
        "1 packets transmitted, 1 received, 0% packet loss\nrtt min/avg/max/mdev = 1/1/1/0 ms", "")
    page.service = DiagnosticsService(runner)
    page.views["Ping"]["count"].set("1")
    page.start("Ping")
    pump_until(window, lambda: page.active is None)
    assert "Received: 1" in page.views["Ping"]["summary"].get("1.0", "end")
    assert "ping -n" in page.views["Ping"]["raw"].get("1.0", "end")
    assert window.pages["Dashboard"].last_diagnostic != "Not run"


def test_invalid_input_does_not_start_worker(window):
    page = window.pages["Network Diagnostics"]
    page.views["Ping"]["target"].set("localhost; id")
    page.start("Ping")
    assert page.worker is None
    assert "Invalid input" in page.views["Ping"]["status"].cget("text")


def test_navigation_and_stop_while_worker_waits(window):
    page = window.pages["Network Diagnostics"]
    started = threading.Event()
    def run(**kwargs):
        started.set()
        assert kwargs["cancel"].wait(2)
        return dict(tool="Ping", target="localhost", args=["ping", "localhost"],
                    stdout="", stderr="", parsed={}, error="Operation cancelled.",
                    returncode=None, finished_at="test timestamp")
    page.service.run = run
    page.start("Ping")
    pump_until(window, started.is_set)
    original = page.worker
    page.start("DNS Lookup")
    assert page.worker is original
    window.show_page("Network Information")
    window.update()
    assert window.page_title.cget("text") == "Network Information"
    page.stop()
    pump_until(window, lambda: page.active is None)
    assert not page.is_running()


def test_close_cancels_diagnostic_worker(window):
    page = window.pages["Network Diagnostics"]
    started = threading.Event()
    def run(**kwargs):
        started.set()
        kwargs["cancel"].wait(2)
        return None
    page.service.run = run
    page.start("Traceroute")
    pump_until(window, started.is_set)
    window.close()
    page.worker.join(timeout=2)
    assert not page.is_running()
    assert page.cancel.is_set()
