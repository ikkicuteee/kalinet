"""Strict single-target validation; never accept command options or shell syntax."""
import ipaddress
import re


def validate_target(value):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("Enter one hostname or IP address without surrounding whitespace.")
    if any(c.isspace() for c in value) or any(c in value for c in "%/\\\x00"):
        raise ValueError("Enter one hostname or IP address, without a URL, range, or zone suffix.")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    # Reject malformed IP-like input instead of silently treating it as a hostname.
    if ":" in value or re.fullmatch(r"[0-9.]+", value):
        raise ValueError("Invalid IP address.")
    name = value[:-1] if value.endswith(".") else value
    if not name.isascii() or len(name) > 253 or not name:
        raise ValueError("Use an ASCII hostname (or its punycode form), up to 253 characters.")
    label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    if any(not re.fullmatch(label, part) for part in name.split(".")):
        raise ValueError("Hostname labels must contain letters, digits, or internal hyphens.")
    return value.lower()


def validate_count(value):
    if type(value) is not int or not 1 <= value <= 20:
        raise ValueError("Packet count must be an integer from 1 to 20.")
    return value
