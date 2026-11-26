# Phase 5 acceptance on Kali Linux

Use an Xfce terminal in the VMware guest. From an existing checkout and virtual environment:

```bash
cd ~/kalinet
git pull --ff-only origin main
sudo apt update
sudo apt install -y iputils-ping python3-tk
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pytest -q tests/test_monitor.py::test_real_loopback_probe
python main.py
```

The requirements install Matplotlib into the virtual environment. SQLite is included with Kali's Python. The real loopback test sends ICMP only to 127.0.0.1. The default automated run also includes this test if Linux and ping are available.

| Action | Expected observation |
| --- | --- |
| Save a monitor target of `127.0.0.1`, an interval of 2 seconds, a new report directory and a default ping count of 3. | Settings confirms the save. Diagnostics shows 3 packets and the Monitor shows the saved target and interval. |
| Try interval 0, target `--help`, or an existing regular file as the report directory. | A readable error appears. The last successful settings remain effective. |
| Start the loopback monitor and navigate between pages. | Time-stamped samples appear, the plot shows measured latency, and Start is disabled until Stop completes. At interval 2 the next probe starts about two seconds after the previous probe finishes. |
| Compare with `ping -n -c 3 127.0.0.1` in another terminal. | Both reach loopback. Latency values can differ between measurements. |
| Monitor the VM gateway, then disconnect the VMware network adapter temporarily and reconnect. | Where the gateway normally answers ICMP, replies cease or ping reports an error during disconnection and resume after recovery. A failed lookup or local routing error may yield unknown packet counts. Loopback remains available. |
| Stop while a probe is in flight, and again while waiting on a long interval. | Stop returns promptly. The history count stays fixed afterward. Starting again opens a fresh session. |
| Export history CSV and inspect the file. | Each sample has a timestamp, target, connectivity, RTT where measured and packet counts where known. The saved path appears on screen. |
| Refresh Network Information, run a localhost Ping and complete a localhost scan following the [scanner procedure](PHASE4_VERIFICATION.md). Open Reports. | Each operation and the stopped monitoring session appears separately. Selecting an older entry displays its stored result. Export it as TXT, CSV and JSON and verify module, time, target and outcome. |
| With the application closed, make the configured export destination unavailable for writing, then reopen and try exporting a saved result. | Export displays an error. The history entry is still selectable. Save a writable directory in Settings and retry. |
| Start the app with `PATH=/nonexistent "$PWD/.venv/bin/python" main.py` and start monitoring. | Missing ping generates a visible error, monitoring stops, and the failed session is available in Reports. Launch normally for subsequent checks. |
| Close the application during monitoring, relaunch and inspect Reports and Settings. | The final session is archived with its completed samples, including a session with zero completed samples. Saved defaults and earlier operations are available after restart. |

Record the guest OS, Python and iputils versions, date and observed outcomes when running this procedure. Windows test results are in [TEST_PLAN.md](TEST_PLAN.md).
