import csv
import json
from unittest.mock import patch

import pytest

from app.core.report_service import export_scan


def record(ports=None):
    return dict(title="KaliNet Port Scan", module="Port Scanner", target="127.0.0.1", hostname="test",
                started_at="2026-11-26T12:00:00+08:00", finished_at="2026-11-26T12:00:01+08:00",
                status="Completed", ports=ports or [], open_ports=0, grouped_ports=[], error=None)


@pytest.mark.parametrize("file_format", ["CSV", "TXT", "JSON"])
def test_empty_report_contains_metadata(tmp_path, file_format):
    path = export_scan(record(), tmp_path, file_format)
    content = path.read_text(encoding="utf-8")
    assert "127.0.0.1" in content and "Completed" in content and "2026-11-26" in content
    if file_format == "JSON":
        assert json.loads(content)["ports"] == []
    if file_format == "CSV":
        with path.open(newline="", encoding="utf-8") as stream:
            assert len(list(csv.DictReader(stream))) == 1


def test_csv_banner_formula_escaped(tmp_path):
    result = record([dict(port=80, protocol="tcp", state="open", service="http", version="=BAD()")])
    path = export_scan(result, tmp_path, "CSV")
    with path.open(newline="", encoding="utf-8") as stream:
        assert next(csv.DictReader(stream))["version"] == "'=BAD()"


def test_export_failure_and_no_result(tmp_path):
    with pytest.raises(OSError):
        export_scan(record(), tmp_path / "missing", "TXT")
    with pytest.raises(ValueError):
        export_scan(None, tmp_path, "JSON")
    with patch("pathlib.Path.open", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            export_scan(record(), tmp_path, "CSV")


def test_exports_do_not_overwrite(tmp_path):
    first = export_scan(record(), tmp_path, "JSON")
    second = export_scan(record(), tmp_path, "JSON")
    assert first != second and first.exists() and second.exists()
