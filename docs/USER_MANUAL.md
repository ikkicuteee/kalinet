# KaliNet user manual — Phases 1 and 2

## Before launching

Install using the exact commands in [README](../README.md). Use your regular Kali desktop account. In VMware, ensure the guest network adapter is connected. NAT is typically sufficient for this milestone's Internet probe; no scanning is performed. KaliNet inspects the guest's interfaces, not the Windows host's adapters.

## Dashboard

Launch `python main.py` from the activated virtual environment. Collection begins automatically. Cards display hostname, active interface, IPv4, gateway, DNS, probe status, interface count and socket count. “Not run” for the diagnostic timestamp is expected in this milestone.

Select **Refresh Dashboard** or the header **Refresh** button to collect again. Progress animates while commands run. Multiple refresh clicks do not start concurrent collections. Warnings and interpretation notes appear below the cards. Snapshot time uses the Kali guest's local timezone.

## Network Information

Select **Network Information** in the sidebar. Its tabs share the same snapshot as the dashboard:

- **Interfaces:** names, operational states, MAC and IPv4/IPv6 addresses. `UNKNOWN` is a real kernel state and is common for loopback or virtual interfaces.
- **Traffic counters:** cumulative received/sent bytes and packets, errors and drops. Values are not bytes per second.
- **Routing & DNS:** default gateway, resolver source, configured servers, main route table entries and collection warnings.
- **Link details:** raw `ip -s link` output.

Tables have vertical and horizontal scrollbars. Read-only details can be selected and copied. Refresh either network page to update both pages.

## Connectivity interpretation

**Reachable** means the single probe to `1.1.1.1` returned successfully. **No ICMP reply** means ping completed without a response. **Unknown** means the probe could not complete, for example because ping was unavailable or hit its command timeout. Inspect warnings before assuming the VM is disconnected. Each refresh sends one real ICMP echo request; there is no periodic background probe in this version.

## Settings and remaining pages

Settings shows the configuration path and effective values. Edit that JSON file while KaliNet is closed and restart to apply changes. The README lists accepted values. Invalid files are left intact and defaults are used. Diagnostics, Port Scanner, Network Monitor and Reports are labeled placeholders; they cannot run or export anything yet.

## Closing and errors

Close the window normally. If collection is running, the status changes to “Stopping background work…” and the subprocess is cancelled before exit. Errors are recorded in the per-user log described in the README. Missing utilities and disconnected interfaces should produce warnings rather than a crash. Consult the troubleshooting table before changing system configuration.

## Project submission

Fill in the author/course placeholders in the README. Use the milestone demonstration checklist now; reserve the full-project diagnostics, scan and export demonstration until their implementation and Kali validation are complete.
