"""Application shell; workers send data through a queue, never touch Tk widgets."""
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk

from app.core.config_service import ConfigService
from app.core.network_utils import NetworkService
from app.gui.dashboard import DashboardPage
from app.gui.diagnostics import DiagnosticsPage
from app.gui.network_info import NetworkInfoPage
from app.core.report_service import operation_report
from app.gui.network_monitor import MonitorPage
from app.gui.reports import ReportsPage
from app import __version__
from app.gui.port_scanner import PortScannerPage
from app.gui.settings import SettingsPage
from app.gui.widgets import BG, PANEL, FG, MUTED, CYAN
from app.utils.command_runner import CommandCancelled
from app.utils.logger import state_directory

LOG = logging.getLogger("kalinet.gui")


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("KaliNet — Network Diagnostics and Security Toolkit")
        self.geometry("1180x800")
        self.minsize(960, 720)
        self.configure(bg=BG)
        self.config_service = ConfigService()
        self.settings = self.config_service.load()
        self.service = NetworkService()
        self.events = queue.Queue()
        self.worker = None
        self.cancel = threading.Event()
        self.closing = False
        self._style()
        self._layout()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.poll_id = self.after(100, self._poll)
        self.after_idle(self.refresh)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        self.option_add("*Font", "{DejaVu Sans} 10")
        style.configure(".", background=BG, foreground=FG, font=("DejaVu Sans", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Title.TLabel", font=("DejaVu Sans", 21, "bold"))
        style.configure("Brand.TLabel", foreground=CYAN, font=("DejaVu Sans", 23, "bold"))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED, font=("DejaVu Sans", 9))
        style.configure("CardValue.TLabel", background=PANEL, foreground=FG, font=("DejaVu Sans", 12, "bold"))
        style.configure("TButton", background="#253c50", foreground=FG, padding=(14, 10), borderwidth=0)
        style.map("TButton", background=[("active", "#205e78"), ("disabled", PANEL)],
                  foreground=[("disabled", MUTED)])
        style.configure("Selected.TButton", background="#155b77", foreground=CYAN)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG,
                        rowheight=32, borderwidth=0)
        style.configure("Treeview.Heading", background="#253c50", foreground=CYAN, padding=8)
        style.map("Treeview", background=[("selected", "#155b77")])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=FG, padding=(10, 8))
        style.map("TNotebook.Tab", background=[("selected", "#155b77")])
        style.configure("Horizontal.TProgressbar", background=CYAN, troughcolor=PANEL)
        for name in ("TEntry", "TSpinbox", "TCombobox"):
            style.configure(name, fieldbackground=PANEL, foreground=FG, insertcolor=FG)
            style.map(name, fieldbackground=[("readonly", PANEL), ("disabled", BG)],
                      foreground=[("readonly", FG), ("disabled", MUTED)])
        self.option_add("*TCombobox*Listbox.background", PANEL)
        self.option_add("*TCombobox*Listbox.foreground", FG)

    def _layout(self):
        header = ttk.Frame(self, padding=(20, 14))
        header.pack(fill="x")
        ttk.Label(header, text="KaliNet", style="Brand.TLabel").pack(side="left")
        self.page_title = ttk.Label(header, text="Dashboard", padding=(24, 0))
        self.page_title.pack(side="left")
        self.refresh_button = ttk.Button(header, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="right")
        self.connectivity = ttk.Label(header, text="● Internet probe: unknown", style="Muted.TLabel")
        self.connectivity.pack(side="right", padx=16)
        ttk.Separator(self).pack(fill="x")
        footer = ttk.Frame(self, padding=(20, 8))
        footer.pack(side="bottom", fill="x")
        self.status = ttk.Label(footer, text="Ready", style="Muted.TLabel")
        self.status.pack(side="left", fill="x", expand=True)
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=140)
        self.progress.pack(side="right", padx=8)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        sidebar = ttk.Frame(body, padding=(12, 20), width=210)
        sidebar.pack(side="left", fill="y")
        ttk.Label(sidebar, text="NETWORK TOOLKIT", style="Muted.TLabel").pack(anchor="w", padx=12, pady=(0, 14))
        content = ttk.Frame(body)
        content.pack(side="left", fill="both", expand=True)
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        self.reports = ReportsPage(content, self.settings)
        self.monitor = MonitorPage(content, self.settings, self.reports)
        self.pages = {
            "Dashboard": DashboardPage(content, self.refresh),
            "Network Information": NetworkInfoPage(content, self.refresh),
            "Network Diagnostics": DiagnosticsPage(content, self.settings, self._diagnostic_completed, self.record),
            "Port Scanner": PortScannerPage(content, self.settings, self._diagnostic_completed, self.record),
            "Network Monitor": self.monitor,
            "Reports": self.reports,
            "Settings": SettingsPage(content, self.settings, self.config_service, self.reports.submit, self.apply_settings),
        }
        self.navigation = {}
        for name, page in self.pages.items():
            page.grid(row=0, column=0, sticky="nsew")
            button = ttk.Button(sidebar, text=name, command=lambda name=name: self.show_page(name))
            button.pack(fill="x", pady=4)
            self.navigation[name] = button
        ttk.Label(sidebar, text=f"v{__version__} • Phases 1–5\nStandard user access", style="Muted.TLabel").pack(
            side="bottom", anchor="w", padx=12, pady=12)
        self.show_page("Dashboard")

    def _diagnostic_completed(self, timestamp):
        self.pages["Dashboard"].set_last_diagnostic(timestamp)

    def record(self, module, result):
        self.reports.archive(operation_report(module, result))

    def apply_settings(self, settings):
        changes = {k: v for k, v in settings.items() if v != self.settings[k]}
        self.settings.update(settings)
        self.monitor.apply_defaults(changes)
        if "ping_count" in changes:
            self.pages["Network Diagnostics"].views["Ping"]["count"].set(str(settings["ping_count"]))

    def show_page(self, name):
        self.reports.visible = name == "Reports"
        if self.reports.visible:
            self.reports.load()
        if name == "Network Monitor":
            self.monitor.init_plot()
        self.pages[name].tkraise()
        self.page_title.configure(text=name)
        for title, button in self.navigation.items():
            button.configure(style="Selected.TButton" if name == title else "TButton")

    def refresh(self):
        if self.closing or (self.worker is not None and self.worker.is_alive()):
            return
        self.cancel.clear()
        self.refresh_button.configure(state="disabled")
        self.status.configure(text="Collecting network information…")
        self.progress.start(12)
        self.worker = threading.Thread(target=self._collect, name="kalinet-network", daemon=False)
        self.worker.start()

    def _collect(self):
        try:
            snapshot = self.service.collect(self.settings["command_timeout"], self.cancel)
            self.events.put(("snapshot", snapshot))
        except CommandCancelled:
            pass
        except Exception:
            LOG.exception("Unexpected network collection failure")
            self.events.put(("error", f"Collection failed. See {state_directory() / 'kalinet.log'}"))

    def _poll(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                self.progress.stop()
                self.refresh_button.configure(state="normal")
                if kind == "snapshot":
                    self.pages["Dashboard"].update_snapshot(data)
                    self.pages["Network Information"].update_snapshot(data)
                    self.record("Network Information", data)
                    color = CYAN if data["connectivity"] == "Reachable" else "#f5c16c"
                    self.connectivity.configure(text=f"● Internet probe: {data['connectivity']}", foreground=color)
                    self.status.configure(text=f"Updated {data['collected_at']} • {len(data['warnings'])} warning(s)")
                else:
                    self.status.configure(text=data)
        except queue.Empty:
            pass
        if not self.closing:
            self.poll_id = self.after(100, self._poll)

    def close(self):
        if self.closing:
            return
        self.closing = True
        self.withdraw()
        self.cancel.set()
        self.pages["Network Diagnostics"].shutdown()
        self.pages["Port Scanner"].shutdown()
        self.monitor.shutdown()
        self.after_cancel(self.poll_id)
        self.progress.stop()
        self.refresh_button.configure(state="disabled")
        self.status.configure(text="Stopping background work…")
        self._wait_for_worker()

    def _wait_for_worker(self):
        if ((self.worker is not None and self.worker.is_alive()) or
                self.pages["Network Diagnostics"].is_running() or self.pages["Port Scanner"].is_running()
                or self.monitor.service.running()):
            self.after(50, self._wait_for_worker)
        else:
            self.monitor.drain()
            if not self.reports.closing:
                self.reports.shutdown()
            if self.reports.is_running():
                self.after(50, self._wait_for_worker)
            else:
                self.reports.finish_shutdown()
                self.destroy()

    def report_callback_exception(self, exc_type, exc_value, traceback):
        LOG.error("GUI callback failed", exc_info=(exc_type, exc_value, traceback))
        if hasattr(self, "status"):
            self.status.configure(text=f"Interface error. See {state_directory() / 'kalinet.log'}")
