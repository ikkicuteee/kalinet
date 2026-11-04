"""Bounded, cancellable subprocess execution. No shell is involved."""
from dataclasses import dataclass
import logging
import os
import shutil
import subprocess
import threading
import time

LOG = logging.getLogger("kalinet.commands")


class CommandError(RuntimeError):
    pass


class CommandCancelled(CommandError):
    pass


@dataclass(frozen=True)
class CommandResult:
    args: tuple
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def run(self, args, timeout=10, cancel=None, accepted_codes=(0,)):
        if not isinstance(args, (list, tuple)) or not args or any(
                not isinstance(arg, str) or "\x00" in arg for arg in args):
            raise ValueError("Commands require a nonempty list of string arguments.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 120:
            raise ValueError("Command timeout must be between 0 and 120 seconds.")
        cancel = cancel if cancel is not None else threading.Event()
        if cancel.is_set():
            raise CommandCancelled("Refresh cancelled.")
        executable = shutil.which(args[0])
        if not executable:
            message = f"Required utility '{args[0]}' is missing. See installation instructions."
            LOG.warning(message)
            raise CommandError(message)
        process = None
        try:
            process = subprocess.Popen([executable, *args[1:]], shell=False,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                       errors="replace", env={**os.environ, "LC_ALL": "C"})
            deadline = time.monotonic() + timeout
            while True:
                if cancel.is_set():
                    raise CommandCancelled("Refresh cancelled.")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise CommandError(f"{args[0]} timed out after {timeout:g} seconds.")
                try:
                    stdout, stderr = process.communicate(timeout=min(0.15, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            result = CommandResult(tuple(args), process.returncode, stdout, stderr)
            if result.returncode not in accepted_codes:
                detail = stderr.strip() or stdout.strip() or "No error details returned."
                raise CommandError(f"{args[0]} failed (exit {result.returncode}): {detail[:500]}")
            return result
        except OSError as exc:
            LOG.warning("Could not execute %s: %s", args[0], exc)
            raise CommandError(f"Cannot execute {args[0]}: {exc}") from exc
        except CommandError as exc:
            LOG.warning("%s", exc)
            raise
        finally:
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate()
