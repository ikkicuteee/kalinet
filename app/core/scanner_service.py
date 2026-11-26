"""Authorized, single-address, unprivileged Nmap scanning."""
from datetime import datetime
import ipaddress
import json
import logging
import re
import socket
import sys
import threading
import time

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from xml.etree.ElementTree import ParseError

from app.utils.command_runner import CommandCancelled, CommandError, CommandRunner, CommandTimedOut
from app.utils.validators import validate_ports, validate_target

LOG = logging.getLogger("kalinet.scanner")
SCAN_MODES = ("Quick", "Standard", "Custom TCP")
# DNS resolution runs in a cancellable child; getaddrinfo in a thread cannot be stopped.
RESOLVE_SCRIPT = "import socket,json,sys; print(json.dumps([r[4][0] for r in socket.getaddrinfo(sys.argv[1],None,0,socket.SOCK_STREAM)]))"


def is_local_target(target):
    target = validate_target(target)
    if target.rstrip(".") == "localhost":
        return True
    try:
        address = ipaddress.ip_address(target)
        return address.is_loopback or (address.version == 6 and address.ipv4_mapped is not None
                                       and address.ipv4_mapped.is_loopback)
    except ValueError:
        return False


def validate_scan(target, mode, ports, service_detection, timeout, authorized):
    target = validate_target(target)
    if re.fullmatch(r"[0-9.-]+", target) and "-" in target:
        raise ValueError("Host address ranges are not supported; enter one host.")
    if not is_local_target(target) and authorized is not True:
        raise ValueError("Explicit authorization is required for each non-local lab target.")
    if mode not in SCAN_MODES:
        raise ValueError("Choose Quick, Standard, or Custom TCP.")
    if type(service_detection) is not bool:
        raise ValueError("Service detection must be enabled or disabled.")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("Scan timeout must be an integer from 1 to 120 seconds.")
    ports = validate_ports(ports) if mode == "Custom TCP" else ""
    return target, ports


def parse_nmap_xml(output):
    if not output.strip():
        raise ValueError("Nmap returned no XML; scan results are unavailable.")
    if len(output) > 16_000_000:
        raise ValueError("Nmap XML exceeds the 16 MB parsing limit.")
    try:
        root = ElementTree.fromstring(output, forbid_entities=True, forbid_external=True)
    except (ParseError, DefusedXmlException) as exc:
        raise ValueError(f"Invalid or unsafe Nmap XML: {exc}") from exc
    if root.tag != "nmaprun":
        raise ValueError("Expected Nmap XML output.")
    hosts = root.findall("host")
    if len(hosts) > 1:
        raise ValueError("Unexpected multiple-host scan output.")
    finished = root.find("runstats/finished")
    if finished is None or finished.get("exit") != "success":
        raise ValueError("Nmap did not report a successful completion in XML.")
    rows, grouped = [], []
    for host in hosts:
        for port in host.findall("ports/port"):
            try:
                number = int(port.get("portid", ""))
            except ValueError as exc:
                raise ValueError("Invalid port number in Nmap XML.") from exc
            state = port.find("state")
            if not 1 <= number <= 65535 or port.get("protocol") != "tcp" or state is None:
                raise ValueError("Invalid TCP port entry in Nmap XML.")
            service = port.find("service")
            version = "" if service is None else " ".join(filter(None, (
                service.get("product"), service.get("version"), service.get("extrainfo"))))
            rows.append(dict(port=number, protocol="tcp", state=state.get("state", "unknown"),
                             service=service.get("name", "") if service is not None else "",
                             version=version))
        for extra in host.findall("ports/extraports"):
            count = int(extra.get("count", "0"))
            if count < 0 or count > 65535:
                raise ValueError("Invalid grouped port count in Nmap XML.")
            grouped.append(dict(state=extra.get("state", "unknown"), count=count))
    host_state = hosts[0].find("status") if hosts else None
    return dict(ports=sorted(rows, key=lambda row: row["port"]), grouped_ports=grouped,
                open_ports=sum(row["state"] == "open" for row in rows) +
                sum(item["count"] for item in grouped if item["state"] == "open"),
                host_state=host_state.get("state", "unknown") if host_state is not None else "not reported")


