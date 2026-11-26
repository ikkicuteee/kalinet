# KaliNet — Network Diagnostics and Security Toolkit

CIT 244 Linux Final Project. Native Python/Tkinter desktop application for Kali Linux with Xfce, including Kali running inside VMware Workstation.

**KaliNet v0.5.0** adds a live ping monitor, persistent operation history and editable settings. See [Phase 5 verification](docs/PHASE5_VERIFICATION.md).

## Installation on Kali Linux

Copy the `kalinet` folder into your Kali home directory, so the entry point is `~/kalinet/main.py`. Run these commands in a Kali terminal:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk iproute2 iputils-ping traceroute dnsutils nmap
cd ~/kalinet
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Python 3.10 or newer is the project target. Run from an active Xfce desktop session as your normal user. Do not use `sudo python main.py`. Native Tkinter/ttk provides the charcoal, blue, and cyan interface without browser technology or optional styling dependencies. ttk panels use rectangular native geometry.

KaliNet reads `/etc/resolv.conf` and supplements it with `resolvectl dns` and NetworkManager's `nmcli` when available. Missing optional utilities are not dashboard errors. Each source is labeled in Routing & DNS; the combined list may contain both local stub and upstream servers, and is not a claim about resolver priority. Do not install systemd-resolved or change your DNS services for this application.

To upgrade an existing installation, run these commands inside Kali.

```bash
cd ~/kalinet
git pull --ff-only origin main
sudo apt install -y nmap python3-tk iputils-ping
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Matplotlib provides the latency graph. SQLite is included with Kali’s Python.

## Launch on subsequent sessions

```bash
cd ~/kalinet
source .venv/bin/activate
python main.py
```

## Implemented behavior

- Seven sidebar destinations, top header, manual refresh, collection status and progress indicator.
- Hostname; inferred active interface; IPv4 address; default gateway; DNS; interface and listening-socket counts.
- Interface table with IPv4/IPv6, MAC and operational state.
- Routing/DNS details, raw link statistics and per-interface traffic counters.
- The dashboard probes on refresh. Start Network Monitor for periodic probes, measured packet loss, a latency graph and timestamped CSV history.
- Reports retains completed operations from all four modules for later viewing and export.
- Partial results with warnings when commands fail; rotating logs; validated JSON configuration.
- Background collection with a main-thread event queue and shutdown cancellation.
- Ping with configurable packet count and loss/latency summaries; traceroute with numbered hops; DNS lookup with a record-type selector and response status.
- Validated single targets, command output, cancellation and partial results after timeout. The diagnostic timestamp records the last completed attempt in this session, including failed or cancelled attempts.
- Single-host Nmap TCP connect scanning: Quick, Standard, Custom TCP ports and optional service detection. Hostnames are resolved to one pinned IP; each non-loopback scan requires authorization confirmation.
- Scrollable port results, duration/status/open count, cancel controls, and scan-only CSV/TXT/JSON exports. Incomplete XML is retained as diagnostic output, not reported as completed port results.

Listening-socket count includes TCP listeners and UDP bound sockets, with separate IPv4/IPv6 entries. It is not a count of unique port numbers. The Local sockets tab exposes `ss -H -lntu` output for comparison with `ss -tuln`: zero is valid when no entries exist, while failures show unavailable. Active interface selection is a default-route heuristic; policy routing and multi-homed systems may require inspecting the detailed route table. Traffic counters are cumulative since interface/system initialization, not throughput rates.

## Configuration and logs

First launch creates `~/.config/kalinet/settings.json`, respecting an absolute `XDG_CONFIG_HOME` override. The packaged `config/default_settings.json` documents the defaults; the application defaults live in `config_service.py`, with a test ensuring the two agree.

Edit defaults in Settings and save them for future operations.

| Setting | Allowed values | Current use |
| --- | --- | --- |
| `command_timeout` | Integer 1–60 seconds | Snapshot, diagnostics and monitor commands. Scanner timeout is configured separately. |
| `ping_count` | Integer 1–20 | Default diagnostic packet count |
| `monitor_interval` | Integer 1–3600 seconds | Delay after each completed probe |
| `monitor_target` | Hostname or IP address | Defaults to `127.0.0.1`, including for existing configurations |
| `report_directory` | Absolute path or `~/…` | Reports and monitor export directory, initial directory for scanner exports |
| `theme` | `dark` | Current theme |

Invalid configuration is preserved and defaults are loaded with a warning visible in Settings and the log. Settings writes use a temporary file and atomic replacement. Logs reside at `~/.local/state/kalinet/kalinet.log`, respecting an absolute `XDG_STATE_HOME` override; rotation keeps up to three 1 MB backups. Logs may contain local interface details or command errors. No passwords are requested or stored.

## Tests

```bash
cd ~/kalinet
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m compileall -q main.py app tests
```

Tests use mocked measurements for deterministic failure conditions. A real loopback ping test runs on Linux with ping installed. The Nmap integration test requires explicit opt-in. See the [test plan](docs/TEST_PLAN.md).

## Project map

```text
main.py                       Linux entry point
app/gui/                      Native desktop shell and seven module views
app/core/network_utils.py     Linux snapshot collection and parsing
app/core/diagnostics_service.py Ping/traceroute/dig and result parsing
app/core/scanner_service.py   Authorized single-address Nmap execution and safe XML parsing
app/core/report_service.py    Persistent SQLite history and TXT/CSV/JSON exports
app/core/monitor_service.py   Serial ping worker, samples and session statistics
app/core/config_service.py    Configuration validation and persistence
app/utils/command_runner.py   Safe, bounded, cancellable subprocess execution
app/utils/validators.py       Single hostname/IP and packet-count validation
app/utils/logger.py           Rotating per-user logs
config/default_settings.json  Documented default configuration
tests/                        Mocked unit tests
docs/                         Design, user manual, tests and demo checklist
```

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `No module named tkinter` | Install `python3-tk` using apt. |
| `No module named psutil` | Activate `.venv`, then install `requirements.txt`. |
| Cannot open desktop window | Run within Kali Xfce, not a headless terminal/SSH session. |
| Required utility missing | Install the packages above; inspect the warning for the utility name. |
| `No module named defusedxml` | Activate `.venv` and reinstall `requirements.txt`. |
| Scan timed out | Use Quick or fewer custom ports, disable service detection, or increase the scanner timeout up to 120 seconds. |
| No IPv4/default gateway | Check VMware's virtual NIC is connected and Kali's NetworkManager connection is active. |
| Internet probe gets no reply | Inspect routes and VMware NAT/bridged settings; ICMP may be filtered. |
| DNS details mention an inactive provider | Existing resolver-file data is still retained; installing systemd-resolved is unnecessary. |
| Traceroute stops before reaching target | Increase `command_timeout` up to 60 seconds in user settings and restart. Asterisks indicate unanswered probes. |
| Slow refresh | Timeout is per command; collection performs several commands sequentially. Navigation remains available. |
| Cannot initialize log/config storage | Check permissions and free space in the user's XDG directories. |

## Academic documentation and authorship

[Design](docs/DESIGN.md), [User manual](docs/USER_MANUAL.md), [Test plan](docs/TEST_PLAN.md), and [Demonstration checklist](docs/DEMO_CHECKLIST.md) accompany this milestone.

Student author: **[Add your name]**. Course/section/instructor: **[Add your details]**. These placeholders intentionally avoid inventing personal details. Review and understand the generated implementation before submitting it, and follow your course's disclosure requirements. License: MIT; see [LICENSE](LICENSE).
