from tkinter import ttk

from app.gui.widgets import heading, table, text_view, set_text


class NetworkInfoPage(ttk.Frame):
    def __init__(self, parent, refresh):
        super().__init__(parent, padding=24)
        heading(self, "Network information", "Interfaces, addresses, routing, DNS, and cumulative traffic counters.")
        ttk.Button(self, text="Refresh Network Information", command=refresh).pack(anchor="w", pady=(0, 12))
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)
        frame, self.interfaces = table(tabs, [("name", "Interface", 110), ("state", "State", 85),
            ("mac", "MAC address", 160), ("ipv4", "IPv4 addresses", 190), ("ipv6", "IPv6 addresses", 260)])
        tabs.add(frame, text=" Interfaces ")
        frame, self.statistics = table(tabs, [("name", "Interface", 100), ("rx", "RX bytes", 120),
            ("tx", "TX bytes", 120), ("rxp", "RX packets", 100), ("txp", "TX packets", 100),
            ("err", "Errors in/out", 110), ("drop", "Drops in/out", 110)])
        tabs.add(frame, text=" Traffic counters ")
        frame, self.routes = text_view(tabs)
        tabs.add(frame, text=" Routing & DNS ")
        frame, self.links = text_view(tabs)
        tabs.add(frame, text=" Link details ")
        self.status = ttk.Label(self, text="No snapshot yet", style="Muted.TLabel")
        self.status.pack(anchor="w", pady=(12, 0))

    def update_snapshot(self, snapshot):
        for tree in (self.interfaces, self.statistics):
            for child in tree.get_children():
                tree.delete(child)
        for interface in snapshot["interfaces"]:
            self.interfaces.insert("", "end", values=(interface["name"], interface["state"], interface["mac"],
                ", ".join(interface["ipv4"]) or "—", ", ".join(interface["ipv6"]) or "—"))
        for name, stat in snapshot["statistics"].items():
            self.statistics.insert("", "end", values=(name, stat["bytes_recv"], stat["bytes_sent"],
                stat["packets_recv"], stat["packets_sent"], f"{stat['errin']} / {stat['errout']}",
                f"{stat['dropin']} / {stat['dropout']}"))
        lines = [f"Default gateway: {snapshot['gateway'] or 'Unavailable'}",
                 f"DNS source: {snapshot['dns_source']}",
                 f"DNS servers: {', '.join(snapshot['dns_servers']) or 'Unavailable'}",
                 "A loopback nameserver may be a local DNS stub resolver.", "", "IPv4 and IPv6 routes:"]
        lines.extend("  ".join(f"{key}={value}" for key, value in route.items()) for route in snapshot["routes"])
        if snapshot["warnings"]:
            lines.extend(["", "Collection warnings:", *snapshot["warnings"]])
        set_text(self.routes, "\n".join(lines))
        set_text(self.links, snapshot["link_statistics"])
        self.status.configure(text=f"Collected: {snapshot['collected_at']} • Counters are cumulative, not rates.")
