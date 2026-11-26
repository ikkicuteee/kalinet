# Phase 4 — Nmap scanner acceptance on Kali

This is a procedure, not a claim of live verification. The development host is Windows without Nmap; no external targets were scanned during development.

## Install/update

Run inside the Kali desktop as your normal user:

```bash
cd ~/kalinet
git pull origin main
sudo apt update
sudo apt install -y nmap
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python main.py
```

Do not launch KaliNet with sudo. The new Python dependency is `defusedxml` from requirements.txt. If starting a new installation, follow README.md for Python/Tkinter and the other utilities.

## Controlled localhost check

In a separate terminal, start a temporary HTTP listener:

```bash
python3 -m http.server 8765 --bind 127.0.0.1
```

In KaliNet choose Port Scanner → target `127.0.0.1` → Custom TCP → ports `8765` → Start Scan. Expect TCP 8765 open. Repeat with service detection enabled; version details depend on Nmap identifying the service. Stop the server with Ctrl+C, rerun and expect closed (unless another process binds the port). Use another unused port if 8765 is occupied.

Equivalent terminal command:

```bash
nmap --unprivileged -sT -Pn -n -p 8765 -oX - 127.0.0.1
```

The opt-in automated integration test opens its own temporary listener and scans only that one localhost TCP port:

```bash
KALINET_LIVE_TESTS=1 python -m pytest -q tests/test_scanner_integration.py
```

## Acceptance checklist

1. Run Quick and Standard against `127.0.0.1`; compare result scope with the selected mode.
2. Test `::1` and `localhost`. `localhost` deliberately maps to IPv4 loopback; `::1` explicitly selects IPv6.
3. Enter one **owned or explicitly authorized lab hostname/IP**. Decline authorization and verify no scan starts. Repeat and confirm; inspect the single resolved IP in the summary. Never use arbitrary third-party targets for this check.
4. Reject `0`, `65536`, `90-80`, `80,`, and `80;id` as Custom ports. Reject CIDRs, URLs and command-option target input.
5. Cancel a running scan. If localhost completes too fast, use a larger custom port selection with service detection on your authorized lab target. Confirm navigation remains responsive and duplicate Start clicks do not launch another scan.
6. Use a short timeout to exercise interruption when a scan runs long enough. Do not expect every localhost scan to time out. Check status, preserved raw output and unavailable open count on interruption.
7. Export CSV/TXT/JSON into a selected directory; inspect timestamps, target, resolved address, status and port data. Export a no-open-ports result and a failed attempt too. Try a directory without write permission to verify a readable failure and retry.
8. Close the GUI during scanning and confirm its Nmap process exits. Check the log for failures.
9. Repeat Dashboard, Network Information, Ping, Traceroute and DNS Lookup checks to verify regression behavior in Kali/Xfce.

Nmap may group closed/filtered ports instead of emitting individual rows. Grouped states appear in Details and exports. `-Pn` skips discovery, so host “up” is not proof of reachability. A timed-out/cancelled scan is not a completed security assessment.

Record Kali/Python/Nmap versions, VMware network mode, commands, results and pass/fail in TEST_PLAN.md. Do not proceed to Phase 5 until instructed.
