import subprocess
import threading
from unittest.mock import MagicMock, patch

import pytest

from app.utils.command_runner import CommandCancelled, CommandError, CommandRunner


def fake_process(code=0):
    process = MagicMock()
    process.communicate.return_value = ("output", "")
    process.returncode = code
    process.poll.return_value = code
    return process


def test_missing_executable():
    with patch("app.utils.command_runner.shutil.which", return_value=None):
        with pytest.raises(CommandError, match="missing"):
            CommandRunner().run(["ip", "-j", "addr"])


def test_no_shell_and_locale():
    process = fake_process()
    with patch("app.utils.command_runner.shutil.which", return_value="/usr/bin/ip"), \
            patch("app.utils.command_runner.subprocess.Popen", return_value=process) as popen:
        result = CommandRunner().run(["ip", "-j", "addr"])
    assert result.stdout == "output"
    assert popen.call_args.args[0] == ["/usr/bin/ip", "-j", "addr"]
    assert popen.call_args.kwargs["shell"] is False
    assert popen.call_args.kwargs["env"]["LC_ALL"] == "C"


def test_timeout_kills_and_reaps():
    process = fake_process()
    process.poll.return_value = None
    process.communicate.side_effect = [subprocess.TimeoutExpired("ip", .15), ("", "")]
    with patch("app.utils.command_runner.shutil.which", return_value="/usr/bin/ip"), \
            patch("app.utils.command_runner.subprocess.Popen", return_value=process), \
            patch("app.utils.command_runner.time.monotonic", side_effect=[0, 0, 2]):
        with pytest.raises(CommandError, match="timed out"):
            CommandRunner().run(["ip"], timeout=1)
    process.kill.assert_called_once()
    assert process.communicate.call_count == 2


def test_cancel_during_command():
    process = fake_process()
    process.poll.return_value = None
    cancel = threading.Event()
    def communicate(**kwargs):
        if "timeout" in kwargs:
            cancel.set()
            raise subprocess.TimeoutExpired("ip", .15)
        return "", ""
    process.communicate.side_effect = communicate
    with patch("app.utils.command_runner.shutil.which", return_value="/usr/bin/ip"), \
            patch("app.utils.command_runner.subprocess.Popen", return_value=process):
        with pytest.raises(CommandCancelled):
            CommandRunner().run(["ip"], cancel=cancel)
    process.kill.assert_called_once()


def test_permission_error():
    with patch("app.utils.command_runner.shutil.which", return_value="/usr/bin/ip"), \
            patch("app.utils.command_runner.subprocess.Popen", side_effect=PermissionError("denied")):
        with pytest.raises(CommandError, match="denied"):
            CommandRunner().run(["ip"])


def test_failed_command():
    process = fake_process(2)
    with patch("app.utils.command_runner.shutil.which", return_value="/usr/bin/ip"), \
            patch("app.utils.command_runner.subprocess.Popen", return_value=process):
        with pytest.raises(CommandError, match="exit 2"):
            CommandRunner().run(["ip"])
