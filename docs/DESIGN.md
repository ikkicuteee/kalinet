# KaliNet design document

## Problem and objectives

Students diagnosing a Kali VM network must otherwise move between several terminal utilities and interpret their output independently. KaliNet presents these observations in a single native desktop interface, makes failures readable, and keeps network operations separate from presentation.

The complete project aims to support configuration inspection, connectivity diagnostics, authorized single-host scanning, periodic monitoring and exportable reports without requiring manual terminal commands for normal use. This milestone implements only the desktop foundation and configuration inspection.

## Requirements and milestone boundaries

| Module | Required behavior | Current milestone |
| --- | --- | --- |
| Desktop shell | Dark theme, seven pages, header, progress, responsive navigation | Implemented |
| Dashboard | Host, interface, address, gateway, DNS, connectivity and counts | Implemented; diagnostic timestamp reserved |
| Network information | Addresses, MAC, states, routing, DNS and traffic counters | Implemented |
| Diagnostics | Validated ping, traceroute and DNS lookup | Phase 3 |
| Scanner | Authorized literal single-IP Nmap scan, XML, cancellation | Phase 4 |
| Monitor/reports | Periodic history, CSV/TXT/JSON exports | Phase 5 |
| Settings | Per-user JSON configuration, validation, editor | Persistence implemented; editor Phase 5 |

Nonfunctional requirements include least privilege, bounded subprocess lifetime, no shell execution, no worker-thread Tk calls, readable errors, logs, modular code, and documented evidence of testing. Live Linux observations are never replaced with sample results.

## Architecture

```text
main.py
  ├── logging initialization
  └── MainWindow (Tk main thread)
        ├── ConfigService → per-user JSON
        ├── DashboardPage / NetworkInfoPage / remaining page containers
        └── network worker → NetworkService
                              ├── CommandRunner → Linux subprocesses
                              ├── /etc/resolv.conf fallback
                              └── psutil counters
              ↓ queue of data/errors
          main-thread after() poll → update views
```

`CommandRunner` accepts argument lists, resolves executables, uses `shell=False`, sets `LC_ALL=C`, captures output, checks allowed return codes and applies deadlines. It polls `communicate()` in short intervals for cancellation, kills and reaps an unfinished direct child in `finally`, and translates failures into readable exceptions. Current commands do not intentionally launch descendants; future commands that spawn process trees would need process-group cancellation.

`NetworkService` collects one snapshot and records individual source failures as warnings. It re-raises cancellation immediately. Data sources are read sequentially and are not a transactionally consistent kernel snapshot. Default routes are ranked by address family and metric, then matched to an interface; an UP non-loopback interface is a fallback. No route means the gateway remains unavailable.

The GUI schedules exactly one collection worker at a time. Repeated refresh clicks during collection do not launch more workers. Workers send plain data through a queue; only the GUI thread touches widgets. Closing sets a cancellation event and polls for worker completion before destroying the window. No root prompt or credential storage exists.

## Commands and data interpretation

| Source | Purpose |
| --- | --- |
| `ip -j addr` | Parse interface states, MAC, IPv4 and IPv6 addresses |
| `ip -j route` / `ip -j -6 route` | Inspect main IPv4/IPv6 route tables |
| `ip -s link` | Show raw link counters and status |
| `resolvectl dns` | Retrieve per-link/system resolver addresses if available |
| `/etc/resolv.conf` | DNS nameserver fallback; may show a stub |
| `ss -H -lntu` | Count TCP listening and UDP bound socket entries |
| `ping -n -c 1 -W 2 1.1.1.1` | Single bounded ICMP connectivity observation |
| `psutil.net_io_counters(pernic=True)` | Cumulative bytes, packets, errors and drops |

An ICMP response is evidence that one external IP is reachable, not proof that DNS or web access works. No reply is inconclusive about general connectivity. TCP/UDP socket rows are not deduplicated ports. psutil counters and `ip` output may differ slightly because they are collected at different times.

## Workflow and failure behavior

1. Validate Linux platform and initialize rotating logging.
2. Load validated settings, or retain the invalid file and use defaults with a warning.
3. Build the dashboard and schedule an initial collection.
4. Collect network observations in a worker while navigation stays responsive.
5. Display the snapshot, warning list and collection timestamp.
6. Refresh manually or close; closure cancels pending subprocess work.

Missing information is shown as unavailable. The GUI does not infer zero listeners from a failed `ss` command. Unexpected collection/callback exceptions are logged; ordinary source failures retain other results. Initial log-path failure produces a terminal error instead of silently losing logging.

## Planned security boundary

Later diagnostics require hostname/IP validation before constructing argument lists. Later scans will accept loopback or one literal IP address, require explicit authorization for non-loopback targets, use unprivileged TCP connect scans and safe XML parsing, and forbid ranges, stealth/exploits and credentials. These are requirements for later milestones, not implemented features of this release.

## Visual design

Charcoal background, navy panels, cyan accents, readable system fonts, padded controls, persistent navigation, scrollable tables/text and indeterminate progress. Native ttk uses rectangular panels. The minimum window is 960×720; a VMware guest resolution of at least 1280×800 is recommended for the demonstration. Xfce visual acceptance remains a manual test.
