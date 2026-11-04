from tkinter import ttk

from app.gui.widgets import heading, text_view, set_text


class SettingsPage(ttk.Frame):
    def __init__(self, parent, settings, config):
        super().__init__(parent, padding=24)
        heading(self, "Settings", "Configuration is loaded and validated at startup. The settings editor is planned for Phase 5.")
        frame, text = text_view(self)
        frame.pack(fill="both", expand=True)
        lines = [f"Configuration file: {config.path}", "", "Effective settings:"]
        lines.extend(f"{key}: {value}" for key, value in settings.items())
        lines.extend(["", "For now, edit the JSON file while KaliNet is closed, then restart.",
                      "Command timeout applies per command. Other defaults are reserved for later modules."])
        if config.warning:
            lines.extend(["", config.warning])
        set_text(text, "\n".join(lines))
