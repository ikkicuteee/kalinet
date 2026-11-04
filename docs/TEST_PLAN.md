# Test plan and verification record

## Automated checks

Run `python -m pytest -q` and `python -m compileall -q main.py app tests` from the project folder with development dependencies installed.

| Test file | Coverage |
| --- | --- |
| `test_command_runner.py` | Missing executable, argument-list/no-shell invocation, locale, deadline cleanup, cancellation, permission error, failed exit |
| `test_config.py` | Invalid types/ranges/paths/theme, initial creation, persistence, corrupt-file preservation, packaged-default agreement |
| `test_network.py` | Address/DNS parsing, malformed interface output, resolver fallback, snapshot fields, missing sources, cancellation |

No live network is required by these tests. Mocked command results validate service logic, not actual Linux utility compatibility or rendered Tk layouts. Diagnostic input validation, ping parsing, Nmap parsing and report generation tests belong to later phases and are not present yet.

## Kali Linux manual acceptance

Record date, Kali/Python versions, VMware network mode, actual results and pass/fail for each step. No manual pass is claimed in this document.

| ID | Procedure | Expected outcome |
| --- | --- | --- |
| M01 | Install and launch in Xfce without sudo | Native dark window, initial collection, no credential prompt |
| M02 | Visit all seven pages | Correct titles, selected navigation, clear placeholders |
| M03 | Compare `ip -j addr` and `ip -j route` with GUI | Matching interfaces/addresses and appropriate gateway |
| M04 | Compare DNS using `resolvectl dns` or `/etc/resolv.conf` | Correct source/servers, fallback warning if appropriate |
| M05 | Compare `ss -H -lntu` row count with dashboard | Matching socket count, allowing for live socket changes |
| M06 | Refresh repeatedly and navigate during collection | No freezing, no duplicate concurrent collections |
| M07 | Disconnect VMware virtual NIC, refresh, then reconnect | Missing routes/addresses or no reply displayed without crash; recovery after refresh |
| M08 | Compare traffic counters before/after guest traffic | Plausible cumulative increases; no rate claim |
| M09 | Close while refreshing | Pending subprocess stops and application exits |
| M10 | Back up user settings, set timeout to `0`, relaunch | Defaults loaded, Settings warning and log entry; invalid file preserved |
| M11 | Restore valid settings and set timeout to `1` | New effective value shown; command timeout warnings handled if triggered |
| M12 | Test at 1280×800 and 960×720, use scrollbars | Readable cards, accessible navigation and details |
| M13 | Inspect log and config paths as standard user | Per-user storage, no root ownership introduced |
| M14 | Launch with a PATH that omits network utilities, using absolute venv Python path | Missing-utility warnings, other available data retained |

For M14, avoid altering system binaries. An example from the project directory is `PATH=/nonexistent "$PWD/.venv/bin/python" main.py`; run normally afterward to restore command discovery.

## Verification status

The development host is Windows. Kali/Xfce rendering, VMware connectivity, actual Linux command execution and manual acceptance are **not verified** here.

Executed on 2026-11-04 in a project-local virtual environment with Python 3.14.5:

- `python -m pytest -q`: **27 passed in 0.30s**.
- `python -m compileall -q main.py app tests`: completed with no errors.

These results verify mocked service behavior on Windows, not a complete Kali desktop acceptance run.
