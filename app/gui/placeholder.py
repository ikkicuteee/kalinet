from tkinter import ttk

from app.gui.widgets import heading


class PlaceholderPage(ttk.Frame):
    def __init__(self, parent, title, description):
        super().__init__(parent, padding=24)
        heading(self, title, description)
        panel = ttk.Frame(self, padding=24, style="Card.TFrame")
        panel.pack(fill="x")
        ttk.Label(panel, text="Planned for a later phase", style="CardValue.TLabel").pack(anchor="w")
        ttk.Label(panel, text="This page is a navigation placeholder. No task runs from this page.",
                  style="CardMuted.TLabel", wraplength=650).pack(anchor="w", pady=(12, 0))
