"""Scanner page using the existing main-thread queue pattern."""
import logging
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.core.report_service import export_scan
from app.core.scanner_service import SCAN_MODES, ScannerService, is_local_target, validate_scan
from app.gui.widgets import heading, table, text_view, set_text
from app.utils.validators import validate_target

LOG = logging.getLogger("kalinet.scanner.gui")


class PortScannerPage(ttk.Frame):
    def __init__(self, parent, settings, on_complete, on_report=None):
        super().__init__(parent, padding=24)
        self.settings, self.on_complete = settings, on_complete
        self.on_report = on_report
        self.service = ScannerService()
        self.cancel = threading.Event()
        self.worker = None
        self.events = queue.Queue()
        self.busy = False
        self.closing = False
        self.result = None
        self.render_id = None
        self.rendering = False
        heading(self, "Port scanner", "Scan one authorized lab host using TCP connect scanning. No administrator privileges required.")
        self.target = tk.StringVar(value="127.0.0.1")
        self.mode = tk.StringVar(value="Quick")
        self.ports = tk.StringVar(value="22,80,443")
        self.detect = tk.BooleanVar(value=False)
        self.timeout = tk.StringVar(value="120")
        self.file_format = tk.StringVar(value="JSON")
        self.controls = []
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Target").pack(side="left", padx=(0, 8))
        entry = ttk.Entry(row, textvariable=self.target)
        entry.pack(side="left", fill="x", expand=True)
        self.controls.append(entry)
        combo = ttk.Combobox(row, values=SCAN_MODES, textvariable=self.mode, state="readonly", width=14)
        combo.pack(side="left", padx=8)
        self.controls.append(combo)
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Custom TCP ports").pack(side="left", padx=(0, 8))
        entry = ttk.Entry(row, textvariable=self.ports, width=24)
        entry.pack(side="left", fill="x", expand=True)
        self.controls.append(entry)
        ttk.Label(row, text="Timeout (s)").pack(side="left", padx=8)
        spin = ttk.Spinbox(row, from_=1, to=120, textvariable=self.timeout, width=5)
        spin.pack(side="left")
        self.controls.append(spin)
        check = ttk.Checkbutton(row, text="Service detection (-sV)", variable=self.detect)
        check.pack(side="left", padx=8)
        self.controls.append(check)
        ttk.Label(self, text="Quick: common TCP ports • Standard: default TCP ports • Custom: e.g. 22,80,8000-8010",
                  style="Muted.TLabel", wraplength=720).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(0, 8))
        start = ttk.Button(row, text="Start Scan", command=self.start)
        start.pack(side="left")
        self.controls.append(start)
        self.stop_button = ttk.Button(row, text="Cancel Scan", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(row, text="Export Scan", command=self.export, state="disabled")
        self.export_button.pack(side="right")
        combo = ttk.Combobox(row, values=("CSV", "TXT", "JSON"), textvariable=self.file_format, state="readonly", width=7)
        combo.pack(side="right", padx=8)
        self.controls.append(combo)
        self.status = ttk.Label(self, text="Ready", style="Muted.TLabel", wraplength=720)
        self.status.pack(anchor="w", pady=(0, 6))
        self.summary = ttk.Label(self, text="No scan yet", wraplength=720)
        self.summary.pack(anchor="w", pady=(0, 6))
        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True)
        frame, self.results_table = table(tabs, [("port", "Port", 80), ("protocol", "Protocol", 80),
            ("state", "State", 110), ("service", "Service", 130), ("version", "Version", 240)])
        tabs.add(frame, text=" Results ")
        frame, self.details = text_view(tabs)
        tabs.add(frame, text=" Details / XML ")
        self.poll_id = self.after(100, self._poll)

    def _set_busy(self, busy, scanning=False):
        self.busy = busy
        for control in self.controls:
            control.configure(state="disabled" if busy else "readonly" if isinstance(control, ttk.Combobox) else "normal")
        self.stop_button.configure(state="normal" if scanning else "disabled")
        self.export_button.configure(state="normal" if not busy and self.result is not None else "disabled")
        self.progress.start(12) if busy else self.progress.stop()

    def start(self):
        if self.busy or self.closing:
            return
        try:
            target = validate_target(self.target.get())
            timeout = int(self.timeout.get())
            # Validate options before requesting authorization; the service validates it again.
            target, ports = validate_scan(target, self.mode.get(), self.ports.get(), self.detect.get(), timeout, True)
            authorized = False
            if not is_local_target(target):
                authorized = messagebox.askyesno("Authorize lab scan",
                    f"Do you own or have explicit permission to scan this single lab target?\n\n{target}\n\n"
                    "For a hostname, one resolved IP will be scanned.", parent=self)
                if not authorized:
                    self.status.configure(text="Scan not started: authorization was not confirmed.")
                    return
        except ValueError as exc:
            self.status.configure(text=f"Invalid input: {exc}")
            return
        arguments = dict(target=target, mode=self.mode.get(), ports=ports,
                         service_detection=self.detect.get(), timeout=timeout, authorized=authorized, cancel=self.cancel)
        self.cancel.clear()
        self.result = None
        for child in self.results_table.get_children():
            self.results_table.delete(child)
        set_text(self.details, "")
        self.summary.configure(text=f"Target: {target} • Running")
        self.status.configure(text="Resolving target / scanning…")
        self._set_busy(True, scanning=True)
        self.worker = threading.Thread(target=self._scan, args=(arguments,), name="kalinet-scanner", daemon=False)
        self.worker.start()

    def _scan(self, arguments):
        try:
            self.events.put(("scan", self.service.scan(**arguments), None))
        except Exception as exc:
            LOG.exception("Unexpected scanner error")
            self.events.put(("scan", None, f"Scan failed: {exc}"))

    def export(self):
        if self.busy or self.closing or self.result is None:
            return
        directory = filedialog.askdirectory(parent=self, title="Save scan report in directory",
            initialdir=str(Path(self.settings["report_directory"]).expanduser()))
        if not directory:
            return
        self._set_busy(True)
        self.status.configure(text="Exporting scan report…")
        self.worker = threading.Thread(target=self._export, args=(self.result, directory, self.file_format.get()),
                                       name="kalinet-scan-export", daemon=False)
        self.worker.start()

    def _export(self, result, directory, file_format):
        try:
            self.events.put(("export", str(export_scan(result, directory, file_format)), None))
        except Exception as exc:
            LOG.exception("Scan export failed")
            self.events.put(("export", None, f"Export failed: {exc}"))

    def _poll(self):
        if self.busy and not self.is_running():
            try:
                kind, result, error = self.events.get_nowait()
            except queue.Empty:
                pass
            else:
                if kind == "scan" and result is not None:
                    self.result = result
                    count = result["open_ports"] if result["open_ports"] is not None else "Unavailable"
                    self.summary.configure(text=f"Target: {result['target']} → {result['resolved_target'] or 'unresolved'}\n"
                        f"{result['status']} • {result['duration_seconds']:g}s • Open ports: {count}")
                    notes = ("No individual port entries; consult grouped states below.\n" if not result["ports"] else "")
                    set_text(self.details, f"Started: {result['started_at']}\nFinished: {result['finished_at']}\n"
                        f"Command: {' '.join(result['args'])}\nHost state: {result['host_state']}\n"
                        f"{notes}Grouped states: {result['grouped_ports']}\n"
                        "-Pn skips host discovery; host state does not prove reachability.\n"
                        f"Error: {result['error'] or 'None'}\n"
                        "Output previews are limited to 200,000 characters each; JSON export retains full output.\n"
                        f"\nSTDERR\n{result['stderr'][:200000]}\n\nXML\n{result['stdout'][:200000]}")
                    self.status.configure(text=result["error"] or "Scan completed. Results cover only the selected TCP ports.")
                    self.on_complete(result["finished_at"])
                    if self.on_report:
                        self.on_report("Port Scanner", result)
                    self.pending_rows = iter(result["ports"])
                    self.rendering = True
                    self._render_rows()
                else:
                    self.status.configure(text=error or f"Saved: {result}")
                if not self.rendering:
                    self._set_busy(False)
        if not self.closing:
            self.poll_id = self.after(100, self._poll)

    def stop(self):
        self.cancel.set()
        self.stop_button.configure(state="disabled")
        if self.busy:
            self.status.configure(text="Stopping scan…")

    def _render_rows(self):
        self.render_id = None
        if self.closing:
            return
        # Large custom scans must not block the event loop while inserting rows.
        for _ in range(250):
            port = next(self.pending_rows, None)
            if port is None:
                self.rendering = False
                self._set_busy(False)
                return
            self.results_table.insert("", "end", values=tuple(port[key] for key in ("port", "protocol", "state", "service", "version")))
        self.stop_button.configure(state="disabled")
        self.render_id = self.after(10, self._render_rows)

    def is_running(self):
        return self.worker is not None and self.worker.is_alive()

    def shutdown(self):
        self.closing = True
        self.stop()
        self.progress.stop()
        self.after_cancel(self.poll_id)
        if self.render_id is not None:
            self.after_cancel(self.render_id)
