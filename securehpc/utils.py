"""Running external commands."""

import logging
import os
import shlex
import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager

from securehpc.config import Config

log = logging.getLogger(__name__)


class CommandError(Exception):
    pass


def run(cmd: list[str], input: str | None = None, env: dict[str, str] | None = None) -> str:
    """Run a command, return its stdout, raise CommandError on failure.

    Never pass secrets in `cmd`: arguments are visible to all users via `ps` and get logged.
    Use `input` (stdin) or `env` (added to the current environment, never logged) instead.
    """
    log.debug("Running: %s", shlex.join(cmd))
    full_env = {**os.environ, **env} if env else None
    result = subprocess.run(cmd, input=input, capture_output=True, text=True, check=False, env=full_env)
    if result.returncode != 0:
        raise CommandError(f"{shlex.join(cmd)} failed with exit code {result.returncode}: {result.stderr.strip()}")
    return result.stdout


@contextmanager
def background(cmd: list[str], debug: bool = False) -> Iterator[subprocess.Popen[bytes]]:
    """Run a command for the duration of the `with` block, then stop it. `debug` also shows its stdout."""
    log.debug("Starting in background: %s", shlex.join(cmd))
    # stderr stays on the terminal, so errors like "Permission denied" are visible
    stdout = None if debug else subprocess.DEVNULL
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=stdout)
    try:
        yield proc
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def cache_sudo_credentials() -> None:
    """Ask for the sudo password now, so later `sudo` calls don't stop the run to prompt.

    sudo remembers the password for a while (15 minutes by default). Only the commands
    that need root (cryptsetup, losetup, mount) use sudo; everything else runs as the user.
    """
    log.info("Some steps need root (LUKS image, mounting). Asking for your sudo password now.")
    run(["sudo", "-v"])


def ssh_target(cfg: Config) -> str:
    return f"{cfg.cluster.user}@{cfg.cluster.login_node}"


def ssh(cfg: Config, *cmd: str) -> str:
    """Run a command on the login node."""
    return run(["ssh", ssh_target(cfg), shlex.join(cmd)])


# ---------- Vault ----------

# Seconds until the wrapping token in command.sh expires, as in old/prepare_scripts.sh.
WRAP_TTL = 3000


@contextmanager
def vault_env(cfg: Config, proxy: bool) -> Iterator[dict[str, str]]:
    """Environment for `vault` calls inside the `with` block, like old/prepare_scripts.sh.

    The token goes through VAULT_TOKEN, as in the original, never as an argument.
    Every vault call also needs `-tls-skip-verify`, as in the original: the server's certificate does not verify.
    With `proxy`, Vault is reached through a SOCKS tunnel via the login node (old `secure_sbatch -p`),
    open only for the duration of the block.
    """
    env = {
        "VAULT_ADDR": cfg.vault.address,
        "VAULT_TOKEN": cfg.vault.token_file.read_text().strip(),
    }
    if not proxy:
        yield env
        return

    port = _free_port()
    log.info("Opening a SOCKS proxy to Vault through %s", cfg.cluster.login_node)
    tunnel = ["ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-D", f"127.0.0.1:{port}", ssh_target(cfg)]
    with background(tunnel) as proc:
        _wait_for_port(port, proc)
        yield env | {"HTTPS_PROXY": f"socks5://127.0.0.1:{port}"}


def _free_port() -> int:
    """A local port nobody listens on right now, so two tunnels never collide (the original always used 2020)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port: int = s.getsockname()[1]
        return port


def _wait_for_port(port: int, proc: subprocess.Popen[bytes], timeout: float = 30) -> None:
    """Wait until ssh listens on the port. It only does after logging in, which may ask for a passphrase."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise CommandError(f"SSH proxy exited with code {proc.returncode}, see its error above")
        try:
            socket.create_connection(("127.0.0.1", port), timeout=1).close()
            return
        except OSError:
            time.sleep(0.2)
    raise CommandError(f"SSH proxy did not open port {port} within {timeout:.0f}s")
