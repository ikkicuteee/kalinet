"""Validated, atomic JSON settings persistence in the XDG configuration directory."""
import json
import logging
import os
from pathlib import Path
import tempfile

DEFAULTS = {
    "ping_count": 4, "command_timeout": 10, "monitor_interval": 5,
    "report_directory": "~/Documents/KaliNet Reports", "theme": "dark",
}
LOG = logging.getLogger("kalinet.config")


def validate_settings(values):
    if not isinstance(values, dict):
        raise ValueError("Settings must be a JSON object.")
    unknown = set(values) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown settings: {', '.join(sorted(unknown))}")
    settings = {**DEFAULTS, **values}
    for key, low, high in (("ping_count", 1, 20), ("command_timeout", 1, 60),
                           ("monitor_interval", 1, 3600)):
        value = settings[key]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{key} must be an integer from {low} to {high}.")
    directory = settings["report_directory"]
    if not isinstance(directory, str) or not directory.strip() or "\x00" in directory:
        raise ValueError("Report directory must be a nonempty path.")
    if not Path(directory).expanduser().is_absolute():
        raise ValueError("Report directory must be an absolute path (or start with ~/).")
    if settings["theme"] != "dark":
        raise ValueError("Only the dark theme is currently supported.")
    return settings


class ConfigService:
    def __init__(self, path=None):
        base = Path(os.environ.get("XDG_CONFIG_HOME", ""))
        if not base.is_absolute():
            base = Path.home() / ".config"
        self.path = Path(path) if path else base / "kalinet" / "settings.json"
        self.warning = None

    def load(self):
        self.warning = None
        try:
            if not self.path.exists():
                self.save(DEFAULTS)
                return dict(DEFAULTS)
            return validate_settings(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            self.warning = f"Using default settings: {exc}"
            LOG.warning(self.warning)
            return dict(DEFAULTS)

    def save(self, values):
        settings = validate_settings(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".settings-", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(settings, stream, indent=2)
                stream.write("\n")
            os.replace(temporary, self.path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
