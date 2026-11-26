# KaliNet design document

## Problem and objectives

Students diagnosing a Kali VM network must otherwise move between several terminal utilities and interpret their output independently. KaliNet presents these observations in a single native desktop interface, makes failures readable, and keeps network operations separate from presentation.

KaliNet combines configuration inspection, diagnostics, single-host scanning, monitoring and reporting in one native desktop application.

## Requirements and milestone boundaries

| Module | Required behavior | Current milestone |
| --- | --- | --- |
| Desktop shell | Dark theme, seven pages, header, progress, responsive navigation | Implemented |
| Dashboard | Host, interface, address, gateway, DNS, connectivity and counts | Implemented; diagnostic timestamp tracks last completed attempt |
| Network information | Addresses, MAC, states, routing, DNS and traffic counters | Implemented |
| Diagnostics | Validated ping, traceroute and DNS lookup | Implemented; Kali acceptance pending |
| Scanner | Authorized single-host Nmap scan, safe XML, cancellation | Implemented; Kali acceptance pending |
| Monitor/general reports | Serial ping probes, latency graph, history and exports | Implemented in Phase 5 |
| Settings | Editable, validated per-user JSON defaults | Implemented |

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
| `/etc/resolv.conf` | Existing resolver configuration; may show a stub |
| `nmcli --terse --escape no --fields IP4.DNS,IP6.DNS device show` | Optional NetworkManager DNS data, labeled separately |
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

Diagnostics validate a single ASCII hostname or IPv4/IPv6 literal before constructing argument lists. Prefix options, shell syntax, URLs, ranges and scoped IPv6 input are rejected. A separate diagnostics worker communicates through a queue and supports cancellation; application shutdown waits for both collection and diagnostic workers. The command runner preserves captured output on timeout, cancellation and nonzero exit. Parsers extract packet summaries, hop observations and DNS answer records while retaining raw output. DNS response codes are checked independently of dig's process exit status. One diagnostic is allowed at a time.

`ScannerService` validates targets, modes, timeout and ports, and requires authorization for non-loopback targets independently of the GUI. Hostname resolution runs in a bounded, cancellable Python child; exactly one returned IP (IPv4 preferred) is passed to Nmap. The scan uses `--unprivileged -sT -Pn -n -oX -`, optionally `-6`, `-F`, `-p` or `-sV`. No raw option input, scripts, exploitation, credential operations or host ranges are exposed. A service lock and GUI busy state prevent concurrent scans. Scan timeout is a total 1–120 seconds including DNS resolution.

`defusedxml` rejects entity expansion/external entities. Parsing enforces the Nmap root, a successful completion marker, at most one host and valid TCP port entries; XML over 16 MB is rejected. Grouped states are retained separately. Truncated/cancelled XML remains raw diagnostic output and does not produce a completed result or zero open count. A typed timeout exception extends the existing runner without changing diagnostics behavior.

The scanner retains its own worker and exporter. Snapshot, diagnostic and scan completion also submit records to Reports. A single executor writes metadata and the original result atomically to SQLite, reads history in pages and exports results off the Tk thread. Both export paths share exclusive file creation, cleanup on failure and CSV escaping.

The monitoring worker runs a cancellable ping and waits on the stop event between probes. The Tk thread consumes queued samples, updates statistics and draws the latest measurements. On normal shutdown the application drains the last monitor event and waits for pending writes. Abrupt termination can lose samples from the active session.

The settings editor uses the existing validator and atomic JSON replacement. Older configurations inherit a default monitor target. Changes apply after the file is saved successfully.

## Visual design

Charcoal background, navy panels, cyan accents, readable system fonts, padded controls, persistent navigation, scrollable tables/text and indeterminate progress. Native ttk uses rectangular panels. The minimum window is 960×720; a VMware guest resolution of at least 1280×800 is recommended for the demonstration. Xfce visual acceptance remains a manual test.
