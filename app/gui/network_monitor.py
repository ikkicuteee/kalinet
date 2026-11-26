"""Network Monitor, using a serial ping worker and main-thread Tk/Matplotlib updates."""
import queue
import tkinter as tk
from tkinter import ttk

from app.core.monitor_service import MonitorService, MonitorSession
from app.core.report_service import export_report, operation_report
from app.gui.widgets import heading, table, PANEL, FG, MUTED, CYAN


def display(value, suffix):
    return "—" if value is None else f"{value:.2f}{suffix}"


class MonitorPage(ttk.Frame):
    def __init__(self, parent, settings, reports):
        super().__init__(parent, padding=24)
        self.settings, self.reports = settings, reports
        self.service = MonitorService()
        self.session = self.finished = None
        self.active = False
        self.pending_defaults = {}
        self.target = tk.StringVar(value=settings["monitor_target"])
        self.interval = tk.StringVar(value=str(settings["monitor_interval"]))
        heading(self, "Network monitor", "Measure ICMP reachability and round-trip time to one host.")
        row = ttk.Frame(self)
        row.pack(fill="x")
        ttk.Label(row, text="Target").pack(side="left")
        self.entry = ttk.Entry(row, textvariable=self.target, width=20)
        self.entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Label(row, text="Interval (s)").pack(side="left")
        self.spin = ttk.Spinbox(row, from_=1, to=3600, textvariable=self.interval, width=5)
        self.spin.pack(side="left", padx=6)
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=8)
        self.start_button = ttk.Button(actions, text="Start Monitoring", command=self.start)
        self.stop_button = ttk.Button(actions, text="Stop Monitoring", command=self.stop)
        self.export_button = ttk.Button(actions, text="Export history CSV", command=self.export)
        for button in (self.start_button, self.stop_button, self.export_button):
            button.pack(side="left", padx=(0, 5))
        self.stop_button.state(["disabled"])
        self.export_button.state(["disabled"])
        self.status = ttk.Label(self, text="Idle", wraplength=700)
        self.status.pack(anchor="w")
        self.stats = ttk.Label(self, text="No measurements yet", wraplength=700)
        self.stats.pack(anchor="w", pady=5)
        self.plot_frame = ttk.Frame(self)
        self.plot_frame.pack(fill="both", expand=True)
        self.canvas = None
        self.plot_attempted = False
        frame, self.tree = table(self, [(k, title, width) for k, title, width in (
            ("timestamp", "Time", 190), ("status", "Connectivity", 100), ("latency", "Latency", 85),
            ("counts", "Received / sent", 100), ("detail", "Details", 200))])
        self.tree.configure(height=6)
        self.tree.tag_configure("failure", foreground="#ffad86")
        frame.pack(fill="both", expand=True, pady=5)
        self.message = tk.StringVar()
        ttk.Label(self, textvariable=self.message, wraplength=700).pack(anchor="w")
        self.poll_id = self.after(100, self.poll)

    def init_plot(self):
        if self.plot_attempted:
            return
        self.plot_attempted = True
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except ImportError:
            ttk.Label(self.plot_frame, text="Install matplotlib from requirements.txt to display the latency graph.").pack()
            return
        figure = Figure(figsize=(5, 1.8), dpi=85, facecolor=PANEL)
        figure.subplots_adjust(left=.12, right=.97, bottom=.26, top=.92)
        self.axis = figure.add_subplot(facecolor=PANEL)
        self.axis.set_xlabel("Probe number · latest 60", color=FG)
        self.axis.set_ylabel("Latency (ms)", color=FG)
        self.axis.tick_params(colors=MUTED)
        self.axis.grid(alpha=.18)
        self.line, = self.axis.plot([], [], ".-", color=CYAN)
        self.canvas = FigureCanvasTkAgg(figure, self.plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.canvas.draw_idle()

    def start(self):
        if self.active:
            return
        try:
            target, interval = self.target.get(), int(self.interval.get())
            self.service.start(target, interval, self.settings["command_timeout"])
        except ValueError as exc:
            self.status.configure(text=f"Invalid monitor settings: {exc}", foreground="#ffad86")
            return
        self.session = MonitorSession(target, interval)
        self.finished = None
        self.active = True
        self.tree.delete(*self.tree.get_children())
        for control in (self.start_button, self.entry, self.spin, self.export_button):
            control.state(["disabled"])
        self.stop_button.state(["!disabled"])
        self.status.configure(text=f"Checking {target}…", foreground=FG)
        self.message.set("")
        self.stats.configure(text="Waiting for the first sample")
        self.draw()

    def stop(self):
        self.service.stop()
        self.stop_button.state(["disabled"])
        self.status.configure(text="Stopping monitoring…")

    def draw(self):
        if self.canvas:
            samples = self.session.samples
            first = max(0, len(samples) - 60)
            self.line.set_data(range(first + 1, len(samples) + 1),
                [s["latency_ms"] if s["latency_ms"] is not None else float("nan") for s in samples[first:]])
            self.axis.relim()
            self.axis.autoscale_view()
            self.canvas.draw_idle()

    def add_sample(self, sample):
        self.session.add(sample)
        ok = sample["status"] == "Reachable"
        self.status.configure(text=f"{self.session.target} • {sample['status']}", foreground=CYAN if ok else "#ffad86")
        values = self.session.statistics()
        loss = "Loss unavailable" if not values["sent"] else (
            f"Loss {display(values['loss_percent'], '%')} ({values['sent'] - values['received']}/{values['sent']})")
        self.stats.configure(text="   ".join([
            f"Latest {display(sample['latency_ms'], ' ms')}", f"Avg {display(values['avg_ms'], ' ms')}",
            f"Min {display(values['min_ms'], ' ms')}", f"Max {display(values['max_ms'], ' ms')}",
            loss]))
        counts = "—" if sample["sent"] is None else f"{sample['received']} / {sample['sent']}"
        self.tree.insert("", 0, values=(sample["timestamp"], sample["status"], display(sample["latency_ms"], " ms"),
                                        counts, sample["detail"]), tags=() if ok else ("failure",))
        if len(self.session.samples) > 500:
            self.tree.delete(self.tree.get_children()[-1])
        self.export_button.state(["!disabled"])
        self.draw()

    def drain(self):
        while True:
            try:
                kind, data = self.service.events.get_nowait()
            except queue.Empty:
                return
            if kind == "sample":
                self.add_sample(data)
            else:
                self.active = False
                self.apply_defaults(self.pending_defaults)
                self.pending_defaults.clear()
                self.finished = operation_report("Network Monitor", self.session.result("Failed" if data else "Stopped", data))
                self.reports.archive(self.finished)
                self.status.configure(text=data or f"Monitoring stopped • {len(self.session.samples)} samples")
                for control in (self.entry, self.spin, self.start_button, self.export_button):
                    control.state(["!disabled"])
                self.stop_button.state(["disabled"])

    def poll(self):
        self.drain()
        self.poll_id = self.after(100, self.poll)

    def export(self):
        if self.session is None:
            return
        report = self.finished or operation_report("Network Monitor", self.session.result("In progress"))
        directory = self.settings["report_directory"]
        self.reports.submit(lambda: export_report(report, directory, "CSV"),
            lambda path, error: self.message.set(f"Export failed: {error}" if error else f"Saved {path}"))

    def shutdown(self):
        self.after_cancel(self.poll_id)
        self.service.stop()

    def apply_defaults(self, changes):
        if self.active:
            self.pending_defaults.update(changes)
            return
        if "monitor_interval" in changes:
            self.interval.set(str(changes["monitor_interval"]))
        if "monitor_target" in changes:
            self.target.set(changes["monitor_target"])
