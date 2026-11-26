"""Operation history and report exports."""
from contextlib import closing, contextmanager
import csv
from datetime import datetime
import json
import logging
import sqlite3
import socket
from pathlib import Path
from uuid import uuid4

from app.utils.logger import state_directory

LOG = logging.getLogger("kalinet.reports")
METADATA = ("title", "module", "hostname", "target", "resolved_target", "started_at", "finished_at",
            "duration_seconds", "status", "open_ports", "mode", "custom_ports", "service_detection", "error")
COLUMNS = ("port", "protocol", "state", "service", "version")


def csv_safe(value):
    text = "" if value is None else str(value)
    # Service banners are untrusted. Keep spreadsheet apps from treating them as formulas.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text


@contextmanager
def report_file(directory, file_format, prefix):
    if file_format not in ("CSV", "TXT", "JSON"):
        raise ValueError("Choose CSV, TXT, or JSON.")
    name = f"kalinet_{prefix}_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.{file_format.lower()}"
    path = Path(directory).expanduser() / name
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="") as stream:
            created = True
            yield stream, path
    except (OSError, ValueError, TypeError):
        LOG.exception("Failed to export report")
        if created:
            try:
                path.unlink()
            except OSError:
                LOG.warning("Could not remove incomplete report %s", path)
        raise


def export_scan(result, directory, file_format):
    if result is None:
        raise ValueError("Run a scan before exporting.")
    with report_file(directory, file_format, "scan") as (stream, path):
        if file_format == "JSON":
            json.dump(result, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        elif file_format == "TXT":
            for key in METADATA:
                stream.write(f"{key}: {result.get(key)}\n")
            stream.write(f"Grouped ports: {result.get('grouped_ports', [])}\n\n")
            for port in result["ports"]:
                stream.write(" | ".join(str(port.get(key, "")) for key in COLUMNS) + "\n")
            if not result["ports"]:
                stream.write("No individual port entries. Consult status and grouped ports.\n")
            stream.write(f"\nSTDERR\n{result.get('stderr', '')}\n")
        else:
            keys = (*METADATA, "grouped_ports", *COLUMNS)
            writer = csv.DictWriter(stream, fieldnames=keys)
            writer.writeheader()
            for port in result["ports"] or [{}]:
                row = {key: result.get(key) for key in METADATA}
                row.update(grouped_ports=json.dumps(result.get("grouped_ports", [])), **port)
                writer.writerow({key: csv_safe(value) for key, value in row.items()})
    return path


def operation_report(module, result):
    hostname = result.get("hostname") or socket.gethostname()
    title = result.get("title") or result.get("tool") or module
    error = result.get("error")
    status = result.get("status") or ("Failed" if error else "Completed")
    if result.get("warnings"):
        status = "Completed with warnings"
    return dict(title=title, module=module, hostname=hostname, target=result.get("target") or hostname,
                finished_at=result.get("finished_at") or result["collected_at"],
                status=status, error=error, results=result)


def export_report(report, directory, file_format):
    if not report:
        raise ValueError("Select an operation to export.")
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    payload = report["results"]
    metadata = {k: v for k, v in report.items() if k != "results"}
    with report_file(directory, file_format, "report") as (stream, path):
        if file_format == "JSON":
            json.dump(report, stream, indent=2, ensure_ascii=False)
        elif file_format == "TXT":
            for key, value in metadata.items():
                stream.write(f"{key}: {value if value is not None else '—'}\n")
            stream.write("\nResults\n")
            json.dump(payload, stream, indent=2, ensure_ascii=False)
        elif report["module"] == "Network Monitor":
            fields = ("timestamp", "status", "latency_ms", "sent", "received", "detail")
            writer = csv.writer(stream)
            writer.writerow([*metadata, *("sample_" + field for field in fields)])
            for row in payload["samples"] or [{}]:
                writer.writerow([csv_safe(v) for v in (*metadata.values(), *(row.get(k) for k in fields))])
        else:
            writer = csv.writer(stream)
            writer.writerow([*metadata, "result_field", "result_value"])
            for key, value in (payload or {"": ""}).items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                writer.writerow([csv_safe(v) for v in (*metadata.values(), key, value)])
    return path


class ReportHistory:
    """Each operation uses its own connection and commits the entire report atomically."""
    def __init__(self, path=None):
        self.path = path or state_directory() / "history.sqlite3"

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=3)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS operations
                (id INTEGER PRIMARY KEY, finished TEXT, module TEXT, title TEXT,
                 target TEXT, status TEXT, payload TEXT NOT NULL)""")
            yield db

    def add(self, report):
        with self.connection() as db:
            db.execute("INSERT INTO operations VALUES(NULL,?,?,?,?,?,?)",
                       (report["finished_at"], report["module"], report["title"], report["target"],
                        report["status"], json.dumps(report, ensure_ascii=False)))

    def entries(self, offset=0, limit=100):
        with self.connection() as db:
            return db.execute("""SELECT id,finished,module,title,target,status FROM operations
                ORDER BY id DESC LIMIT ? OFFSET ?""", (limit, offset)).fetchall()

    def read(self, identifier):
        with self.connection() as db:
            row = db.execute("SELECT payload FROM operations WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise ValueError("This operation could not be found.")
        return json.loads(row[0])
