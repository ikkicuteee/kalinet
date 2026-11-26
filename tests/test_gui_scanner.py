import threading

from app.core.scanner_service import ScannerService
from app.utils.command_runner import CommandCancelled
from test_gui_diagnostics import window, pump_until
from test_scanner import runner_for


def test_scanner_results_and_export(window, monkeypatch, tmp_path):
    page = window.pages["Port Scanner"]
    page.service = ScannerService(runner_for())
    page.start()
    pump_until(window, lambda: not page.busy)
    assert len(page.results_table.get_children()) == 2
    assert "Open ports: 1" in page.summary.cget("text")
    assert window.pages["Dashboard"].last_diagnostic != "Not run"
    monkeypatch.setattr("app.gui.port_scanner.filedialog.askdirectory", lambda **kwargs: str(tmp_path))
    page.export()
    pump_until(window, lambda: not page.busy)
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_scanner_requires_fresh_authorization(window, monkeypatch):
    page = window.pages["Port Scanner"]
    page.target.set("192.0.2.1")
    page.service = ScannerService(runner_for())
    monkeypatch.setattr("app.gui.port_scanner.messagebox.askyesno", lambda *args, **kwargs: False)
    page.start()
    assert page.worker is None
    assert "not confirmed" in page.status.cget("text")
    monkeypatch.setattr("app.gui.port_scanner.messagebox.askyesno", lambda *args, **kwargs: True)
    page.start()
    pump_until(window, lambda: not page.busy)
    assert page.result["authorized"] is True
    original = page.worker
    monkeypatch.setattr("app.gui.port_scanner.messagebox.askyesno", lambda *args, **kwargs: False)
    page.start()
    assert page.worker is original


def test_scan_navigation_duplicate_prevention_and_cancel(window):
    page = window.pages["Port Scanner"]
    runner = runner_for()
    started = threading.Event()
    def execute(args, timeout, cancel):
        started.set()
        assert cancel.wait(2)
        raise CommandCancelled("Scan cancelled.")
    runner.run.side_effect = execute
    page.service = ScannerService(runner)
    page.start()
    pump_until(window, started.is_set)
    original = page.worker
    page.start()
    assert page.worker is original
    window.show_page("Network Diagnostics")
    window.update()
    assert window.page_title.cget("text") == "Network Diagnostics"
    page.stop()
    pump_until(window, lambda: not page.busy)
    assert page.result["status"] == "Cancelled"


def test_scanner_shutdown_cancels_worker(window):
    page = window.pages["Port Scanner"]
    runner = runner_for()
    started = threading.Event()
    def execute(args, timeout, cancel):
        started.set()
        cancel.wait(2)
        raise CommandCancelled("Scan cancelled.")
    runner.run.side_effect = execute
    page.service = ScannerService(runner)
    page.start()
    pump_until(window, started.is_set)
    window.close()
    page.worker.join(timeout=2)
    assert not page.is_running() and page.cancel.is_set()


def test_large_scan_table_batches_complete(window):
    page = window.pages["Port Scanner"]
    result = ScannerService(runner_for()).scan("127.0.0.1")
    result["ports"] = [dict(port=n, protocol="tcp", state="closed", service="", version="") for n in range(1, 602)]
    page.service.scan = lambda **kwargs: result
    page.start()
    pump_until(window, lambda: not page.busy)
    assert len(page.results_table.get_children()) == 601
    assert page.render_id is None
