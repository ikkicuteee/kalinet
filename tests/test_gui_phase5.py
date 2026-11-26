import csv
import json
import sys
from unittest.mock import Mock

from app.core.report_service import ReportHistory
from app.utils.command_runner import CommandResult
from test_gui_diagnostics import window, pump_until
from test_monitor import REPLY


def test_monitor_without_matplotlib_or_ping(window, monkeypatch):
    monkeypatch.setitem(sys.modules, "matplotlib.figure", None)
    window.show_page("Network Monitor")
    page = window.monitor
    assert page.canvas is None
    assert "Install matplotlib" in page.plot_frame.winfo_children()[0].cget("text")
    monkeypatch.setattr("app.utils.command_runner.shutil.which", lambda name: None)
    page.start()
    pump_until(window, lambda: page.finished)
    assert page.finished["status"] == "Failed"
    assert page.session.statistics()["loss_percent"] is None
    assert "ping" in page.finished["error"]


def test_monitor_settings_graph_history_and_csv(window, tmp_path):
    settings = window.pages["Settings"]
    settings.config.path = tmp_path / "settings.json"
    settings.fields["monitor_interval"].set("0")
    settings.save()
    assert not settings.config.path.exists()
    settings.fields["monitor_interval"].set("2")
    settings.fields["ping_count"].set("7")
    directory = tmp_path / "exports"
    settings.fields["report_directory"].set(str(directory))
    settings.save()
    pump_until(window, lambda: settings.notice.get() == "Settings saved.")
    assert json.loads(settings.config.path.read_text())["monitor_interval"] == 2
    assert window.pages["Network Diagnostics"].views["Ping"]["count"].get() == "7"
    window.show_page("Network Monitor")
    monitor = window.monitor
    assert monitor.interval.get() == "2" and monitor.canvas
    monitor.service.runner = Mock()
    monitor.service.runner.run.return_value = CommandResult((), 0, REPLY, "")
    monitor.start()
    pump_until(window, lambda: monitor.session.samples)
    assert list(monitor.line.get_ydata()) == [2.5]
    monitor.stop()
    pump_until(window, lambda: monitor.finished)
    window.show_page("Reports")
    reports = window.reports
    pump_until(window, lambda: reports.tree.selection() and "latency_ms" in reports.preview.get("1.0", "end"))
    reports.export()
    pump_until(window, lambda: reports.notice.get().startswith("Saved "))
    assert json.loads(next(directory.glob("*.json")).read_text())["results"]["samples"][0]["received"] == 1
    monitor.export()
    pump_until(window, lambda: monitor.message.get().startswith("Saved "))
    with next(directory.glob("*.csv")).open(newline="", encoding="utf-8") as stream:
        assert next(csv.DictReader(stream))["sample_latency_ms"] == "2.5"


def test_close_during_monitor_archives_session(window):
    page = window.monitor
    page.service.runner = Mock()
    page.service.runner.run.return_value = CommandResult((), 0, REPLY, "")
    page.start()
    pump_until(window, lambda: page.session.samples)
    window.close()
    pump_until(window, lambda: window.reports.closing and not window.reports.is_running())
    assert not page.service.running()
    db = ReportHistory(window.reports.history.path)
    assert db.read(db.entries()[0][0])["results"]["samples"][0]["received"] == 1
