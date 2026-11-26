# KaliNet user manual — Phases 1–5

## Before launching

Install using the exact commands in [README](../README.md). Use your regular Kali desktop account. In VMware, ensure the guest network adapter is connected. NAT is typically sufficient for this milestone's Internet probe; no scanning is performed. KaliNet inspects the guest's interfaces, not the Windows host's adapters.

## Dashboard

Launch `python main.py` from the activated virtual environment. Collection begins automatically. Cards display hostname, active interface, IPv4, gateway, DNS, probe status, interface count and socket count. The diagnostic timestamp is initially “Not run”, then records the last completed diagnostic attempt in the current session, including errors/cancellations.

Select **Refresh Dashboard** or the header **Refresh** button to collect again. Progress animates while commands run. Multiple refresh clicks do not start concurrent collections. Warnings and interpretation notes appear below the cards. Snapshot time uses the Kali guest's local timezone.

## Network Information

Select **Network Information** in the sidebar. Its tabs share the same snapshot as the dashboard:

- **Interfaces:** names, operational states, MAC and IPv4/IPv6 addresses. `UNKNOWN` is a real kernel state and is common for loopback or virtual interfaces.
- **Traffic counters:** cumulative received/sent bytes and packets, errors and drops. Values are not bytes per second.
- **Routing & DNS:** default gateway, resolver source, configured servers, main route table entries and collection warnings.
- **Link details:** raw `ip -s link` output.
- **Local sockets:** raw `ss -H -lntu` output and count. Compare with `ss -tuln` in the same guest; exclude its header. Zero means no entries were returned; a failed command shows an unavailable count.

Tables have vertical and horizontal scrollbars. Read-only details can be selected and copied. Refresh either network page to update both pages.

## Connectivity interpretation

**Reachable** means the dashboard probe to `1.1.1.1` succeeded. **No ICMP reply** means ping finished without a response. **Unknown** means the probe could not complete. Network Monitor probes its selected target independently.

## Network Diagnostics

Select Ping, Traceroute, or DNS Lookup within the existing Network Diagnostics page. Enter a hostname or IPv4/IPv6 address, then select Run. Input rejects URLs, IP ranges, command options, spaces, shell syntax, and IPv6 zone suffixes. Internationalized hostnames must use punycode.

- **Ping:** choose 1–20 packets. Parsed results show transmitted/received packets, loss, min/average/max latency and deviation when available. The overall configured timeout can end a large packet count early; partial output remains available.
- **Traceroute:** uses numeric output, a 30-hop limit, one probe per hop and a one-second per-probe wait. Parsed results preserve hop addresses, response times, asterisks and error annotations. Command completion does not prove the destination was reached. IPv6 literals automatically select IPv6.
- **DNS Lookup:** queries with `dig` using the selected A, AAAA, MX, NS, TXT, CNAME, SOA or PTR type. Parsed results show DNS response status and answer-section records; the full authority/additional sections remain in Raw output. NXDOMAIN means no such name; SERVFAIL/REFUSED indicate resolver errors. NOERROR without answers means no records of that type. For PTR, enter a reverse DNS name such as `1.0.0.127.in-addr.arpa`.

Parsed results and Raw output are separate tabs. Raw output includes command arguments, exit status, stdout and stderr. Output appears on completion or cancellation, not as a live stream. Select Stop to cancel; commands also stop when the window closes. One diagnostic runs at a time, while sidebar navigation and dashboard refresh remain usable. The Settings command timeout (default 10 seconds, maximum 60) applies to the whole command; partial traceroutes are common on longer paths. Missing utilities produce a readable error; install `traceroute` and `dnsutils` as shown in the README.

## Port Scanner

Default target is `127.0.0.1`. Enter a single IPv4/IPv6 address or ASCII hostname, select a mode, and click Start Scan. Each non-loopback target prompts for explicit permission to scan that lab host. Declining starts no command. `localhost` maps to `127.0.0.1`; enter `::1` to test IPv6. Other hostnames resolve to exactly one address, preferring IPv4. The selected address is displayed and exported. Host ranges, CIDRs, URLs and command options are unsupported.

- **Quick:** Nmap `-F` common TCP port selection.
- **Standard:** Nmap's default TCP port selection.
- **Custom TCP:** comma-separated ports and ascending port ranges, e.g. `22,443,8000-8010`, within 1–65535. This field is ignored for other modes.
- **Service detection:** adds `-sV`; may take substantially longer and does not guarantee a version for every service.

All scans use `--unprivileged -sT -Pn -n`. Host discovery is skipped so blocked discovery probes do not prevent a TCP scan. Consequently an Nmap “up” status does not establish reachability. The result covers only selected ports; no open ports is not a claim that the host has no services.

The scanner has its own timeout of 1–120 seconds, initially 120, covering resolution plus scanning. Cancel Scan terminates the current command. The window remains navigable; a second scan is blocked until the first finishes. The spinner shows activity, not a completion percentage. Results appear after completion, not live. Large tables are inserted in batches. Window closure cancels scans and waits for workers, including any export already in progress.

The Results table shows port, protocol, state, service and version. Details / XML shows timestamps, command, grouped states and stderr/XML previews (up to 200,000 characters each). Nmap may summarize closed/filtered ports without listing individual numbers; those summaries appear under grouped states. Failed, timed-out and cancelled scans have an unavailable open count rather than a misleading zero. Truncated XML is not treated as a completed result.

Select CSV, TXT or JSON and Export Scan, then choose an existing directory. Empty completed results and failed attempts can be exported with metadata and errors. Files receive timestamped unique names and do not overwrite existing reports. CSV includes metadata in each row, including one metadata-only row when empty; potentially executable spreadsheet text is escaped. TXT is a readable summary; JSON retains full XML/stdout/stderr. Readable export failures leave the scan available for retry.

## Network Monitor

Enter a target and interval in seconds, then select **Start Monitoring**. Each probe sends one ping. The interval starts after the probe finishes. Navigate while it runs. Select **Stop Monitoring** to interrupt a ping or interval wait and archive the session.

The plot displays the latest 60 probes, with gaps for unavailable latency. The history table displays the latest 500 samples. Statistics and exports cover the entire session. Minimum, average and maximum use measured round-trip times. Loss uses packets reported sent and received. Timeouts without counts and local errors appear separately. **Export history CSV** saves a snapshot of the current or last stopped session.

## Reports

Select an operation to display its results. Use **Older** and **Newer** to browse pages of 100. The preview displays up to 80,000 characters. Choose TXT, CSV or JSON and select **Export selected** for the full result. Monitoring CSV contains one row per sample. Other central CSV exports list result fields and values. The scanner also provides its original port-oriented exports.

History is stored in `~/.local/state/kalinet/history.sqlite3` or the configured XDG state directory. History begins with operations performed in v0.5.0. Monitor sessions are archived on Stop or normal shutdown. Exports go to the configured report directory.

## Settings

Set the default ping count, command timeout, monitor interval, target and report directory, then select **Save settings**. The editor checks the values and tests directory write access before saving. In-flight operations keep their original parameters. Future operations use the saved defaults.

## Closing and errors

Close the window normally. If collection is running, the status changes to “Stopping background work…” and the subprocess is cancelled before exit. Errors are recorded in the per-user log described in the README. Missing utilities and disconnected interfaces should produce warnings rather than a crash. Consult the troubleshooting table before changing system configuration.

## Project submission

Fill in the author/course placeholders in the README. Complete the Kali acceptance procedures before presenting diagnostics, scans and exports as verified on that system.
