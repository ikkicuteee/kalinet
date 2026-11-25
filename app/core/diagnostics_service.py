"""Ping, traceroute and dig execution and parsing, independent of Tkinter."""
from datetime import datetime
import re
import logging

from app.utils.command_runner import CommandError, CommandRunner
from app.utils.validators import validate_count, validate_target

DNS_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "PTR")
LOG = logging.getLogger("kalinet.diagnostics")


def parse_ping(output):
    stats = {}
    packets = re.search(r"(\d+) packets transmitted,\s*(\d+)(?: packets)? received,.*?([\d.]+)% packet loss", output)
    if packets:
        stats.update(transmitted=int(packets[1]), received=int(packets[2]), loss_percent=float(packets[3]))
    latency = re.search(r"(?:rtt|round-trip).*?=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)\s*ms", output)
    if latency:
        stats.update(zip(("min_ms", "avg_ms", "max_ms", "mdev_ms"), map(float, latency.groups())))
    return stats


def parse_traceroute(output):
    hops = []
    for line in output.splitlines():
        match = re.match(r"^\s*(\d+)\s+(.+)$", line)
        if match:
            hops.append({"hop": int(match[1]), "details": match[2],
                         "latencies_ms": [float(x) for x in re.findall(r"([\d.]+)\s*ms", match[2])],
                         "timeouts": match[2].count("*")})
    return hops


def parse_dns(output):
    status = re.search(r"status:\s*([A-Z0-9]+)", output)
    records = []
    in_answer = False
    for line in output.splitlines():
        if line.startswith(";; ANSWER SECTION:"):
            in_answer = True
            continue
        if line.startswith(";;"):
            in_answer = False
        if in_answer and line.strip() and not line.startswith(";"):
            parts = line.split(None, 4)
            if len(parts) == 5:
                records.append(dict(zip(("name", "ttl", "class", "type", "value"), parts)))
    return {"status": status[1] if status else None, "records": records}


class DiagnosticsService:
    def __init__(self, runner=None):
        self.runner = runner or CommandRunner()

    def run(self, tool, target, count=4, record_type="A", timeout=10, cancel=None):
        target = validate_target(target)
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise ValueError("Timeout must be an integer from 1 to 60 seconds.")
        if tool == "Ping":
            args = ["ping", "-n", "-c", str(validate_count(count)), "-W", "2", target]
            parser = parse_ping
        elif tool == "Traceroute":
            args = ["traceroute", "-n", "-m", "30", "-q", "1", "-w", "1"]
            if ":" in target:
                args.append("-6")
            args.append(target)
            parser = parse_traceroute
        elif tool == "DNS Lookup":
            if record_type not in DNS_TYPES:
                raise ValueError("Choose a supported DNS record type.")
            args = ["dig", "+time=2", "+tries=1", target, record_type]
            parser = parse_dns
        else:
            raise ValueError("Unknown diagnostic tool.")
        error = None
        try:
            result = self.runner.run(args, timeout=timeout, cancel=cancel)
        except CommandError as exc:
            result, error = exc.result, str(exc)
        stdout = result.stdout if result else ""
        stderr = result.stderr if result else ""
        parsed = parser(stdout)
        if tool == "Ping" and not error and "transmitted" not in parsed:
            error = "Ping returned no recognizable packet statistics. Inspect raw output."
        if tool == "Traceroute" and not error and not parsed:
            error = "Traceroute returned no recognizable hops. Inspect raw output."
        if tool == "DNS Lookup":
            status = parsed["status"]
            if not error and status != "NOERROR":
                error = f"DNS response: {status or 'missing response header'}. Inspect raw output."
        if error:
            LOG.warning("%s %s: %s", tool, target, error)
        return {"tool": tool, "target": target, "args": args, "stdout": stdout, "stderr": stderr,
                "returncode": result.returncode if result else None, "parsed": parsed,
                "error": error, "finished_at": datetime.now().astimezone().isoformat(timespec="seconds")}


def summarize(result):
    data = result["parsed"]
    lines = [f"{result['tool']} • {result['target']} • {result['finished_at']}"]
    if result["error"]:
        lines.append(result["error"])
    if result["tool"] == "Ping":
        if "transmitted" in data:
            lines.append(f"Transmitted: {data['transmitted']} | Received: {data['received']} | Loss: {data['loss_percent']:g}%")
        if "avg_ms" in data:
            lines.append(f"Latency min/avg/max: {data['min_ms']:g} / {data['avg_ms']:g} / {data['max_ms']:g} ms; deviation {data['mdev_ms']:g} ms")
        else:
            lines.append("Latency unavailable; no completed round-trip statistics.")
    elif result["tool"] == "Traceroute":
        lines.append(f"Observed {len(data)} hop(s). An asterisk is an unanswered probe; completion does not guarantee the destination was reached.")
        lines.extend(f"{h['hop']:2}  {h['details']}" for h in data)
    else:
        lines.append(f"DNS status: {data['status'] or 'Unavailable'}; answer records: {len(data['records'])}")
        lines.extend(f"{r['name']} {r['ttl']} {r['class']} {r['type']} {r['value']}" for r in data["records"])
        if data["status"] == "NOERROR" and not data["records"]:
            lines.append("The resolver returned no answers for this record type (NODATA).")
    return "\n".join(lines)
