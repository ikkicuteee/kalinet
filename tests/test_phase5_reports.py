import csv
import json

import pytest

from app.core.report_service import ReportHistory, export_report, operation_report
from app.core.config_service import ConfigService, validate_settings


@pytest.mark.parametrize("target", ["-c", "1.2.3.999", "x;id", "", None])
def test_invalid_saved_target(target):
    with pytest.raises(ValueError):
        validate_settings({"monitor_target": target})


def test_upgrade_and_reload_old_settings(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"ping_count": 7, "monitor_interval": 60}')
    service = ConfigService(path)
    settings = service.load()
    assert settings["monitor_target"] == "127.0.0.1" and settings["ping_count"] == 7
    service.save({**settings, "monitor_target": "::1"})
    assert ConfigService(path).load()["monitor_target"] == "::1"


@pytest.mark.parametrize("module,details", [
    ("Network Information", {"hostname": "guest", "collected_at": "12:00", "warnings": ["no route"]}),
    ("Network Diagnostics", {"tool": "Ping", "target": "::1", "finished_at": "12:01", "error": "missing ping"}),
    ("Port Scanner", {"title": "KaliNet Port Scan", "target": "::1", "finished_at": "12:02", "ports": []}),
    ("Network Monitor", {"target": "localhost", "finished_at": "12:03", "status": "Stopped", "samples": []}),
])
def test_all_sources_persist_and_export(tmp_path, module, details):
    report = operation_report(module, details)
    path = tmp_path / "state" / "history.db"
    ReportHistory(path).add(report)
    history = ReportHistory(path)
    entry, = history.entries()
    assert entry[2] == module
    assert history.read(entry[0]) == report
    directory = tmp_path / "new reports"
    assert json.loads(export_report(report, directory, "JSON").read_text()) == report
    assert module in export_report(report, directory, "TXT").read_text()
    with export_report(report, directory, "CSV").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
        assert rows and all(row["module"] == module and row["target"] == report["target"] for row in rows)


def test_export_error(tmp_path):
    bad = tmp_path / "ordinary_file"
    bad.touch()
    with pytest.raises(OSError):
        export_report({"results": {}}, bad, "CSV")
    assert bad.read_bytes() == b""
