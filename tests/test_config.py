import json

import pytest

from app.core.config_service import ConfigService, DEFAULTS, validate_settings


@pytest.mark.parametrize("values", [[], {"ping_count": True}, {"ping_count": 0},
    {"command_timeout": 61}, {"monitor_interval": -1}, {"theme": "light"},
    {"report_directory": ""}, {"report_directory": "relative"}, {"unknown": 4}])
def test_invalid_config(values):
    with pytest.raises(ValueError):
        validate_settings(values)


def test_config_round_trip(tmp_path):
    service = ConfigService(tmp_path / "config" / "settings.json")
    assert service.load() == DEFAULTS
    service.save({**DEFAULTS, "command_timeout": 25})
    assert service.load()["command_timeout"] == 25
    assert json.loads(service.path.read_text())["command_timeout"] == 25


def test_corrupt_config_preserved(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("broken json")
    service = ConfigService(path)
    assert service.load() == DEFAULTS
    assert service.warning
    assert path.read_text() == "broken json"


def test_default_file_matches_code():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "config" / "default_settings.json"
    assert json.loads(path.read_text()) == DEFAULTS
