"""Read Linux network state. Collection tolerates failures of individual sources."""
from datetime import datetime
import ipaddress
import json
import logging
from pathlib import Path
import socket

import psutil

from app.utils.command_runner import CommandCancelled, CommandError, CommandRunner

LOG = logging.getLogger("kalinet.network")
PROBE_TARGET = "1.1.1.1"


def json_objects(output):
    value = json.loads(output)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("Expected a JSON array of objects.")
    return value


def parse_interfaces(output):
    interfaces = []
    for item in json_objects(output):
        name = item.get("ifname")
        if not isinstance(name, str) or not name:
            raise ValueError("Interface entry has no valid name.")
        addresses = item.get("addr_info", [])
        if not isinstance(addresses, list) or any(not isinstance(a, dict) for a in addresses):
            raise ValueError(f"Invalid address data for {name}.")
        interfaces.append({
            "name": name, "state": item.get("operstate", "UNKNOWN"),
            "mac": item.get("address", "Unavailable"),
            "ipv4": [f"{a['local']}/{a['prefixlen']}" for a in addresses
                     if a.get("family") == "inet" and "local" in a and "prefixlen" in a],
            "ipv6": [f"{a['local']}/{a['prefixlen']}" for a in addresses
                     if a.get("family") == "inet6" and "local" in a and "prefixlen" in a],
        })
    return interfaces


def parse_nameservers(output, resolvectl=False):
    servers = []
    for line in output.splitlines():
        if resolvectl:
            if ":" not in line:
                continue
            tokens = line.split(":", 1)[1].split()
        else:
            tokens = line.split("#", 1)[0].split()
            tokens = tokens[1:2] if tokens and tokens[0] == "nameserver" else []
        for token in tokens:
            token = token.split("#", 1)[0]
            try:
                ipaddress.ip_address(token.split("%", 1)[0])
            except ValueError:
                continue
            if token not in servers:
                servers.append(token)
    return servers


class NetworkService:
    def __init__(self, runner=None, resolv_conf=None):
        self.runner = runner or CommandRunner()
        self.resolv_conf = Path(resolv_conf or "/etc/resolv.conf")

    def collect(self, timeout=10, cancel=None):
        snapshot = {
            "hostname": socket.gethostname(), "interfaces": [], "routes": [],
            "dns_servers": [], "dns_source": "Unavailable", "statistics": {},
            "link_statistics": "", "listening_ports": None, "active_interface": None,
            "ipv4": None, "gateway": None, "connectivity": "Unknown",
            "probe_target": PROBE_TARGET, "warnings": [],
        }

        def attempt(label, action, default=None):
            try:
                return action()
            except CommandCancelled:
                raise
            except (CommandError, OSError, ValueError, TypeError, KeyError) as exc:
                message = f"{label}: {exc}"
                snapshot["warnings"].append(message)
                LOG.warning(message)
                return default

        def run(args, accepted_codes=(0,)):
            return self.runner.run(args, timeout=timeout, cancel=cancel,
                                   accepted_codes=accepted_codes)

        snapshot["interfaces"] = attempt("Interfaces", lambda: parse_interfaces(
            run(["ip", "-j", "addr"]).stdout), [])
        snapshot["routes"] = attempt("IPv4 routes", lambda: json_objects(
            run(["ip", "-j", "route"]).stdout), [])
        snapshot["routes"].extend(attempt("IPv6 routes", lambda: json_objects(
            run(["ip", "-j", "-6", "route"]).stdout), []))
        snapshot["link_statistics"] = attempt("Link statistics", lambda:
            run(["ip", "-s", "link"]).stdout, "Unavailable")

        defaults = [r for r in snapshot["routes"] if r.get("dst") == "default"]
        # Prefer IPv4 defaults, then the route with the lowest metric.
        def route_rank(route):
            metric = route.get("metric", 0)
            if not isinstance(metric, (int, float)):
                metric = 0
            return (":" in str(route.get("gateway", "")), metric)
        defaults.sort(key=route_rank)
        interfaces = {i["name"]: i for i in snapshot["interfaces"]}
        chosen = next((r for r in defaults if r.get("dev") in interfaces and
                       interfaces[r["dev"]]["state"] != "DOWN"), None)
        active = interfaces.get(chosen.get("dev")) if chosen else next(
            (i for i in snapshot["interfaces"] if i["name"] != "lo" and i["state"] == "UP"), None)
        if active:
            snapshot["active_interface"] = active["name"]
            snapshot["ipv4"] = ", ".join(active["ipv4"]) or None
        if chosen:
            snapshot["gateway"] = chosen.get("gateway") or "Direct default route"

        # resolvectl may be installed without a running systemd-resolved service.
        dns = attempt("System resolver (falling back to resolv.conf if unavailable)",
                      lambda: parse_nameservers(run(["resolvectl", "dns"]).stdout, True), [])
        if dns:
            snapshot["dns_servers"], snapshot["dns_source"] = dns, "resolvectl dns"
        else:
            snapshot["dns_servers"] = attempt("DNS configuration", lambda:
                parse_nameservers(self.resolv_conf.read_text(encoding="utf-8")), [])
            snapshot["dns_source"] = str(self.resolv_conf)

        def counters():
            return {name: counter._asdict() for name, counter in
                    psutil.net_io_counters(pernic=True).items()}
        snapshot["statistics"] = attempt("Network counters", counters, {})
        # Each nonempty ss row is a TCP listener or bound UDP socket, not a unique port.
        snapshot["listening_ports"] = attempt("Local sockets", lambda:
            len([line for line in run(["ss", "-H", "-lntu"]).stdout.splitlines() if line.strip()]))
        probe = attempt("Connectivity probe", lambda:
            run(["ping", "-n", "-c", "1", "-W", "2", PROBE_TARGET], (0, 1)))
        if probe is not None:
            snapshot["connectivity"] = "Reachable" if probe.returncode == 0 else "No ICMP reply"
        snapshot["collected_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        return snapshot
