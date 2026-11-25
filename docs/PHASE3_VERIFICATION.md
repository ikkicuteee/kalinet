# Phase 3 — Kali acceptance procedure

Run these steps **inside the Kali VMware guest**, as a normal desktop user. The development session was on Windows; it did not have access to this guest. This document is a procedure, not a claim that live commands passed.

## Install and start

Copy the updated project to `~/kalinet` (or substitute your checkout location). Do not copy a Windows `.venv` into Linux; use the Kali virtual environment.

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk iproute2 iputils-ping traceroute dnsutils
cd ~/kalinet
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python main.py
```

No systemd-resolved installation is required. Dependencies in the requirements files are unchanged.

## Verify the two dashboard observations

In a second guest terminal:

```bash
cat /etc/resolv.conf
command -v nmcli && nmcli --terse --escape no --fields IP4.DNS,IP6.DNS device show
command -v resolvectl && resolvectl dns
ss -tuln
ss -H -lntu
ss -H -lntu | wc -l
```

Refresh the GUI and compare Routing & DNS source labels. An absent optional resolver tool should no longer produce a dashboard warning. A local stub server and upstream servers may both appear; source labels distinguish them. The combined list is not resolver priority, and NetworkManager can report servers from multiple devices.

The original `ss -H -lntu` command selects the same TCP/UDP sockets as `ss -tuln`; option order does not change selection and `-H` removes the header. No incorrect counting has been established in the guest. The revised code validates each row and exposes raw output under Network Information → Local sockets. A successfully empty result is zero; execution/parsing failure is unavailable. Compare observations close in time because sockets can change.

For a controlled TCP listener, start this in another terminal and leave it running:

```bash
cd ~/kalinet
.venv/bin/python -m http.server 8765 --bind 127.0.0.1
```

Refresh KaliNet and confirm `127.0.0.1:8765` appears in Local sockets and `ss -tuln`. Stop the server with Ctrl+C, then refresh. If the port is already occupied, choose another unused local port. Do not treat unrelated concurrent socket changes as a counting defect.

## Compare diagnostics with terminal commands

```bash
ping -n -c 4 -W 2 127.0.0.1
ping -n -c 4 -W 2 ::1
traceroute -n -m 30 -q 1 -w 1 127.0.0.1
traceroute -n -m 30 -q 1 -w 1 -6 ::1
dig +time=2 +tries=1 example.com A
dig +time=2 +tries=1 example.com AAAA
dig +time=2 +tries=1 nonexistent-kalinet.invalid A
```

Repeat these targets/types in the GUI. Latencies and DNS records can vary between runs. Verify ping packet totals/loss, hop addresses/times, DNS statuses and complete raw output. A responsive resolver should return NXDOMAIN for the `.invalid` name; resolver/network failure is a different valid error outcome.

## Error handling and lifecycle

1. Enter `example.com; id`, `-c`, `999.1.1.1`, a URL, and a CIDR range. Each must be rejected before a process starts.
2. Set Ping to 20 packets and run localhost with the default 10-second command timeout. It should time out with captured partial output; completed packet statistics may be absent.
3. Run 20 packets again, click Stop, and inspect the cancellation message and raw output.
4. Navigate to Dashboard and Network Information during a diagnostic; refresh should still work. Repeated Run clicks must not create multiple diagnostics.
5. Close the window during a running diagnostic. Confirm the GUI and its command exit.
6. To test missing utilities without changing the OS, start from the project directory with `PATH=/nonexistent "$PWD/.venv/bin/python" main.py`, then run each diagnostic. Restore normal launch afterward.
7. Disconnect the VMware NIC and test an external target, then reconnect. Expect useful no-reply, resolver, unreachable, or timeout feedback—not a frozen window. Loopback tests should remain independent of the virtual NIC.
8. Confirm the dashboard's last diagnostic timestamp survives dashboard refresh in the same session and resets on relaunch.

Record actual Kali/Python versions, network mode, output and pass/fail in TEST_PLAN.md. Phase 4 is deferred until this acceptance run is reviewed.
