"""Opt-in, real Nmap localhost test. Never scans external systems."""
import os
import shutil
import socket
import sys

import pytest

from app.core.scanner_service import ScannerService


@pytest.mark.skipif(os.environ.get("KALINET_LIVE_TESTS") != "1" or sys.platform != "linux"
                    or shutil.which("nmap") is None, reason="Requires opt-in KALINET_LIVE_TESTS=1, Linux, and Nmap")
def test_real_localhost_listener():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(16)
        port = listener.getsockname()[1]
        result = ScannerService().scan("127.0.0.1", mode="Custom TCP", ports=str(port), timeout=30)
        assert result["status"] == "Completed", result["error"]
        assert any(row["port"] == port and row["state"] == "open" for row in result["ports"])
