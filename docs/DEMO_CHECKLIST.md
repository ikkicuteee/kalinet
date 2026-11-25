# CIT 244 demonstration checklist

## Current milestone demonstration

- Explain the problem: several Linux network tools expose related information in different formats.
- Explain the solution: a native desktop dashboard with real command integration and a separate service layer.
- Launch as a normal Kali user; identify sidebar, header and collection progress.
- Show hostname, interface, address, gateway and DNS.
- Open interface, traffic, route/DNS and link-detail tabs; compare one result with its Linux command.
- Refresh while navigating to demonstrate responsiveness.
- Demonstrate an error case using the test plan's restricted-PATH launch or disconnected virtual NIC, then restore normal conditions.
- Explain the difference between no ICMP reply and confirmed Internet failure.
- Show Settings and the per-user log; close during refresh to demonstrate cleanup.
- Run Ping on `127.0.0.1` and `::1`, Traceroute on `127.0.0.1`, and DNS Lookup on `example.com`.
- Show parsed results and raw outputs; reject `example.com; id` without starting a command.
- Stop a long diagnostic and navigate during execution. Complete [Phase 3 acceptance](PHASE3_VERIFICATION.md) before Phase 4.

## Full-project demonstration — blocked on later implementation

- Explain single-host authorization rules and perform an authorized localhost scan (Phase 4).
- Start/stop connectivity monitoring (Phase 5).
- Export a report and open the exported CSV/TXT/JSON (Phase 5).
- Record actual test outcomes and finish documentation review (Phase 6).

Do not present placeholder pages as working features. This milestone alone does not satisfy the complete final-project demonstration requirements.
