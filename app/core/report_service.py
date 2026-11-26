"""Scan-only exports. General reports remain a later milestone."""
import csv
from datetime import datetime
import json
import logging
from pathlib import Path
from uuid import uuid4

LOG = logging.getLogger("kalinet.reports")
METADATA = ("title", "module", "hostname", "target", "resolved_target", "started_at", "finished_at",
            "duration_seconds", "status", "open_ports", "mode", "custom_ports", "service_detection", "error")
COLUMNS = ("port", "protocol", "state", "service", "version")


def csv_safe(value):
    text = "" if value is None else str(value)
    # Service banners are untrusted. Keep spreadsheet apps from treating them as formulas.
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text


def export_scan(result, directory, file_format):
    if file_format not in ("CSV", "TXT", "JSON"):
        raise ValueError("Choose CSV, TXT, or JSON.")
    if result is None:
        raise ValueError("Run a scan before exporting.")
    directory = Path(directory).expanduser()
    name = f"kalinet_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}.{file_format.lower()}"
    path = directory / name
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="") as stream:
            created = True
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
    except (OSError, ValueError, TypeError):
        LOG.exception("Failed to export scan report")
        if created:
            try:
                path.unlink()
            except OSError:
                LOG.warning("Could not remove incomplete report %s", path)
        raise
    return path
