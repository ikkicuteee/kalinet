import tkinter as tk
from tkinter import ttk

from app.gui.widgets import heading, text_view, set_text


class DashboardPage(ttk.Frame):
    def __init__(self, parent, refresh):
        super().__init__(parent, padding=24)
        heading(self, "Network overview", "Live local network state. Refresh to collect a new snapshot.")
        ttk.Button(self, text="Refresh Dashboard", command=refresh).pack(anchor="w", pady=(0, 16))
        cards = ttk.Frame(self)
        cards.pack(fill="x")
        self.values = {}
        labels = [("hostname", "HOSTNAME"), ("active_interface", "ACTIVE INTERFACE"),
                  ("ipv4", "IPv4 ADDRESS"), ("gateway", "DEFAULT GATEWAY"),
                  ("dns_servers", "DNS SERVERS"), ("connectivity", "INTERNET PROBE"),
                  ("interface_count", "NETWORK INTERFACES"), ("listening_ports", "LISTENING SOCKETS"),
                  ("last_diagnostic", "LAST DIAGNOSTIC / SCAN")]
        for index, (key, label) in enumerate(labels):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.grid(row=index // 3, column=index % 3, padx=5, pady=5, sticky="nsew")
            cards.columnconfigure(index % 3, weight=1, uniform="cards")
            ttk.Label(card, text=label, style="CardMuted.TLabel").pack(anchor="w")
            value = tk.StringVar(value="Not collected")
            self.values[key] = value
            ttk.Label(card, textvariable=value, style="CardValue.TLabel", wraplength=250).pack(
                anchor="w", pady=(8, 0))
        self.timestamp = ttk.Label(self, text="No snapshot yet", style="Muted.TLabel")
        self.timestamp.pack(anchor="w", pady=(14, 6))
        frame, self.notes = text_view(self)
        frame.pack(fill="both", expand=True)
        set_text(self.notes, "Network collection has not completed.")

    def update_snapshot(self, snapshot):
        values = {**snapshot, "interface_count": len(snapshot["interfaces"]),
                  "dns_servers": ", ".join(snapshot["dns_servers"]),
                  "last_diagnostic": "Not run (future phase)"}
        for key, variable in self.values.items():
            value = values.get(key)
            variable.set("Unavailable" if value is None or value == "" else str(value))
        self.timestamp.configure(text=f"Snapshot: {snapshot['collected_at']}")
        notes = ["Internet indicator: one ICMP probe to 1.1.1.1. A missing reply does not prove the Internet is down.",
                 "Listening sockets include TCP listeners and bound UDP sockets; IPv4/IPv6 entries are counted separately.",
                 "Active interface is inferred from default routes, then from an UP non-loopback interface."]
        if snapshot["warnings"]:
            notes.append("\nCollection warnings:\n" + "\n".join(snapshot["warnings"]))
        set_text(self.notes, "\n\n".join(notes))
