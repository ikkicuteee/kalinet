# KaliNet user manual — Phases 1–3

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

**Reachable** means the single probe to `1.1.1.1` returned successfully. **No ICMP reply** means ping completed without a response. **Unknown** means the probe could not complete, for example because ping was unavailable or hit its command timeout. Inspect warnings before assuming the VM is disconnected. Each refresh sends one real ICMP echo request; there is no periodic background probe in this version.

## Network Diagnostics

Select Ping, Traceroute, or DNS Lookup within the existing Network Diagnostics page. Enter a hostname or IPv4/IPv6 address, then select Run. Input rejects URLs, IP ranges, command options, spaces, shell syntax, and IPv6 zone suffixes. Internationalized hostnames must use punycode.

- **Ping:** choose 1–20 packets. Parsed results show transmitted/received packets, loss, min/average/max latency and deviation when available. The overall configured timeout can end a large packet count early; partial output remains available.
- **Traceroute:** uses numeric output, a 30-hop limit, one probe per hop and a one-second per-probe wait. Parsed results preserve hop addresses, response times, asterisks and error annotations. Command completion does not prove the destination was reached. IPv6 literals automatically select IPv6.
- **DNS Lookup:** queries with `dig` using the selected A, AAAA, MX, NS, TXT, CNAME, SOA or PTR type. Parsed results show DNS response status and answer-section records; the full authority/additional sections remain in Raw output. NXDOMAIN means no such name; SERVFAIL/REFUSED indicate resolver errors. NOERROR without answers means no records of that type. For PTR, enter a reverse DNS name such as `1.0.0.127.in-addr.arpa`.

Parsed results and Raw output are separate tabs. Raw output includes command arguments, exit status, stdout and stderr. Output appears on completion or cancellation, not as a live stream. Select Stop to cancel; commands also stop when the window closes. One diagnostic runs at a time, while sidebar navigation and dashboard refresh remain usable. The Settings command timeout (default 10 seconds, maximum 60) applies to the whole command; partial traceroutes are common on longer paths. Missing utilities produce a readable error; install `traceroute` and `dnsutils` as shown in the README.

## Settings and remaining pages

Settings shows the configuration path and effective values. Edit that JSON file while KaliNet is closed and restart to apply changes. The README lists accepted values. Invalid files are left intact and defaults are used. Port Scanner, Network Monitor and Reports remain labeled placeholders.

## Closing and errors

Close the window normally. If collection is running, the status changes to “Stopping background work…” and the subprocess is cancelled before exit. Errors are recorded in the per-user log described in the README. Missing utilities and disconnected interfaces should produce warnings rather than a crash. Consult the troubleshooting table before changing system configuration.

## Project submission

Fill in the author/course placeholders in the README. Use the milestone demonstration checklist now; reserve the full-project diagnostics, scan and export demonstration until their implementation and Kali validation are complete.
