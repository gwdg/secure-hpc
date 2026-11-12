import importlib.resources
import logging
import socket
import subprocess
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from securehpc import utils
from securehpc.config import Config
from securehpc.utils import CommandError

DEFAULT_TEXT = (importlib.resources.files("securehpc") / "default_config.toml").read_text()


def test_run_returns_stdout() -> None:
    assert utils.run(["echo", "hi there"]) == "hi there\n"


def test_run_passes_input() -> None:
    assert utils.run(["tr", "a-z", "A-Z"], input="secret") == "SECRET"


def test_run_failure_includes_stderr() -> None:
    with pytest.raises(CommandError, match="exit code 3: oops"):
        utils.run(["sh", "-c", "echo oops >&2; exit 3"])


def test_background_stops_process() -> None:
    with utils.background(["sleep", "100"]) as proc:
        assert proc.poll() is None
    assert proc.returncode is not None


def test_background_stops_process_on_exception() -> None:
    with pytest.raises(RuntimeError), utils.background(["sleep", "100"]) as proc:
        raise RuntimeError("boom")
    assert proc.returncode is not None


def test_run_adds_env_without_logging_it(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    # sh is still found: env is added to the current environment (PATH stays), not a replacement
    assert utils.run(["sh", "-c", 'echo "$SECUREHPC_TEST"'], env={"SECUREHPC_TEST": "s3cret"}) == "s3cret\n"
    assert "s3cret" not in caplog.text


# ---------- Vault ----------


def make_config(tmp_path: Path) -> Config:
    token_file = tmp_path / "vault.token"
    token_file.write_text("hvs.MY-TOKEN\n")
    text = DEFAULT_TEXT.replace("~/.config/securehpc/vault.token", str(token_file))
    return Config.from_dict(tomllib.loads(text))


def test_vault_env(tmp_path: Path) -> None:
    with utils.vault_env(make_config(tmp_path), proxy=False) as env:
        assert env == {
            "VAULT_ADDR": "https://kms.hpc.gwdg.de",
            "VAULT_TOKEN": "hvs.MY-TOKEN",
        }


def test_vault_env_proxy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With proxy, the tunnel is open exactly while the block runs, and vault is pointed at it."""
    tunnels: list[list[str]] = []

    @contextmanager
    def fake_background(cmd: list[str], debug: bool = False) -> Iterator[subprocess.Popen[bytes]]:
        # like `ssh -D`: listen on the requested port
        tunnels.append(cmd)
        port = int(cmd[cmd.index("-D") + 1].rsplit(":", 1)[1])
        with socket.create_server(("127.0.0.1", port)), subprocess.Popen(["sleep", "100"]) as proc:
            yield proc
            proc.kill()

    monkeypatch.setattr(utils, "background", fake_background)
    with utils.vault_env(make_config(tmp_path), proxy=True) as env:
        port = env["HTTPS_PROXY"].removeprefix("socks5://127.0.0.1:")
        assert tunnels == [
            ["ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-D", f"127.0.0.1:{port}", "uXXXXX@glogin7.hpc.gwdg.de"]
        ]
        assert env["VAULT_TOKEN"] == "hvs.MY-TOKEN"


def test_wait_for_port_tunnel_died() -> None:
    with subprocess.Popen(["true"]) as proc:
        proc.wait()
        with pytest.raises(CommandError, match="exited with code 0"):
            utils._wait_for_port(utils._free_port(), proc)


def test_wait_for_port_timeout() -> None:
    with utils.background(["sleep", "100"]) as proc, pytest.raises(CommandError, match="did not open"):
        utils._wait_for_port(utils._free_port(), proc, timeout=0.5)
