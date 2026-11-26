"""Editable defaults backed by the existing atomic JSON configuration service."""
from pathlib import Path
from tempfile import TemporaryFile
import tkinter as tk
from tkinter import filedialog, ttk

from app.core.config_service import validate_settings
from app.gui.widgets import heading


class SettingsPage(ttk.Frame):
    def __init__(self, parent, settings, config, submit, apply):
        super().__init__(parent, padding=24)
        self.settings, self.config = settings, config
        self.submit, self.apply = submit, apply
        self.fields = {}
        heading(self, "Settings", "Saved defaults apply to future operations.")
        form = ttk.Frame(self)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        for index, (key, label) in enumerate((
                ("ping_count", "Ping packets (1–20)"), ("command_timeout", "Command timeout (1–60 s)"),
                ("monitor_interval", "Monitor interval (1–3600 s)"), ("monitor_target", "Monitor target"),
                ("report_directory", "Report directory"))):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="w", padx=(0, 12), pady=6)
            variable = tk.StringVar(value=str(settings[key]))
            self.fields[key] = variable
            ttk.Entry(form, textvariable=variable).grid(row=index, column=1, sticky="ew")
        ttk.Button(form, text="Browse…", command=self.browse).grid(row=4, column=2, padx=6)
        self.button = ttk.Button(self, text="Save settings", command=self.save)
        self.button.pack(anchor="w", pady=12)
        self.notice = tk.StringVar(value=config.warning or "")
        ttk.Label(self, textvariable=self.notice, wraplength=700).pack(anchor="w")
        ttk.Label(self, text=str(config.path), style="Muted.TLabel").pack(anchor="w", pady=6)

    def browse(self):
        path = filedialog.askdirectory(parent=self, title="Default report directory")
        if path:
            self.fields["report_directory"].set(path)

    def save(self):
        candidate = {**self.settings, **{k: v.get() for k, v in self.fields.items()}}
        try:
            for key in ("ping_count", "command_timeout", "monitor_interval"):
                try:
                    candidate[key] = int(candidate[key])
                except ValueError:
                    raise ValueError(f"{key.replace('_', ' ')} must be a whole number.") from None
            candidate = validate_settings(candidate)
        except ValueError as exc:
            self.notice.set(str(exc))
            return

        def write():
            directory = Path(candidate["report_directory"]).expanduser()
            directory.mkdir(parents=True, exist_ok=True)
            with TemporaryFile(dir=directory):
                pass  # Check actual write access before making this the new default.
            self.config.save(candidate)

        def completed(_, error):
            self.button.state(["!disabled"])
            if error:
                self.notice.set(f"Could not save settings: {error}")
            else:
                self.apply(candidate)
                self.config.warning = None
                self.notice.set("Settings saved.")

        self.notice.set("Saving…")
        self.button.state(["disabled"])
        self.submit(write, completed)
