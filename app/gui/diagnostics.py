"""Diagnostics page: one cancellable worker, Tk updates only in the main thread."""
import logging
import queue
import threading
import tkinter as tk
from tkinter import ttk

from app.core.diagnostics_service import DNS_TYPES, DiagnosticsService, summarize
from app.gui.widgets import heading, set_text, text_view
from app.utils.validators import validate_count, validate_target

LOG = logging.getLogger("kalinet.diagnostics")


class DiagnosticsPage(ttk.Frame):
    def __init__(self, parent, settings, on_complete, on_report=None):
        super().__init__(parent, padding=24)
        self.settings, self.on_complete = settings, on_complete
        self.on_report = on_report
        self.service = DiagnosticsService()
        self.worker = None
        self.cancel = threading.Event()
        self.events = queue.Queue()
        self.closing = False
        self.active = None
        self.controls = []
        self.views = {}
        heading(self, "Network diagnostics", "Run ping, traceroute, or a DNS query. Results use the current command timeout from Settings.")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        for tool in ("Ping", "Traceroute", "DNS Lookup"):
            self._add_tool(tool)
        self.poll_id = self.after(100, self._poll)

    def _add_tool(self, tool):
        page = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(page, text=f" {tool} ")
        row = ttk.Frame(page)
        row.pack(fill="x", pady=(0, 10))
        ttk.Label(row, text="Target").pack(side="left", padx=(0, 8))
        target = tk.StringVar(value="localhost" if tool != "DNS Lookup" else "example.com")
        entry = ttk.Entry(row, textvariable=target, width=25)
        entry.pack(side="left", fill="x", expand=True)
        self.controls.append(entry)
        count = tk.StringVar(value=str(self.settings["ping_count"]))
        record_type = tk.StringVar(value="A")
        if tool == "Ping":
            ttk.Label(row, text="Packets").pack(side="left", padx=8)
            spin = ttk.Spinbox(row, from_=1, to=20, width=4, textvariable=count)
            spin.pack(side="left")
            self.controls.append(spin)
        if tool == "DNS Lookup":
            ttk.Label(row, text="Type").pack(side="left", padx=8)
            combo = ttk.Combobox(row, values=DNS_TYPES, textvariable=record_type, state="readonly", width=7)
            combo.pack(side="left")
            self.controls.append(combo)
        run = ttk.Button(row, text="Run", command=lambda: self.start(tool))
        run.pack(side="left", padx=8)
        self.controls.append(run)
        stop = ttk.Button(row, text="Stop", state="disabled", command=self.stop)
        stop.pack(side="left")
        status = ttk.Label(page, text="Ready", style="Muted.TLabel", wraplength=700)
        status.pack(anchor="w", pady=(0, 6))
        progress = ttk.Progressbar(page, mode="indeterminate")
        progress.pack(fill="x", pady=(0, 10))
        results = ttk.Notebook(page)
        results.pack(fill="both", expand=True)
        frame, summary = text_view(results)
        results.add(frame, text=" Parsed results ")
        frame, raw = text_view(results)
        results.add(frame, text=" Raw output ")
        self.views[tool] = dict(target=target, count=count, record_type=record_type,
                                stop=stop, status=status, progress=progress, summary=summary, raw=raw)

    def start(self, tool):
        if self.closing or self.active is not None:
            return
        view = self.views[tool]
        try:
            target = validate_target(view["target"].get())
            count = validate_count(int(view["count"].get())) if tool == "Ping" else 4
        except ValueError as exc:
            view["status"].configure(text=f"Invalid input: {exc}")
            return
        # Capture Tk variables before starting the worker.
        arguments = dict(tool=tool, target=target, count=count, record_type=view["record_type"].get(),
                         timeout=self.settings["command_timeout"], cancel=self.cancel)
        self.cancel.clear()
        self.active = tool
        for control in self.controls:
            control.configure(state="disabled")
        view["stop"].configure(state="normal")
        view["status"].configure(text=f"Running… timeout {arguments['timeout']} seconds. Partial output is shown on timeout.")
        set_text(view["summary"], "Waiting for command completion…")
        set_text(view["raw"], "")
        view["progress"].start(12)
        self.worker = threading.Thread(target=self._run, args=(arguments,), name="kalinet-diagnostics", daemon=False)
        self.worker.start()

    def _run(self, arguments):
        try:
            self.events.put((self.service.run(**arguments), None))
        except Exception as exc:
            LOG.exception("Diagnostic execution failed")
            self.events.put((None, f"Diagnostic failed: {exc}"))

    def _poll(self):
        # Do not permit another run until the old worker has actually exited.
        if self.active is not None and not self.is_running():
            try:
                result, error = self.events.get_nowait()
            except queue.Empty:
                pass
            else:
                view = self.views[self.active]
                view["progress"].stop()
                view["stop"].configure(state="disabled")
                for control in self.controls:
                    control.configure(state="readonly" if isinstance(control, ttk.Combobox) else "normal")
                if result is not None:
                    set_text(view["summary"], summarize(result))
                    set_text(view["raw"], f"Command: {' '.join(result['args'])}\nExit code: {result['returncode']}\n\n"
                             f"STDOUT\n{result['stdout']}\nSTDERR\n{result['stderr']}")
                    view["status"].configure(text=result["error"] or f"Completed at {result['finished_at']}")
                    self.on_complete(result["finished_at"])
                    if self.on_report:
                        self.on_report("Network Diagnostics", result)
                else:
                    view["status"].configure(text=error)
                    set_text(view["summary"], error)
                self.active = None
        if not self.closing:
            self.poll_id = self.after(100, self._poll)

    def stop(self):
        self.cancel.set()
        if self.active:
            self.views[self.active]["status"].configure(text="Stopping…")
            self.views[self.active]["stop"].configure(state="disabled")

    def is_running(self):
        return self.worker is not None and self.worker.is_alive()

    def shutdown(self):
        self.closing = True
        self.stop()
        self.after_cancel(self.poll_id)
        for view in self.views.values():
            view["progress"].stop()