class ScannerService:
    def __init__(self, runner=None):
        self.runner = runner or CommandRunner()
        self._lock = threading.Lock()

    def _resolve(self, target, deadline, cancel):
        if target.rstrip(".") == "localhost":
            return "127.0.0.1"
        try:
            return str(ipaddress.ip_address(target))
        except ValueError:
            result = self.runner.run([sys.executable, "-c", RESOLVE_SCRIPT, target],
                                     timeout=self._remaining(deadline), cancel=cancel)
            addresses = json.loads(result.stdout)
            if not isinstance(addresses, list) or not addresses:
                raise ValueError("Hostname did not resolve to an address.")
            parsed = [ipaddress.ip_address(address) for address in addresses]
            parsed.sort(key=lambda address: address.version)  # Prefer IPv4; scan exactly one address.
            return str(parsed[0])

    @staticmethod
    def _remaining(deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CommandTimedOut("Scan timed out.")
        return min(remaining, 120)

    def scan(self, target, mode="Quick", ports="", service_detection=False,
             timeout=120, authorized=False, cancel=None):
        target, ports = validate_scan(target, mode, ports, service_detection, timeout, authorized)
        if not self._lock.acquire(blocking=False):
            raise ValueError("A scan is already running.")
        start = time.monotonic()
        record = dict(title="KaliNet Port Scan", module="Port Scanner", hostname=socket.gethostname(),
                      target=target, resolved_target=None, mode=mode, custom_ports=ports,
                      service_detection=service_detection, authorized=authorized,
                      started_at=datetime.now().astimezone().isoformat(timespec="seconds"),
                      status="Failed", error=None, ports=[], grouped_ports=[], open_ports=None,
                      host_state="unknown", stdout="", stderr="", args=[], returncode=None)
        try:
            if cancel is not None and cancel.is_set():
                raise CommandCancelled("Scan cancelled.")
            address = self._resolve(target, start + timeout, cancel)
            parsed = ipaddress.ip_address(address)
            effective = parsed.ipv4_mapped if parsed.version == 6 and parsed.ipv4_mapped else parsed
            if effective.is_multicast or effective.is_unspecified or str(effective) == "255.255.255.255":
                raise ValueError("Use a single unicast lab host, not multicast, unspecified, or broadcast addresses.")
            record["resolved_target"] = address
            args = ["nmap", "--unprivileged", "-sT", "-Pn", "-n", "-oX", "-"]
            if parsed.version == 6:
                args.append("-6")
            if mode == "Quick":
                args.append("-F")
            elif mode == "Custom TCP":
                args.extend(["-p", ports])
            if service_detection:
                args.append("-sV")
            args.append(address)
            record["args"] = args
            result = self.runner.run(args, timeout=self._remaining(start + timeout), cancel=cancel)
            record.update(stdout=result.stdout, stderr=result.stderr, returncode=result.returncode)
            record.update(parse_nmap_xml(result.stdout))
            record["status"] = "Completed"
        except (CommandError, ValueError, TypeError) as exc:
            record["error"] = str(exc)
            record["status"] = ("Cancelled" if isinstance(exc, CommandCancelled) else
                                "Timed out" if isinstance(exc, CommandTimedOut) else "Failed")
            if isinstance(exc, CommandError) and exc.result is not None:
                record.update(stdout=exc.result.stdout, stderr=exc.result.stderr, returncode=exc.result.returncode)
            LOG.warning("Scan %s: %s", target, exc)
        finally:
            record["duration_seconds"] = round(time.monotonic() - start, 3)
            record["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            self._lock.release()
        return record
