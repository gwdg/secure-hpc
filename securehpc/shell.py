import logging
import shlex
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager

log = logging.getLogger(__name__)


class CommandError(Exception):
    pass


def run(cmd: list[str], input: str | None = None) -> str:
    """Run a command, return its stdout, raise CommandError on failure.

    Never pass secrets in `cmd`: arguments are visible to all users via `ps` and get logged.
    Use `input` (stdin) instead.
    """
    log.debug("Running: %s", shlex.join(cmd))
    result = subprocess.run(cmd, input=input, capture_output=True, text=True, check=False)
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
