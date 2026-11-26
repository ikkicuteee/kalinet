"""Persistent report history, preview and export. Disk work runs on one worker."""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from tkinter import ttk, StringVar

from app.core.report_service import ReportHistory, export_report
from app.gui.widgets import heading, table, text_view, set_text

LOG = logging.getLogger("kalinet.reports")


class ReportsPage(ttk.Frame):
    def __init__(self, parent, settings):
        super().__init__(parent, padding=24)
        self.settings = settings
        self.history = ReportHistory()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kalinet-reports")
        self.pending = []
        self.offset = 0
        self.visible = False
        self.closing = False
        self.format = StringVar(value="JSON")
        heading(self, "Reports", "Select a completed operation to view its results or export a copy.")
        controls = ttk.Frame(self)
        controls.pack(fill="x")
        self.newer = ttk.Button(controls, text="Newer", command=lambda: self.load(self.offset - 100))
        self.older = ttk.Button(controls, text="Older", command=lambda: self.load(self.offset + 100))
        for button in (self.newer, self.older):
            button.pack(side="left", padx=(0, 5))
            button.state(["disabled"])
        self.export_button = ttk.Button(controls, text="Export selected", command=self.export)
        self.export_button.pack(side="right")
        self.export_button.state(["disabled"])
        ttk.Combobox(controls, values=("TXT", "CSV", "JSON"), state="readonly",
                     width=6, textvariable=self.format).pack(side="right", padx=6)
        frame, self.tree = table(self, [(k, k.title(), w) for k, w in
            (("time", 190), ("module", 140), ("operation", 130), ("target", 130), ("status", 110))])
        self.tree.configure(height=7, selectmode="browse")
        frame.pack(fill="x", pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.select)
        frame, self.preview = text_view(self)
        frame.pack(fill="both", expand=True)
        self.notice = StringVar(value="")
        ttk.Label(self, textvariable=self.notice, wraplength=700).pack(anchor="w", pady=5)
        self.poll_id = self.after(80, self.poll)

    def submit(self, action, callback):
        self.pending.append((self.executor.submit(action), callback))

    def poll(self):
        for future, callback in self.pending.copy():
            if future.done():
                self.pending.remove((future, callback))
                try:
                    value = future.result()
                except Exception as exc:
                    LOG.exception("Report operation failed")
                    callback(None, str(exc))
                else:
                    callback(value, None)
        if not self.closing:
            self.poll_id = self.after(80, self.poll)

    def archive(self, report):
        def saved(_, error):
            if error:
                self.notice.set(f"Could not save history: {error}")
            elif self.visible and not self.closing and self.offset == 0:
                self.load(0)
        self.submit(lambda: self.history.add(report), saved)

    def load(self, offset=0):
        self.offset = max(0, offset)
        offset = self.offset
        def loaded(rows, error):
            if error:
                self.notice.set(f"Could not read history: {error}")
                return
            if self.offset != offset:
                return
            selected = self.tree.selection()
            self.tree.delete(*self.tree.get_children())
            for identifier, *values in rows[:100]:
                self.tree.insert("", "end", iid=str(identifier), values=values)
            self.newer.state(["!disabled" if offset else "disabled"])
            self.older.state(["!disabled" if len(rows) > 100 else "disabled"])
            if selected and self.tree.exists(selected[0]):
                self.tree.selection_set(selected)
            elif rows:
                self.tree.selection_set(str(rows[0][0]))
            else:
                set_text(self.preview, "No completed operations yet.")
        self.submit(lambda: self.history.entries(offset, 101), loaded)

    def select(self, event=None):
        selection = self.tree.selection()
        self.export_button.state(["!disabled" if selection else "disabled"])
        if not selection:
            set_text(self.preview, "")
            return
        identifier = selection[0]
        def preview():
            report = self.history.read(identifier)
            body = json.dumps(report["results"], indent=2, ensure_ascii=False)
            if len(body) > 80000:
                body = body[:80000] + "\n… Full results are available in the export."
            return report["title"] + "\n\n" + body
        def show(value, error):
            if self.tree.selection() == (identifier,):
                set_text(self.preview, error or value)
        self.submit(preview, show)

    def export(self):
        selection = self.tree.selection()
        if not selection:
            self.notice.set("Select an operation first.")
            return
        directory, fmt = self.settings["report_directory"], self.format.get()
        self.submit(lambda: export_report(self.history.read(selection[0]), directory, fmt),
                    lambda path, error: self.notice.set(f"Export failed: {error}" if error else f"Saved {path}"))

    def shutdown(self):
        self.closing = True
        self.after_cancel(self.poll_id)
        self.executor.shutdown(wait=False)

    def is_running(self):
        return any(not future.done() for future, _ in self.pending)

    def finish_shutdown(self):
        self.executor.shutdown(wait=True)
        self.pending.clear()
