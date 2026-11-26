# Test plan and verification record

## Automated checks

Run `python -m pytest -q` and `python -m compileall -q main.py app tests` from the project folder with development dependencies installed.

| Test file | Coverage |
| --- | --- |
| `test_command_runner.py` | Missing executable, argument-list/no-shell invocation, locale, deadline cleanup with partial output, cancellation, permission error, failed exit |
| `test_config.py` | Invalid types/ranges/paths/theme, initial creation, persistence, corrupt-file preservation, packaged-default agreement |
| `test_network.py` | Address/DNS parsing, malformed output, resolver-file/NetworkManager sources, optional provider behavior, socket counting, snapshot fields, missing sources, cancellation |
| `test_validators.py` | IPv4/IPv6/hostname acceptance, malformed inputs, injection/option rejection, packet counts |
| `test_diagnostics.py` | Command arguments, ping statistics, hops, DNS answers/status/NODATA, malformed output, partial timeout and error reporting |
| `test_gui_diagnostics.py` | Real Tk event loop with mocked services: results, timestamp, input rejection, navigation, duplicate-run prevention, cancellation and shutdown |
| `test_scanner.py` | Ports/authorization, single-IP hostname pinning, unprivileged arguments, safe XML, missing Nmap, empty results, timeout/cancellation and scan lock |
| `test_reports.py` | CSV/TXT/JSON scan exports, metadata for empty results, formula escaping, permission failures and unique filenames |
| `test_gui_scanner.py` | Scan results, exports, repeated authorization, navigation, duplicate-run prevention, cancellation, shutdown and batched table rendering |
| `test_scanner_integration.py` | Opt-in real Nmap scan of a temporary localhost TCP listener |

No live network is required by the default tests. Mocked command results validate service logic, not actual Linux utility compatibility. Tk tests skip when desktop/Tcl initialization is unavailable; they do not replace an Xfce visual review. Follow [PHASE3_VERIFICATION.md](PHASE3_VERIFICATION.md) for diagnostics and [PHASE4_VERIFICATION.md](PHASE4_VERIFICATION.md) for scan acceptance. Only `KALINET_LIVE_TESTS=1` on Linux with Nmap enables the integration test, which scans localhost only.

## Kali Linux manual acceptance

Record date, Kali/Python versions, VMware network mode, actual results and pass/fail for each step. No manual pass is claimed in this document.

| ID | Procedure | Expected outcome |
| --- | --- | --- |
| M01 | Install and launch in Xfce without sudo | Native dark window, initial collection, no credential prompt |
| M02 | Visit all seven pages | Correct titles, selected navigation, diagnostics tools and clearly labeled remaining placeholders |
| M03 | Compare `ip -j addr` and `ip -j route` with GUI | Matching interfaces/addresses and appropriate gateway |
| M04 | Compare DNS using available `resolvectl`, `nmcli` and `/etc/resolv.conf` | Correct source labels/servers; no dashboard warning for absent optional tools |
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

### Phase 3 verification — 2026-11-04

Executed on the same Windows Python 3.14.5 host after the Phase 3 changes:

- Full suite: **100 passed, 1 skipped in 1.21s**. The invalid-input GUI test skipped because a repeated Tk initialization could not read the host's `init.tcl`.
- That skipped GUI test rerun alone in a fresh process: **1 passed in 0.33s**.
- Python compilation of `main.py`, `app`, and `tests`: passed.
- `git diff --check`: passed (Git emitted only Windows line-ending notices).

The full suite used `-p no:cacheprovider` and a newly allocated `--basetemp` path because pre-existing Windows pytest/cache directories had incompatible access permissions. Earlier setup/teardown errors were addressed before the final run. GUI tests exercised real Tk widgets and event-loop callbacks with mocked diagnostic services, not live Linux utilities.

The user reported a working v0.2.0 dashboard in Kali; this session did not independently inspect that VM. **The guest's zero-socket observation has not been verified against live `ss -tuln`.** The original selection flags are equivalent; revised parsing, retained raw output and a controlled listener procedure make the comparison testable. **Live Phase 3 Kali/Xfce acceptance remains pending.** Do not proceed to Phase 4 until the acceptance procedure is completed and reviewed.

### Phase 4 verification — 2026-11-26

The user explicitly authorized Phase 4 implementation on this date, superseding the earlier development gate without asserting new live Kali test results.

- Full suite on Windows/Python 3.14.5: **165 passed, 1 skipped in 3.62s**.
- The skipped test is the explicitly gated Linux/Nmap localhost integration test. Nmap is absent from this development host; no actual Nmap scan was executed here.
- All diagnostics and scanner Tk GUI tests passed in the final run, including cancellation, authorization, shutdown, export and batched table rendering. An earlier run skipped one diagnostics GUI test due to the existing intermittent host Tcl initialization issue.
- `python -m compileall -q main.py app tests`: passed.
- `git diff --check`: passed.
- Tests used a fresh temporary directory and `-p no:cacheprovider` to avoid pre-existing Windows cache permission issues.

Kali/Xfce visual acceptance and actual Nmap behavior remain pending. Run the Phase 4 acceptance procedure, including `KALINET_LIVE_TESTS=1 python -m pytest -q tests/test_scanner_integration.py`, inside Kali and record actual results. Phase 5 is not implemented and must wait for instruction.
