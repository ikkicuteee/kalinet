# KaliNet — Network Diagnostics and Security Toolkit

CIT 244 Linux Final Project. Native Python/Tkinter desktop application for Kali Linux with Xfce, including Kali running inside VMware Workstation.

**Current milestone: Phases 1 and 2.** Dashboard and network information are implemented. Diagnostics, Nmap scanning, continuous monitoring, report exports, and the settings editor are not yet implemented. Their navigation pages state this explicitly. No results are simulated.

## Installation on Kali Linux

Copy the `kalinet` folder into your Kali home directory, so the entry point is `~/kalinet/main.py`. Run these commands in a Kali terminal:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-tk iproute2 iputils-ping
cd ~/kalinet
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

Python 3.10 or newer is the project target. Run from an active Xfce desktop session as your normal user. Do not use `sudo python main.py`. Native Tkinter/ttk provides the charcoal, blue, and cyan interface without browser technology or optional styling dependencies. ttk panels use rectangular native geometry.

`resolvectl` is optional: if it is missing or its service is inactive, KaliNet reads `/etc/resolv.conf`. This may show a local stub resolver rather than an upstream server. Do not change your system DNS services merely to enable this optional information source.

For later milestones, the planned utility packages are:

```bash
sudo apt install -y traceroute dnsutils nmap
```

Installing these packages does not enable the unfinished pages.

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
- A single ICMP Internet probe to `1.1.1.1` on startup and each refresh. It sends real traffic; there is no continuous monitoring yet. No reply may indicate ICMP filtering rather than an Internet outage.
- Partial results with warnings when commands fail; rotating logs; validated JSON configuration.
- Background collection with a main-thread event queue and shutdown cancellation.

Listening-socket count includes TCP listeners and UDP bound sockets, with separate IPv4/IPv6 entries. It is not a count of unique port numbers. Active interface selection is a default-route heuristic; policy routing and multi-homed systems may require inspecting the detailed route table. Traffic counters are cumulative since interface/system initialization, not throughput rates. Last diagnostic/scan remains “Not run” until those modules exist; snapshot time is displayed separately.

## Configuration and logs

First launch creates `~/.config/kalinet/settings.json`, respecting an absolute `XDG_CONFIG_HOME` override. The packaged `config/default_settings.json` documents the defaults; the application defaults live in `config_service.py`, with a test ensuring the two agree.

Edit the user JSON while the application is closed. Validation requires:

| Setting | Allowed values | Current use |
| --- | --- | --- |
| `command_timeout` | Integer 1–60 seconds | Per Linux command |
| `ping_count` | Integer 1–20 | Reserved for Phase 3 |
| `monitor_interval` | Integer 1–3600 seconds | Reserved for Phase 5 |
| `report_directory` | Absolute path or `~/…` | Reserved for Phase 5 |
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

Tests use mocked processes and network counters, with no network probes. They cover command timeout, cancellation, missing utilities, permission errors, interface/DNS parsing, partial collection, configuration validation and persistence. The later hostname/IP-input, diagnostic parsing, Nmap XML, and report tests will be added with those modules. See [TEST_PLAN.md](docs/TEST_PLAN.md) for verification status and Kali acceptance tests.

## Project map

```text
main.py                       Linux entry point
app/gui/                      Desktop shell, dashboard, network view, placeholders
app/core/network_utils.py     Linux snapshot collection and parsing
app/core/config_service.py    Configuration validation and persistence
app/utils/command_runner.py   Safe, bounded, cancellable subprocess execution
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
| No IPv4/default gateway | Check VMware's virtual NIC is connected and Kali's NetworkManager connection is active. |
| Internet probe gets no reply | Inspect routes and VMware NAT/bridged settings; ICMP may be filtered. |
| `resolvectl` warning | The `/etc/resolv.conf` fallback is expected on systems without systemd-resolved. |
| Slow refresh | Timeout is per command; collection performs several commands sequentially. Navigation remains available. |
| Cannot initialize log/config storage | Check permissions and free space in the user's XDG directories. |

## Academic documentation and authorship

[Design](docs/DESIGN.md), [User manual](docs/USER_MANUAL.md), [Test plan](docs/TEST_PLAN.md), and [Demonstration checklist](docs/DEMO_CHECKLIST.md) accompany this milestone.

Student author: **[Add your name]**. Course/section/instructor: **[Add your details]**. These placeholders intentionally avoid inventing personal details. Review and understand the generated implementation before submitting it, and follow your course's disclosure requirements. License: MIT; see [LICENSE](LICENSE).
